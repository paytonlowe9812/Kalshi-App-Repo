import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import IndexCreate, IndexUpdate
from backend.kalshi.client import get_kalshi_client
from backend.kalshi.implied_prob import (
    book_quotes_pct_from_rest,
    implied_odds_yes_no_from_rest,
    yes_spread_is_degenerate,
)
from backend.kalshi.websocket import ws_manager
from backend.engine.index_auto_roll import infer_series_ticker

router = APIRouter(prefix="/api/indexes", tags=["indexes"])


def _dedupe_market_rows(rows: list) -> list:
    """First row wins per ticker (DB may have legacy duplicates before unique index)."""
    seen: set[str] = set()
    out = []
    for m in rows:
        t = (m["ticker"] or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(m)
    return out


def _dedupe_index_markets_payload(markets: list[dict] | None) -> list[dict]:
    """Skip duplicate tickers on create/update (first occurrence keeps sort order)."""
    if not markets:
        return []
    seen: set[str] = set()
    out: list[dict] = []
    for m in markets:
        t = (m.get("ticker") or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(m)
    return out


def _index_market_row(index_id: int, m: dict, sort_order: int) -> tuple:
    t = (m.get("ticker") or "").strip()
    label = (m.get("label") or "").strip() or t or "market"
    ser = (m.get("series_ticker") or "").strip() or infer_series_ticker(t) or None
    ar = m.get("auto_roll")
    if ar is None:
        ar = 1
    else:
        ar = 1 if ar else 0
    return (index_id, t, label, sort_order, ser, ar)


@router.get("")
def list_indexes():
    db = get_db()
    indexes = db.execute("SELECT * FROM sentiment_indexes ORDER BY id").fetchall()
    result = []
    for idx in indexes:
        markets = db.execute(
            "SELECT * FROM sentiment_index_markets WHERE index_id = ? ORDER BY sort_order",
            (idx["id"],),
        ).fetchall()
        deduped = _dedupe_market_rows(list(markets))
        result.append({
            **dict(idx),
            "markets": [dict(m) for m in deduped],
        })
    return result


@router.post("")
async def create_index(data: IndexCreate):
    db = get_db()
    markets_in = _dedupe_index_markets_payload([dict(m) for m in data.markets])
    db.execute("INSERT INTO sentiment_indexes (name) VALUES (?)", (data.name,))
    index_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i, m in enumerate(markets_in):
        db.execute(
            "INSERT INTO sentiment_index_markets (index_id, ticker, label, sort_order, series_ticker, auto_roll) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            _index_market_row(index_id, m, i),
        )
    db.commit()
    tickers = [m["ticker"] for m in markets_in if m.get("ticker")]
    if tickers:
        await ws_manager.subscribe(tickers)
    return {"id": index_id, "status": "created"}


@router.put("/{id}")
async def update_index(id: int, data: IndexUpdate):
    db = get_db()
    if data.name is not None:
        db.execute("UPDATE sentiment_indexes SET name = ? WHERE id = ?", (data.name, id))
    if data.markets is not None:
        markets_in = _dedupe_index_markets_payload([dict(m) for m in data.markets])
        db.execute("DELETE FROM sentiment_index_markets WHERE index_id = ?", (id,))
        for i, m in enumerate(markets_in):
            db.execute(
                "INSERT INTO sentiment_index_markets (index_id, ticker, label, sort_order, series_ticker, auto_roll) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                _index_market_row(id, m, i),
            )
    db.commit()
    if data.markets is not None:
        tickers = [m["ticker"] for m in markets_in if m.get("ticker")]
        if tickers:
            await ws_manager.subscribe(tickers)
    return {"status": "updated"}


@router.delete("/{id}")
def delete_index(id: int):
    db = get_db()
    db.execute("DELETE FROM sentiment_indexes WHERE id = ?", (id,))
    db.commit()
    return {"status": "deleted"}


@router.get("/{id}/live")
async def get_live_index(id: int):
    db = get_db()
    idx = db.execute("SELECT * FROM sentiment_indexes WHERE id = ?", (id,)).fetchone()
    if not idx:
        raise HTTPException(404, "Index not found")
    markets = db.execute(
        "SELECT * FROM sentiment_index_markets WHERE index_id = ? ORDER BY sort_order",
        (id,),
    ).fetchall()

    client = get_kalshi_client()
    market_rows = _dedupe_market_rows(list(markets))
    rest_by_ticker: Dict[str, Optional[Dict[str, Any]]] = {}
    if client and market_rows:

        async def _fetch_market(tkr: str):
            try:
                raw = await client.get_market(tkr)
                info = raw.get("market", raw)
                return tkr, info if isinstance(info, dict) else None
            except Exception:
                return tkr, None

        pairs = await asyncio.gather(*[_fetch_market(m["ticker"]) for m in market_rows])
        rest_by_ticker = {t: info for t, info in pairs}

    coins = []
    total_yes = 0
    total_no = 0
    bull_count = 0
    bear_count = 0

    for m in market_rows:
        tkr = m["ticker"]
        yes_bid = yes_ask = no_bid = no_ask = None
        yes_odds = 50.0
        no_odds = 50.0
        snap = ws_manager.get_cached_market(tkr)
        if snap:
            yes_bid = snap.yes_bid_pct
            yes_ask = snap.yes_ask_pct
            no_bid = snap.no_bid_pct
            no_ask = snap.no_ask_pct
            if snap.yes_price is not None:
                wb, wa = snap.yes_bid_pct, snap.yes_ask_pct
                if not (
                    wb is not None
                    and wa is not None
                    and yes_spread_is_degenerate(wb, wa)
                ):
                    yes_odds = float(snap.yes_price)
                    no_odds = float(
                        snap.no_price if snap.no_price is not None else 100.0 - yes_odds
                    )

        market_info = rest_by_ticker.get(tkr)
        if market_info:
            try:
                b = book_quotes_pct_from_rest(market_info)
                yes_bid = yes_bid if yes_bid is not None else b["yes_bid"]
                yes_ask = yes_ask if yes_ask is not None else b["yes_ask"]
                no_bid = no_bid if no_bid is not None else b["no_bid"]
                no_ask = no_ask if no_ask is not None else b["no_ask"]
                yo, no_ = implied_odds_yes_no_from_rest(market_info)
                yes_odds, no_odds = yo, no_
            except Exception:
                pass
        bullish = yes_odds > 50
        if bullish:
            bull_count += 1
        else:
            bear_count += 1
        total_yes += yes_odds
        total_no += no_odds
        coins.append({
            "ticker": m["ticker"],
            "label": m["label"],
            "yes_bid": yes_bid,
            "yes_ask": yes_ask,
            "no_bid": no_bid,
            "no_ask": no_ask,
            "yes_odds": round(yes_odds, 1),
            "no_odds": round(no_odds, 1),
            "bullish": bullish,
        })

    count = len(market_rows) or 1
    avg_yes = round(total_yes / count, 1)
    avg_no = round(total_no / count, 1)
    score = round(avg_yes, 0)

    return {
        "name": idx["name"],
        "score": score,
        "bull_count": bull_count,
        "bear_count": bear_count,
        "avg_yes": avg_yes,
        "avg_no": avg_no,
        "coins": coins,
    }
