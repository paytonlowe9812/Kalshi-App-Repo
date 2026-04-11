import json
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import RuleSetUpdate, SnapshotCreate

router = APIRouter(prefix="/api/bots/{bot_id}/rules", tags=["rules"])


@router.get("")
def get_rules(bot_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number", (bot_id,)
    ).fetchall()
    return [dict(r) for r in rows]


@router.put("")
def replace_rules(bot_id: int, data: RuleSetUpdate):
    db = get_db()
    db.execute("DELETE FROM rules WHERE bot_id = ?", (bot_id,))
    for rule in data.rules:
        db.execute(
            "INSERT INTO rules (bot_id, line_number, line_type, left_operand, operator, "
            "right_operand, action_type, action_params, group_id, group_logic) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bot_id, rule.line_number, rule.line_type, rule.left_operand,
                rule.operator, rule.right_operand, rule.action_type,
                rule.action_params, rule.group_id, rule.group_logic,
            ),
        )
    db.commit()
    return {"status": "updated", "count": len(data.rules)}


@router.post("/snapshot")
def create_snapshot(bot_id: int, data: SnapshotCreate):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number", (bot_id,)
    ).fetchall()
    rules_json = json.dumps([dict(r) for r in rows])
    db.execute(
        "INSERT INTO snapshots (bot_id, name, rules_json) VALUES (?, ?, ?)",
        (bot_id, data.name, rules_json),
    )
    db.commit()
    snap_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": snap_id, "status": "snapshot saved"}


@router.get("/snapshots")
def list_snapshots(bot_id: int):
    """Return all snapshots across all bots so any snapshot can be applied to any bot."""
    db = get_db()
    rows = db.execute(
        """
        SELECT s.id, s.bot_id, s.name, s.created_at, b.name AS bot_name
        FROM snapshots s
        LEFT JOIN bots b ON b.id = s.bot_id
        ORDER BY s.bot_id = ? DESC, s.created_at DESC
        """,
        (bot_id,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/snapshots/{snap_id}/restore")
def restore_snapshot(bot_id: int, snap_id: int):
    db = get_db()
    # Allow any snapshot to be applied to any bot (universal snapshots)
    snap = db.execute(
        "SELECT rules_json FROM snapshots WHERE id = ?",
        (snap_id,),
    ).fetchone()
    if not snap:
        raise HTTPException(404, "Snapshot not found")
    rules = json.loads(snap["rules_json"])
    db.execute("DELETE FROM rules WHERE bot_id = ?", (bot_id,))
    for r in rules:
        db.execute(
            "INSERT INTO rules (bot_id, line_number, line_type, left_operand, operator, "
            "right_operand, action_type, action_params, group_id, group_logic) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bot_id, r["line_number"], r["line_type"], r.get("left_operand"),
                r.get("operator"), r.get("right_operand"), r.get("action_type"),
                r.get("action_params"), r.get("group_id"), r.get("group_logic"),
            ),
        )
    db.commit()
    return {"status": "restored"}


@router.delete("/snapshots/{snap_id}")
def delete_snapshot(bot_id: int, snap_id: int):
    """Remove a saved rule snapshot (any bot; snap_id is global)."""
    db = get_db()
    cur = db.execute("DELETE FROM snapshots WHERE id = ?", (snap_id,))
    db.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Snapshot not found")
    return {"status": "deleted"}
