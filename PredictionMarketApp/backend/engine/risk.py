import logging
from datetime import datetime, timedelta
from backend.database import get_db
from backend.models import RiskLimitError
from backend.kalshi.client import get_kalshi_client

logger = logging.getLogger(__name__)


def _read_position_fp(p: dict) -> float:
    """Read signed position from a Kalshi market_positions entry.
    Current API: 'position_fp' (fixed-point string e.g. '5.00').
    Legacy API:  'position' (integer). +N = YES contracts, -N = NO contracts."""
    for key in ("position_fp", "position"):
        v = p.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0

CIRCUIT_BREAKER_PRICE_THRESHOLD = 0.50
CIRCUIT_BREAKER_ENTRY_THRESHOLD = 0.80


def check_global_limits():
    db = get_db()

    def _setting(key: str) -> str:
        row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else ""

    if _setting("daily_loss_limit_enabled") == "true":
        limit_amount = float(_setting("daily_loss_limit_amount") or 100)
        row = db.execute(
            "SELECT SUM(pnl) as total FROM trade_log WHERE date(logged_at) = date('now')"
        ).fetchone()
        daily_pnl = row["total"] if row and row["total"] else 0.0
        if daily_pnl <= -limit_amount:
            stop_all_bots(f"Daily loss limit of ${limit_amount} hit")
            raise RiskLimitError(f"Daily loss limit of ${limit_amount} hit")

    if _setting("max_open_positions_enabled") == "true":
        max_pos = int(_setting("max_open_positions") or 10)
        client = get_kalshi_client()
        if client:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    pass
            except Exception:
                pass

    if _setting("window_exposure_cap_enabled") == "true":
        cap = int(_setting("window_exposure_cap_contracts") or 30)
        window_start = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
        row = db.execute(
            "SELECT SUM(contracts) as total FROM trade_log WHERE logged_at >= ?",
            (window_start,),
        ).fetchone()
        window_contracts = row["total"] if row and row["total"] else 0
        if window_contracts >= cap:
            raise RiskLimitError("Window exposure cap reached")

    if _setting("circuit_breaker_enabled") == "true":
        if _check_circuit_breaker(db):
            force_close = _setting("circuit_breaker_force_close") == "true"
            if force_close:
                logger.warning("Circuit breaker force close triggered")
            raise RiskLimitError("Circuit breaker triggered")


def _check_circuit_breaker(db) -> bool:
    window_start = (datetime.utcnow() - timedelta(minutes=15)).isoformat()
    rows = db.execute(
        "SELECT entry_price, exit_price, pnl FROM trade_log WHERE logged_at >= ? AND pnl IS NOT NULL",
        (window_start,),
    ).fetchall()
    for r in rows:
        entry = r["entry_price"] or 0
        if entry >= CIRCUIT_BREAKER_ENTRY_THRESHOLD * 100:
            if r["pnl"] and r["pnl"] < 0:
                return True
    return False


def stop_all_bots(reason: str):
    db = get_db()
    db.execute(
        "UPDATE bots SET status = 'stopped', error_message = ? WHERE status = 'running'",
        (reason,),
    )
    db.commit()
    logger.warning(f"All bots stopped: {reason}")


async def close_all_positions():
    client = get_kalshi_client()
    if not client:
        return
    try:
        positions = await client.get_positions()
        for p in positions.get("market_positions", []):
            pos = p.get("position", 0)
            count = abs(pos)
            if count > 0:
                if pos > 0:
                    await client.create_order(
                        ticker=p["ticker"],
                        contract_side="yes",
                        order_action="sell",
                        count=count,
                        type="market",
                    )
                else:
                    await client.create_order(
                        ticker=p["ticker"],
                        contract_side="no",
                        order_action="sell",
                        count=count,
                        type="market",
                    )
    except Exception as e:
        logger.error(f"Failed to close positions: {e}")
    stop_all_bots("Panic button triggered")
