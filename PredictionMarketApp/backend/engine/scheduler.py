import logging
from datetime import datetime
from backend.database import get_db

logger = logging.getLogger(__name__)


def is_trading_window_active() -> bool:
    db = get_db()
    enabled = db.execute(
        "SELECT value FROM settings WHERE key = 'trading_schedule_enabled'"
    ).fetchone()
    if not enabled or enabled[0] != "true":
        return True

    row = db.execute("SELECT COUNT(*) AS c FROM trading_schedule").fetchone()
    if not row or int(row["c"]) == 0:
        # UI can enable the schedule toggle before any rows are saved — do not brick all bots.
        logger.warning(
            "trading_schedule_enabled is true but trading_schedule has no rows; "
            "treating window as open. Add days/windows in CONFIG or turn the toggle off."
        )
        return True

    now = datetime.now()
    day = now.weekday()
    current_time = now.strftime("%H:%M")

    windows = db.execute(
        "SELECT start_time, end_time FROM trading_schedule WHERE day_of_week = ? AND is_enabled = 1",
        (day,),
    ).fetchall()

    if not windows:
        return False

    for w in windows:
        if w["start_time"] <= current_time <= w["end_time"]:
            return True
    return False


def get_loop_interval() -> float:
    db = get_db()
    row = db.execute(
        "SELECT value FROM settings WHERE key = 'loop_interval_ms'"
    ).fetchone()
    ms = int(row[0]) if row else 500
    return ms / 1000.0
