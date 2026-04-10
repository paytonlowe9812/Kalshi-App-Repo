import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.database import get_db
from backend.kalshi.client import get_kalshi_client

router = APIRouter(prefix="/api/markets", tags=["markets"])

# Extra crypto series not guaranteed to appear in GET /series?category=Crypto for every account/API version.
_FALLBACK_CRYPTO_SERIES = [
    "KXXRP15M", "KXXRP", "KXXRPD",
    "KXDOGE15M", "KXDOGE", "KXDOGED",
    "KXBNB15M", "KXBNB", "KXBNBD",
    "KXHYPE15M", "KXHYPE", "KXHYPED",
]

CATEGORY_SERIES = {
    "crypto": [
        "KXBTC15M", "KXETH15M", "KXSOL15M",
        "KXBTC", "KXETH", "KXSOL",
        "KXBTCD", "KXETHD", "KXSOLD",
        *_FALLBACK_CRYPTO_SERIES,
    ],
    "politics": ["KXELECTION", "KXPRESAPP", "KXHOUSE", "KXSENATE", "KXNEWPOPE"],
    "economics": ["KXCPI", "KXFED", "KXGDP", "KXJOBS", "KXUNEMPLOYMENT"],
    "sports": ["KXNBA", "KXMLB", "KXNFL", "KXNHL", "KXSOCCER", "KXPGA", "KXTENNIS"],
    "weather": ["KXTEMP", "KXHURRICANE", "KXWARMING"],
}

# Kalshi cadence hints (series ticker prefix before first "-").
_SERIES_15M = frozenset({
    "KXBTC15M", "KXETH15M", "KXSOL15M",
    "KXXRP15M", "KXDOGE15M", "KXBNB15M", "KXHYPE15M",
})
_SERIES_DAILY_CRYPTO = frozenset({
    "KXBTCD", "KXETHD", "KXSOLD",
    "KXXRPD", "KXDOGED", "KXBNBD", "KXHYPED",
})
_HORIZON_KEYS = frozenset(
    {"15m", "hourly", "daily", "weekly", "monthly", "annual", "one_time"}
)


def _series_prefix(ticker: str) -> str:
    if not ticker:
        return ""
    return ticker.split("-")[0].upper()


def _hours_to_close(close_time: Optional[str]) -> Optional[float]:
    """Hours from now until close; negative if already past."""
    if not close_time or not str(close_time).strip():
        return None
    s = str(close_time).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (dt - now).total_seconds() / 3600.0
    except (TypeError, ValueError):
        return None


def _classify_horizon(m: dict) -> str:
    """Best-effort bucket from series ticker + time-to-close (Kalshi naming varies)."""
    ticker = m.get("ticker") or ""
    series = _series_prefix(ticker)
    h = _hours_to_close(m.get("close_time"))

    if series in _SERIES_15M or "15M" in series:
        return "15m"
    if series in _SERIES_DAILY_CRYPTO:
        return "daily"
    if "1H" in series or "HRLY" in series or "HOURLY" in series:
        return "hourly"

    if h is None:
        return "one_time"
    if h < 0:
        return "one_time"

    if h <= 2:
        return "15m"
    if h <= 8:
        return "hourly"
    if h <= 72:
        return "daily"
    if h <= 24 * 14:
        return "weekly"
    if h <= 24 * 90:
        return "monthly"
    if h <= 24 * 540:
        return "annual"
    return "one_time"


def _normalize_horizon_param(horizon: Optional[str]) -> Optional[str]:
    if not horizon:
        return None
    raw = horizon.strip().lower().replace("-", "_")
    if raw in ("", "all", "any"):
        return None
    if raw == "onetime":
        raw = "one_time"
    if raw in _HORIZON_KEYS:
        return raw
    return None


_CRYPTO_SERIES_RE = re.compile(r"^KX[A-Z0-9]{2,20}(?:15M|1H|HRLY|HOURLY|D)?$", re.I)


