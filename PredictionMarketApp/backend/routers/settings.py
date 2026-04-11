from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import SettingsBulkUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

_LLM_KEY_FIELDS = {
    "strategy_llm_api_key": "strategy_llm_openai_key_configured",
    "strategy_llm_groq_key": "strategy_llm_groq_key_configured",
    "strategy_llm_gemini_key": "strategy_llm_gemini_key_configured",
    "strategy_llm_mistral_key": "strategy_llm_mistral_key_configured",
}


def _coerce_setting_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return str(value)


@router.get("")
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings").fetchall()
    out = {row["key"]: row["value"] for row in rows}

    # Mask all LLM API keys; expose only configured flags
    any_key = False
    for field, flag in _LLM_KEY_FIELDS.items():
        has = bool((out.get(field) or "").strip())
        out[field] = ""
        out[flag] = "true" if has else "false"
        if has:
            any_key = True

    # True if ANY provider key is configured — enables the assistant panel
    out["strategy_llm_key_configured"] = "true" if any_key else "false"

    return out


@router.put("")
def update_settings(data: SettingsBulkUpdate):
    db = get_db()
    for key, value in data.settings.items():
        sk = key if isinstance(key, str) else str(key)
        if sk in ("strategy_llm_key_configured",) or sk.endswith("_key_configured"):
            continue
        sval = _coerce_setting_value(value)
        if sk in _LLM_KEY_FIELDS:
            if not sval.strip():
                continue  # blank = keep existing key
        db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (sk, sval),
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
