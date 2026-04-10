import asyncio
import logging

from backend.database import get_db
from backend.kalshi.client import get_kalshi_client
from backend.kalshi.implied_prob import (
    book_quotes_pct_from_rest,
    implied_odds_yes_no_from_rest,
    scalar_to_implied_pct,
    yes_spread_is_degenerate,
)
from backend.kalshi.websocket import ws_manager
from backend.kalshi.market_derived import (
    distance_from_strike_from_market,
    last_traded_pct_candidates,
    minutes_to_expiry_from_market,
)

logger = logging.getLogger(__name__)


def _f(x) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


async def _fetch_market_rest(ticker: str) -> dict | None:
    client = get_kalshi_client()
    if not client:
        return None
    try:
        data = await client.get_market(ticker)
        return data.get("market", data)
    except Exception as e:
        logger.debug("REST get_market(%s) failed: %s", ticker, e)
        return None


def _apply_bot_rest_enrichment(ticker: str, market: dict, variables: dict) -> None:
    """Fill time/distance/last/bid/ask from Get Market payload (Kalshi OpenAPI)."""
    variables["TimeToExpiry"] = minutes_to_expiry_from_market(market)
    variables["DistanceFromStrike"] = distance_from_strike_from_market(market, ticker)
    for cand in last_traded_pct_candidates(market):
        lt = scalar_to_implied_pct(cand)
        if lt is not None:
            variables["LastTraded"] = _f(lt)
            break
    b = book_quotes_pct_from_rest(market)
    yb, ya = b["yes_bid"], b["yes_ask"]
    if yb is not None and ya is not None and not yes_spread_is_degenerate(yb, ya):
        variables["Bid"] = _f(yb)
        variables["Ask"] = _f(ya)
    bid_v = variables.get("Bid")
    ask_v = variables.get("Ask")
    if (bid_v is None or ask_v is None or yes_spread_is_degenerate(bid_v, ask_v)) and "YES_price" in variables:
        mid = float(variables["YES_price"])
        variables["Bid"] = round(max(0.0, mid - 0.5), 2)
        variables["Ask"] = round(min(100.0, mid + 0.5), 2)