async def _crypto_series_from_catalog(client) -> list[str]:
    """Series tickers under Kalshi's Crypto category so search is not limited to BTC/ETH/SOL."""
    out: list[str] = []
    seen: set[str] = set()
    for cat in ("Crypto", "crypto"):
        try:
            r = await client.get_series_list(category=cat)
        except Exception:
            continue
        for s in r.get("series") or []:
            t = (s.get("ticker") or "").strip().upper()
            if not t or t in seen:
                continue
            if not _CRYPTO_SERIES_RE.match(t):
                continue
            seen.add(t)
            out.append(t)
        if out:
            break
    return out


async def _wide_fetch_markets(client) -> list[dict]:
    sem = asyncio.Semaphore(14)

    async def _events_for_series(series: str) -> list:
        async with sem:
            try:
                r = await client.get_events(
                    limit=25,
                    status="open",
                    series_ticker=series,
                    with_nested_markets=True,
                )
                return r.get("events", [])
            except Exception:
                return []

    all_markets: list[dict] = []
    base = await client.get_events(
        limit=150, status="open", with_nested_markets=True,
    )
    for evt in base.get("events", []):
        all_markets.extend(evt.get("markets", []))

    seen_series: set[str] = set()
    all_series: list[str] = []
    for series_list in CATEGORY_SERIES.values():
        for s in series_list:
            u = s.upper()
            if u not in seen_series:
                seen_series.add(u)
                all_series.append(u)

    for t in await _crypto_series_from_catalog(client):
        if t not in seen_series:
            seen_series.add(t)
            all_series.append(t)

    for t in _FALLBACK_CRYPTO_SERIES:
        u = t.upper()
        if u not in seen_series:
            seen_series.add(u)
            all_series.append(u)

    event_batches = await asyncio.gather(
        *[_events_for_series(s) for s in all_series]
    )
    for evts in event_batches:
        for evt in evts:
            all_markets.extend(evt.get("markets", []))

    return _dedupe_markets_by_ticker(all_markets)


def _normalize_market(m: dict) -> dict:
    """Flatten Kalshi v2 market fields into the shape the frontend expects."""
    def _cents(dollar_str):
        try:
            return round(float(dollar_str) * 100)
        except (TypeError, ValueError):
            return None

    def _vol(fp_str):
        try:
            return round(float(fp_str))
        except (TypeError, ValueError):
            return None

    def _pick(primary, fallback):
        return primary if primary is not None else fallback

    title = m.get("title") or m.get("yes_sub_title") or m.get("ticker", "")
    return {
        "ticker": m.get("ticker", ""),
        "event_ticker": m.get("event_ticker", ""),
        "title": title,
        "yes_bid": _pick(_cents(m.get("yes_bid_dollars")), m.get("yes_bid")),
        "yes_ask": _pick(_cents(m.get("yes_ask_dollars")), m.get("yes_ask")),
        "no_bid": _pick(_cents(m.get("no_bid_dollars")), m.get("no_bid")),
        "no_ask": _pick(_cents(m.get("no_ask_dollars")), m.get("no_ask")),
        "last_price": _pick(_cents(m.get("last_price_dollars")), m.get("last_price")),
        "volume": _pick(_vol(m.get("volume_fp")), m.get("volume", 0)),
        "volume_24h": _pick(_vol(m.get("volume_24h_fp")), m.get("volume_24h", 0)),
        "open_interest": _pick(_vol(m.get("open_interest_fp")), m.get("open_interest", 0)),
        "status": m.get("status", ""),
        "close_time": m.get("close_time", ""),
        "yes_sub_title": m.get("yes_sub_title", ""),
        "no_sub_title": m.get("no_sub_title", ""),
        "event_ticker": m.get("event_ticker", ""),
    }


def _dedupe_markets_by_ticker(markets: list[dict]) -> list[dict]:
    by_ticker: dict[str, dict] = {}
    for m in markets:
        t = m.get("ticker")
        if t and t not in by_ticker:
            by_ticker[t] = m
    return list(by_ticker.values())


