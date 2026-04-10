from fastapi import APIRouter
from backend.database import get_db
from backend.models import VariableUpdate

router = APIRouter(prefix="/api/bots/{bot_id}/variables", tags=["variables"])


@router.get("")
def get_variables(bot_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT name, value FROM variables WHERE bot_id = ?", (bot_id,)
    ).fetchall()
    return {r["name"]: r["value"] for r in rows}


@router.put("")
def update_variables(bot_id: int, data: VariableUpdate):
    db = get_db()
    for name, value in data.variables.items():
        db.execute(
            "INSERT OR REPLACE INTO variables (bot_id, name, value) VALUES (?, ?, ?)",
            (bot_id, name, value),
        )
    db.commit()
    return {"status": "updated"}
