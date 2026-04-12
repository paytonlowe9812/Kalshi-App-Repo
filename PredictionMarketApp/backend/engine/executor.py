import asyncio
import logging
import time
from backend.database import get_db
from backend.models import RiskLimitError, InfiniteLoopError
from backend.engine import evaluator, actions
from backend.engine.variables import resolve_all
from backend.engine.risk import check_global_limits
from backend.engine.scheduler import is_trading_window_active, get_loop_interval
from backend.engine.bot_logger import log_event

logger = logging.getLogger(__name__)

_running_tasks: dict[int, asyncio.Task] = {}
_schedule_skip_logged: dict[int, float] = {}
_idle_skip: dict[int, int] = {}
_settlement_task: asyncio.Task | None = None
_auto_roll_task: asyncio.Task | None = None


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
            if status in ("active", "open"):
                return False  # Still live — no roll needed
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
                now = time.time()
                last = _schedule_skip_logged.get(bot_id, 0.0)
                if now - last >= 120.0:
                    _schedule_skip_logged[bot_id] = now
                    logger.warning(
                        "Bot %s: outside CONFIG trading schedule — rules are NOT evaluated and no orders run. "
                        "(VARS / live-variables still updates trend if you open that tab.)",
                        bot_id,
                    )
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
                db = get_db()
                _bot_row = db.execute("SELECT name FROM bots WHERE id = ?", (bot_id,)).fetchone()
                _bot_name = _bot_row["name"] if _bot_row else str(bot_id)
                log_event(
                    bot_id, _bot_name, "INFO", "TICK_FIRED",
                    f"Line {result.fired_line} → {result.action.type}",
                    {"fired_line": result.fired_line, "action": result.action.type,
                     "yes_price": variables.get("YES_price"), "no_price": variables.get("NO_price"),
                     "has_position": variables.get("HasPosition")},
                )
                await actions.execute(bot_id, result.action, variables)
            else:
                _idle_skip[bot_id] = _idle_skip.get(bot_id, 0) + 1
                if _idle_skip[bot_id] % 10 == 0:
                    db = get_db()
                    _bot_row = db.execute("SELECT name FROM bots WHERE id = ?", (bot_id,)).fetchone()
                    _bot_name = _bot_row["name"] if _bot_row else str(bot_id)
                    log_event(bot_id, _bot_name, "DEBUG", "TICK_IDLE", "No condition met", {})

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


async def _global_auto_roll_loop():
    """Every 60 s, check ALL bots with auto_roll=1 — running or stopped.
    If their current ticker is finalized/expired, roll them to the next contract.
    This ensures stopped bots don't wake up with a dead market."""
    while True:
        try:
            db = get_db()
            bots = db.execute(
                "SELECT id FROM bots WHERE auto_roll = 1 AND series_ticker IS NOT NULL AND series_ticker != ''"
            ).fetchall()
            for row in bots:
                try:
                    await _check_auto_roll(row["id"])
                except Exception as e:
                    logger.debug("Global auto-roll bot %s: %s", row["id"], e)
        except Exception as e:
            logger.error("Global auto-roll loop error: %s", e)
        await asyncio.sleep(60)


async def _settlement_loop():
    """Runs every 60 s and back-fills P&L for settled contracts."""
    from backend.engine.settlement_scanner import scan_and_settle
    while True:
        try:
            n = await scan_and_settle()
            if n:
                logger.info("Settlement scanner: updated %d trade_log row(s)", n)
        except Exception as e:
            logger.error("Settlement loop error: %s", e)
        await asyncio.sleep(60)


async def start_scheduler():
    global _settlement_task
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
    # Start background settlement scanner.
    _settlement_task = asyncio.create_task(_settlement_loop())
    logger.info("Settlement scanner started")
    # Start background auto-roll for ALL bots (running or stopped).
    _auto_roll_task = asyncio.create_task(_global_auto_roll_loop())
    logger.info("Global auto-roll loop started")