@router.get("")
async def list_markets(
    search: Optional[str] = None,
    category: Optional[str] = None,
    horizon: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_dir: Optional[str] = "desc",
    limit: int = 50,
    cursor: Optional[str] = None,
):
    client = get_kalshi_client()
    if not client:
        return {"markets": [], "cursor": None}
    search_clean = (search or "").strip() or None
    horizon_clean = _normalize_horizon_param(horizon)
    use_wide_pool = bool(search_clean) or (
        bool(horizon_clean) and not (category and category in CATEGORY_SERIES)
    )
    try:
        all_markets = []

        if category and category in CATEGORY_SERIES:
            for series in CATEGORY_SERIES[category]:
                try:
                    result = await client.get_events(
                        limit=20, status="open",
                        series_ticker=series, with_nested_markets=True,
                    )
                    for evt in result.get("events", []):
                        all_markets.extend(evt.get("markets", []))
                except Exception:
                    continue
        elif use_wide_pool:
            all_markets = await _wide_fetch_markets(client)
        else:
            result = await client.get_events(
                limit=40, status="open", with_nested_markets=True,
            )
            for evt in result.get("events", []):
                all_markets.extend(evt.get("markets", []))

        normalized = [_normalize_market(m) for m in all_markets]

        by_event: dict[str, list[dict]] = {}
        for m in normalized:
            by_event.setdefault(m["event_ticker"] or m["ticker"], []).append(m)
        deduped = []
        for strikes in by_event.values():
            if len(strikes) == 1:
                deduped.append(strikes[0])
            else:
                best = min(
                    strikes,
                    key=lambda s: abs((s.get("yes_bid") or 0) - 50),
                )
                total_vol = sum(s.get("volume") or 0 for s in strikes)
                best["volume"] = total_vol
                deduped.append(best)
        normalized = deduped

        if horizon_clean:
            normalized = [m for m in normalized if _classify_horizon(m) == horizon_clean]

        if search_clean:
            q = search_clean.lower()
            normalized = [
                m for m in normalized
                if q in (m.get("title") or "").lower()
                or q in (m.get("ticker") or "").lower()
                or q in (m.get("event_ticker") or "").lower()
                or q in (m.get("yes_sub_title") or "").lower()
                or q in (m.get("no_sub_title") or "").lower()
            ]

        descending = sort_dir != "asc"
        if sort_by == "volume":
            normalized.sort(key=lambda m: m.get("volume") or 0, reverse=descending)
        elif sort_by == "close_date":
            normalized.sort(key=lambda m: m.get("close_time") or "", reverse=descending)

        normalized = normalized[:limit]

        return {"markets": normalized, "cursor": None}
    except Exception as e:
        raise HTTPException(502, f"Kalshi API error: {e}")


@router.get("/favorites")
def list_favorites():
    db = get_db()
    rows = db.execute("SELECT ticker, added_at FROM favorites ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


@router.get("/{ticker}")
async def get_market(ticker: str):
    client = get_kalshi_client()
    if not client:
        raise HTTPException(503, "No active API key")
    try:
        return await client.get_market(ticker)
    except Exception as e:
        raise HTTPException(502, f"Kalshi API error: {e}")


@router.get("/{ticker}/orderbook")
async def get_orderbook(ticker: str):
    client = get_kalshi_client()
    if not client:
        raise HTTPException(503, "No active API key")
    try:
        return await client.get_orderbook(ticker)
    except Exception as e:
        raise HTTPException(502, f"Kalshi API error: {e}")


@router.get("/{ticker}/history")
async def get_market_history(ticker: str, limit: int = 100):
    client = get_kalshi_client()
    if not client:
        raise HTTPException(503, "No active API key")
    try:
        return await client.get_market_history(ticker, limit=limit)
    except Exception as e:
        raise HTTPException(502, f"Kalshi API error: {e}")


@router.post("/{ticker}/favorite")
def add_favorite(ticker: str):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO favorites (ticker) VALUES (?)", (ticker,))
    db.commit()
    return {"status": "favorited"}


@router.delete("/{ticker}/favorite")
def remove_favorite(ticker: str):
    db = get_db()
    db.execute("DELETE FROM favorites WHERE ticker = ?", (ticker,))
    db.commit()
    return {"status": "unfavorited"}
