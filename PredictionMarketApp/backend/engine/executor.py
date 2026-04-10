import asyncio
import logging
from backend.database import get_db
from backend.models import RiskLimitError, InfiniteLoopError
from backend.engine import evaluator, actions
from backend.engine.variables import resolve_all
from backend.engine.risk import check_global_limits
from backend.engine.scheduler import is_trading_window_active, get_loop_interval

logger = logging.getLogger(__name__)

_running_tasks: dict[int, asyncio.Task] = {}


def bot_is_running(bot_id: int) -> bool:
    db = get_db()
    row = db.execute("SELECT status FROM bots WHERE id = ?", (bot_id,)).fetchone()
    return row is not None and row["status"] == "running"


async def _check_auto_roll(bot_id: int) -> bool:
    """If the bot's current market is expired/settled and auto_roll is on,
    find the next contract and update the bot's ticker.
    Returns True if a roll happened (caller should skip this loop tick)."""
    db = get_db()
    row = db.execute(
        "SELECT market_ticker, auto_roll, series_ticker FROM bots WHERE id = ?",
        (bot_id,),
    ).fetchone()
    if not row or not row["auto_roll"] or not row["series_ticker"]:
        return False

    from backend.kalshi.client import get_kalshi_client
    client = get_kalshi_client()
    if not client:
        return False

    current_ticker = row["market_ticker"]
    needs_roll = False

    if not current_ticker:
        needs_roll = True
    else:
        try:
            mdata = await client.get_market(current_ticker)
            market = mdata.get("market", mdata)
            status = market.get("status", "")
            if status in ("closed", "settled", "determined", "finalized"):
                needs_roll = True
        except Exception:
            needs_roll = True

    if not needs_roll:
        return False

    try:
        new_ticker = await client.find_next_contract(
            row["series_ticker"], current_ticker
        )
    except Exception as e:
        logger.error(f"Bot {bot_id} auto-roll lookup failed: {e}")
        return False

    if not new_ticker:
        logger.warning(f"Bot {bot_id} auto-roll: no next contract found for {row['series_ticker']}")
        return False

    logger.info(f"Bot {bot_id} auto-roll: {current_ticker} -> {new_ticker}")
    db.execute(
        "UPDATE bots SET market_ticker = ?, roll_count = roll_count + 1, "
        "last_roll_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
        (new_ticker, bot_id),
    )
    db.commit()

    from backend.kalshi.websocket import ws_manager
    await ws_manager.subscribe([new_ticker])

    return True


async def run_bot(bot_id: int):
    logger.info(f"Bot {bot_id} started")
    while bot_is_running(bot_id):
        try:
            if not is_trading_window_active():
                await asyncio.sleep(get_loop_interval())
                continue

            check_global_limits()

            rolled = await _check_auto_roll(bot_id)
            if rolled:
                await asyncio.sleep(1)
                continue

            variables = await resolve_all(bot_id)

            has_none = any(v is None for v in variables.values())
            if has_none:
                logger.warning(f"Bot {bot_id}: waiting for data")
                await asyncio.sleep(get_loop_interval())
                continue

            result = evaluator.evaluate(bot_id, variables)

            if result.action:
                await actions.execute(bot_id, result.action, variables)

            db = get_db()
            db.execute(
                "UPDATE bots SET run_count = run_count + 1, last_run_at = datetime('now') WHERE id = ?",
                (bot_id,),
            )
            db.commit()

        except RiskLimitError as e:
            logger.warning(f"Bot {bot_id} risk limit: {e}")
            db = get_db()
            db.execute(
                "UPDATE bots SET status = 'stopped', error_message = ? WHERE id = ?",
                (str(e), bot_id),
            )
            db.commit()
            break

        except InfiniteLoopError:
            logger.error(f"Bot {bot_id}: infinite loop detected")
            db = get_db()
            db.execute(
                "UPDATE bots SET status = 'error', error_message = 'Infinite loop detected' WHERE id = ?",
                (bot_id,),
            )
            db.commit()
            break

        except Exception as e:
            logger.error(f"Bot {bot_id} error: {e}")
            db = get_db()
            db.execute(
                "UPDATE bots SET error_message = ? WHERE id = ?", (str(e), bot_id)
            )
            db.commit()

        await asyncio.sleep(get_loop_interval())

    logger.info(f"Bot {bot_id} stopped")


async def start_bot_execution(bot_id: int):
    if bot_id in _running_tasks:
        task = _running_tasks[bot_id]
        if not task.done():
            return
    task = asyncio.create_task(run_bot(bot_id))
    _running_tasks[bot_id] = task


async def stop_bot_execution(bot_id: int):
    db = get_db()
    db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot_id,))
    db.commit()
    if bot_id in _running_tasks:
        task = _running_tasks.pop(bot_id)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def stop_all_bots_panic():
    from backend.engine.risk import close_all_positions, stop_all_bots

    stop_all_bots("Panic button triggered")
    await close_all_positions()

    for bot_id in list(_running_tasks.keys()):
        task = _running_tasks.pop(bot_id)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def start_scheduler():
    db = get_db()
    running = db.execute(
        "SELECT id FROM bots WHERE status = 'running'"
    ).fetchall()
    for r in running:
        db.execute(
            "UPDATE bots SET status = 'stopped', error_message = 'Interrupted by restart' WHERE id = ?",
            (r["id"],),
        )
    db.commit()
