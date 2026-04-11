from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import SettingsBulkUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    out = {row["key"]: row["value"] for row in rows}
    # Never expose LLM API key to the frontend (localhost app still uses browser).
    has_llm = bool((out.get("strategy_llm_api_key") or "").strip())
    out["strategy_llm_api_key"] = ""
    out["strategy_llm_key_configured"] = "true" if has_llm else "false"
    return out


@router.put("")
def update_settings(data: SettingsBulkUpdate):
    db = get_db()
    for key, value in data.settings.items():
        if key == "strategy_llm_key_configured":
            continue
        if key == "strategy_llm_api_key":
            v = (value or "").strip()
            if not v:
                continue
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value) if value is not None else ""),
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
