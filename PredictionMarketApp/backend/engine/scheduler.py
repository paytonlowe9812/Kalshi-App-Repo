from datetime import datetime
from backend.database import get_db


def is_trading_window_active() -> bool:
    db = get_db()
    enabled = db.execute(
        "SELECT value FROM settings WHERE key = 'trading_schedule_enabled'"
    ).fetchone()
    if not enabled or enabled[0] != "true":
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
