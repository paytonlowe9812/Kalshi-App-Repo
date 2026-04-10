from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import GroupCreate, GroupUpdate, BulkBotEdit

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("")
def list_groups():
    db = get_db()
    groups = db.execute("SELECT * FROM groups ORDER BY sort_order, id").fetchall()
    result = []
    for g in groups:
        bots = db.execute(
            "SELECT * FROM bots WHERE group_id = ? ORDER BY sort_order, id",
            (g["id"],),
        ).fetchall()
        result.append({
            **dict(g),
            "bots": [dict(b) for b in bots],
        })
    ungrouped = db.execute(
        "SELECT * FROM bots WHERE group_id IS NULL ORDER BY sort_order, id"
    ).fetchall()
    return {
        "groups": result,
        "ungrouped_bots": [dict(b) for b in ungrouped],
    }


@router.post("")
def create_group(data: GroupCreate):
    db = get_db()
    db.execute(
        "INSERT INTO groups (name, parent_id) VALUES (?, ?)",
        (data.name, data.parent_id),
    )
    db.commit()
    gid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": gid, "status": "created"}


@router.put("/{id}")
def update_group(id: int, data: GroupUpdate):
    db = get_db()
    if data.name is not None:
        db.execute("UPDATE groups SET name = ? WHERE id = ?", (data.name, id))
    if data.parent_id is not None:
        db.execute("UPDATE groups SET parent_id = ? WHERE id = ?", (data.parent_id, id))
    db.commit()
    return {"status": "updated"}


@router.delete("/{id}")
def delete_group(id: int, move_bots_to_root: bool = True):
    db = get_db()
    if move_bots_to_root:
        db.execute("UPDATE bots SET group_id = NULL WHERE group_id = ?", (id,))
    else:
        db.execute("DELETE FROM bots WHERE group_id = ?", (id,))
    db.execute("UPDATE groups SET parent_id = NULL WHERE parent_id = ?", (id,))
    db.execute("DELETE FROM groups WHERE id = ?", (id,))
    db.commit()
    return {"status": "deleted"}


@router.post("/{id}/start-all")
async def start_all_in_group(id: int):
    from backend.engine.executor import start_bot_execution

    db = get_db()
    bots = db.execute("SELECT id FROM bots WHERE group_id = ?", (id,)).fetchall()
    for bot in bots:
        db.execute(
            "UPDATE bots SET status = 'running', error_message = NULL WHERE id = ?",
            (bot["id"],),
        )
        db.commit()
        await start_bot_execution(bot["id"])
    return {"status": "started", "count": len(bots)}


@router.post("/{id}/stop-all")
async def stop_all_in_group(id: int):
    from backend.engine.executor import stop_bot_execution

    db = get_db()
    bots = db.execute("SELECT id FROM bots WHERE group_id = ?", (id,)).fetchall()
    for bot in bots:
        db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (bot["id"],))
        db.commit()
        await stop_bot_execution(bot["id"])
    return {"status": "stopped", "count": len(bots)}


@router.put("/{id}/bulk-edit")
def bulk_edit_group(id: int, data: BulkBotEdit):
    db = get_db()
    updates = []
    params = []
    if data.is_paper is not None:
        updates.append("is_paper = ?")
        params.append(int(data.is_paper))
    if data.trigger_type is not None:
        updates.append("trigger_type = ?")
        params.append(data.trigger_type)
    if data.market_ticker is not None:
        updates.append("market_ticker = ?")
        params.append(data.market_ticker)
    if updates:
        params.append(id)
        db.execute(
            f"UPDATE bots SET {', '.join(updates)} WHERE group_id = ?", params
        )
        db.commit()
    return {"status": "updated"}
