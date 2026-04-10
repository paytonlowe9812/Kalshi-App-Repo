"""
Background auto-roll for sentiment index markets (same idea as bot auto_roll):
when a listed contract is settled/closed, advance to the next open contract in the series.
"""

from __future__ import annotations

import asyncio
import logging

from backend.database import get_db
from backend.kalshi.client import get_kalshi_client
from backend.kalshi.websocket import ws_manager

logger = logging.getLogger(__name__)

_index_roll_task: asyncio.Task | None = None


def infer_series_ticker(market_ticker: str) -> str | None:
    if not (market_ticker or "").strip():
        return None
    parts = market_ticker.strip().split("-")
    return parts[0] if parts else None


async def roll_sentiment_index_markets_once() -> None:
    client = get_kalshi_client()
    if not client:
        return

    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, ticker, label, series_ticker, auto_roll FROM sentiment_index_markets"
        ).fetchall()
    except Exception:
        return

    for row in rows:
        try:
            ar = row["auto_roll"]
        except (KeyError, IndexError):
            ar = 1
        if ar is None or int(ar) == 0:
            continue

        current = (row["ticker"] or "").strip()
        try:
            stored_series = (row["series_ticker"] or "").strip()
        except (KeyError, IndexError):
            stored_series = ""

        series = stored_series or infer_series_ticker(current) or ""
        if not series:
            continue

        needs_roll = False
        if not current:
            needs_roll = True
        else:
            try:
                mdata = await client.get_market(current)
                market = mdata.get("market", mdata)
                status = (market.get("status") or "").lower()
                if status in ("closed", "settled", "determined", "finalized"):
                    needs_roll = True
            except Exception:
                needs_roll = True

        if not needs_roll:
            continue

        try:
            new_ticker = await client.find_next_contract(series, current or None)
        except Exception as e:
            logger.warning("Index auto-roll lookup failed (%s): %s", series, e)
            continue

        if not new_ticker or new_ticker == current:
            continue

        new_series = stored_series or infer_series_ticker(new_ticker) or series
        logger.info(
            "Index market auto-roll: %s -> %s (series=%s, label=%s)",
            current,
            new_ticker,
            new_series,
            row["label"],
        )

        db.execute(
            "UPDATE sentiment_index_markets SET ticker = ?, series_ticker = ? WHERE id = ?",
            (new_ticker, new_series, row["id"]),
        )
        db.commit()

        if current:
            await ws_manager.unsubscribe([current])
        await ws_manager.subscribe([new_ticker])


async def _index_roll_loop() -> None:
    await asyncio.sleep(8)
    while True:
        try:
            await roll_sentiment_index_markets_once()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("sentiment index auto-roll tick failed")
        await asyncio.sleep(30)


async def start_index_auto_roll_worker() -> None:
    global _index_roll_task
    if _index_roll_task is not None and not _index_roll_task.done():
        return
    _index_roll_task = asyncio.create_task(_index_roll_loop())


async def stop_index_auto_roll_worker() -> None:
    global _index_roll_task
    if _index_roll_task is None:
        return
    t = _index_roll_task
    _index_roll_task = None
    t.cancel()
    try:
        await t
    except asyncio.CancelledError:
        pass