async def _resolve_all_core(
    bot_id: int,
) -> tuple[dict[str, float], set[str]]:
    db = get_db()
    bot = db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
    variables: dict[str, float] = {}
    unavailable: set[str] = set()

    if bot and bot["market_ticker"]:
        ticker = bot["market_ticker"]
        market_rest = await _fetch_market_rest(ticker) if get_kalshi_client() else None
        snap = ws_manager.get_cached_market(ticker)
        # Kalshi often sends a wide YES book (bid 0 / ask 100) when liquidity is thin.
        # _on_message still fills yes_price/no_price from last trade or mid; use that.
        filled_from_ws = False
        if snap:
            tight_book = (
                snap.yes_bid_pct is not None
                and snap.yes_ask_pct is not None
                and not yes_spread_is_degenerate(snap.yes_bid_pct, snap.yes_ask_pct)
            )
            has_implied = snap.yes_price is not None and snap.no_price is not None
            if tight_book:
                variables["YES_price"] = _f(snap.yes_bid_pct)
                variables["NO_price"] = _f(snap.no_bid_pct)
                filled_from_ws = True
            elif has_implied:
                variables["YES_price"] = _f(snap.yes_price)
                variables["NO_price"] = _f(snap.no_price)
                filled_from_ws = True
            if filled_from_ws:
                variables["LastTraded"] = _f(snap.last_traded)
                if tight_book:
                    variables["Bid"] = _f(snap.yes_bid_pct)
                    variables["Ask"] = _f(snap.yes_ask_pct)
                else:
                    # Degenerate WS book (bid~0 / ask~100): use implied mid ± 0.5 as a
                    # stand-in so callers never see the meaningless 0/99 sentinels.
                    # _apply_bot_rest_enrichment will overwrite with real REST values below.
                    mid = variables.get("YES_price")
                    if mid is not None:
                        variables["Bid"] = round(max(0.0, float(mid) - 0.5), 2)
                        variables["Ask"] = round(min(100.0, float(mid) + 0.5), 2)
                variables["FillPrice"] = _get_fill_price(bot_id, ticker)
                variables["TimeToExpiry"] = _f(snap.minutes_to_expiry)
                variables["DistanceFromStrike"] = _f(snap.distance_from_strike)
        if not filled_from_ws:
            if market_rest:
                b = book_quotes_pct_from_rest(market_rest)
                yb, ya = b["yes_bid"], b["yes_ask"]
                if (
                    yb is not None
                    and ya is not None
                    and not yes_spread_is_degenerate(yb, ya)
                ):
                    variables["YES_price"] = _f(yb)
                    variables["NO_price"] = _f(b["no_bid"])
                else:
                    yi, ni = implied_odds_yes_no_from_rest(market_rest)
                    variables["YES_price"] = _f(yi)
                    variables["NO_price"] = _f(ni)
                variables["Bid"] = _f(b["yes_bid"])
                variables["Ask"] = _f(b["yes_ask"])
                lt = scalar_to_implied_pct(market_rest.get("last_price_dollars"))
                if lt is None:
                    lt = scalar_to_implied_pct(market_rest.get("last_price"))
                variables["LastTraded"] = _f(lt)
                variables["FillPrice"] = _get_fill_price(bot_id, ticker)
                variables["TimeToExpiry"] = 0.0
                variables["DistanceFromStrike"] = 0.0
            else:
                if get_kalshi_client() is None:
                    logger.warning(
                        "No active Kalshi API key: cannot load market %s (configure Keys in CONFIG)",
                        ticker,
                    )
                for k in ("YES_price", "NO_price", "LastTraded", "Bid", "Ask", "FillPrice", "TimeToExpiry", "DistanceFromStrike"):
                    variables[k] = 0.0
                    unavailable.add(k)
        if market_rest and (filled_from_ws or "YES_price" in variables):
            _apply_bot_rest_enrichment(ticker, market_rest, variables)

        # Flip Bid/Ask to the NO book when the bot trades the NO side.
        # Binary contract: no_bid = 100 - yes_ask, no_ask = 100 - yes_bid.
        cs = str(dict(bot).get("contract_side") or "yes").lower().strip()
        if cs == "no" and "Bid" in variables and "Ask" in variables:
            yes_bid = variables["Bid"]
            yes_ask = variables["Ask"]
            variables["Bid"] = round(100.0 - yes_ask, 2)
            variables["Ask"] = round(100.0 - yes_bid, 2)

    client = get_kalshi_client()
    daily_pnl = 0.0
    position_size = 0.0
    if client:
        try:
            logs = db.execute(
                "SELECT SUM(pnl) as total FROM trade_log WHERE date(logged_at) = date('now')"
            ).fetchone()
            daily_pnl = logs["total"] or 0.0
        except Exception:
            pass
        try:
            positions = await client.get_positions()
            pos_list = positions.get("market_positions", [])
            if bot and bot["market_ticker"]:
                for p in pos_list:
                    if p.get("ticker") == bot["market_ticker"]:
                        position_size = float(p.get("position", 0))
                        break
        except Exception:
            pass

    variables["DailyPnL"] = daily_pnl
    variables["PositionSize"] = position_size

    indexes = db.execute("SELECT * FROM sentiment_indexes").fetchall()
    index_ticker_set: set[str] = set()
    index_sections: list[tuple] = []
    for idx in indexes:
        markets = db.execute(
            "SELECT * FROM sentiment_index_markets WHERE index_id = ?", (idx["id"],)
        ).fetchall()
        index_sections.append((idx, markets))
        for m in markets:
            t = (m["ticker"] or "").strip()
            if t:
                index_ticker_set.add(t)

    rest_by_index_ticker: dict[str, dict] = {}
    if index_ticker_set and get_kalshi_client():

        async def _fetch_one(tkr: str):
            mk = await _fetch_market_rest(tkr)
            return tkr, mk

        pairs = await asyncio.gather(
            *[_fetch_one(t) for t in index_ticker_set],
            return_exceptions=True,
        )
        for item in pairs:
            if not (isinstance(item, tuple) and len(item) == 2):
                continue
            tkr, mk = item
            if isinstance(mk, dict):
                rest_by_index_ticker[tkr] = mk

    for idx, markets in index_sections:
        total_yes = 0.0
        total_no = 0.0
        bull = 0
        bear = 0
        for m in markets:
            raw = (m["label"] or "").strip()
            label = raw or (m["ticker"] or "").strip() or "market"
            tkr = (m["ticker"] or "").strip()
            snap = ws_manager.get_cached_market(tkr) if tkr else None
            y = n = None

            # Match /api/indexes/{id}/live: prefer REST implied odds when available.
            # WS alone can show bogus ~0/~100 from stale price_dollars on a wide book.
            market_rest = rest_by_index_ticker.get(tkr) if tkr else None
            if market_rest:
                y, n = implied_odds_yes_no_from_rest(market_rest)
            elif snap and snap.yes_price is not None and snap.no_price is not None:
                y = float(snap.yes_price)
                n = float(snap.no_price)
            elif (
                snap
                and snap.yes_bid_pct is not None
                and snap.yes_ask_pct is not None
                and not yes_spread_is_degenerate(snap.yes_bid_pct, snap.yes_ask_pct)
            ):
                y = round((float(snap.yes_bid_pct) + float(snap.yes_ask_pct)) / 2.0, 1)
                n = round(100.0 - y, 1)
            if y is None:
                y = n = 50.0
                unavailable.add(f"{label}.YES")
                unavailable.add(f"{label}.NO")
            total_yes += y
            total_no += n
            if y > 50:
                bull += 1
            else:
                bear += 1
            variables[f"{label}.YES"] = y
            variables[f"{label}.NO"] = n
        count = len(markets) or 1
        variables[f"{idx['name']}.Score"] = round(total_yes / count, 1)
        variables[f"{idx['name']}.BullCount"] = float(bull)
        variables[f"{idx['name']}.BearCount"] = float(bear)
        variables[f"{idx['name']}.AvgYES"] = round(total_yes / count, 1)
        variables[f"{idx['name']}.AvgNO"] = round(total_no / count, 1)

    user_vars = db.execute(
        "SELECT name, value FROM variables WHERE bot_id = ?", (bot_id,)
    ).fetchall()
    for v in user_vars:
        try:
            variables[v["name"]] = float(v["value"])
        except (ValueError, TypeError):
            variables[v["name"]] = 0.0

    return variables, unavailable


async def resolve_all(bot_id: int) -> dict[str, float]:
    variables, _ = await _resolve_all_core(bot_id)
    return variables


def _get_fill_price(bot_id: int, ticker: str) -> float:
    db = get_db()
    row = db.execute(
        "SELECT entry_price FROM trade_log WHERE bot_id = ? AND market_ticker = ? "
        "ORDER BY logged_at DESC LIMIT 1",
        (bot_id, ticker),
    ).fetchone()
    return row["entry_price"] if row and row["entry_price"] else 0.0
