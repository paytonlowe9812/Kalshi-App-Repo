from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import SettingsBulkUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


@router.put("")
def update_settings(data: SettingsBulkUpdate):
    db = get_db()
    for key, value in data.settings.items():
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
    db.commit()
    return {"status": "ok"}


@router.get("/first-launch")
def get_first_launch():
    db = get_db()
    row = db.execute(
        "SELECT value FROM settings WHERE key = 'first_launch'"
    ).fetchone()
    return {"first_launch": row and row[0] == "true"}


@router.post("/panic")
async def panic_stop():
    from backend.engine.executor import stop_all_bots_panic

    await stop_all_bots_panic()
    return {"status": "all bots stopped, positions closing"}
