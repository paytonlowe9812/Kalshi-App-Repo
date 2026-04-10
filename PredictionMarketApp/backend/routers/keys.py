from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import ApiKeyCreate, ApiKeyUpdate
from backend.kalshi.client import KalshiClient, set_kalshi_client
from backend.kalshi.websocket import ws_manager, get_all_tickers

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.get("")
def list_keys():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, key_id, is_active, is_demo, last_used, created_at FROM api_keys"
    ).fetchall()
    return [dict(row) for row in rows]


@router.post("")
def add_key(data: ApiKeyCreate):
    db = get_db()
    db.execute(
        "INSERT INTO api_keys (name, key_id, key_secret, is_demo) VALUES (?, ?, ?, ?)",
        (data.name, data.key_id, data.key_secret, int(data.is_demo)),
    )
    db.commit()
    key_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": key_id, "status": "created"}


@router.put("/{id}")
def update_key(id: int, data: ApiKeyUpdate):
    db = get_db()
    row = db.execute("SELECT * FROM api_keys WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Key not found")
    if data.name is not None:
        db.execute("UPDATE api_keys SET name = ? WHERE id = ?", (data.name, id))
    if data.is_active is not None:
        db.execute("UPDATE api_keys SET is_active = ? WHERE id = ?", (int(data.is_active), id))
    db.commit()
    return {"status": "updated"}


@router.delete("/{id}")
def delete_key(id: int):
    db = get_db()
    db.execute("DELETE FROM api_keys WHERE id = ?", (id,))
    db.commit()
    return {"status": "deleted"}


@router.post("/{id}/test")
async def test_key(id: int):
    db = get_db()
    row = db.execute(
        "SELECT key_id, key_secret, is_demo FROM api_keys WHERE id = ?", (id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Key not found")
    client = KalshiClient(row["key_id"], row["key_secret"], bool(row["is_demo"]))
    result = await client.test_connection()
    await client.close()
    return result


@router.post("/{id}/activate")
async def activate_key(id: int):
    db = get_db()
    row = db.execute(
        "SELECT key_id, key_secret, is_demo FROM api_keys WHERE id = ?", (id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Key not found")
    db.execute("UPDATE api_keys SET is_active = 0")
    db.execute("UPDATE api_keys SET is_active = 1 WHERE id = ?", (id,))
    db.execute(
        "UPDATE api_keys SET last_used = datetime('now') WHERE id = ?", (id,)
    )
    db.commit()

    client = KalshiClient(row["key_id"], row["key_secret"], bool(row["is_demo"]))
    set_kalshi_client(client)

    await ws_manager.stop()
    ws_manager.configure(row["key_id"], row["key_secret"], bool(row["is_demo"]))
    await ws_manager.start()
    tickers = get_all_tickers()
    if tickers:
        await ws_manager.subscribe(tickers)

    return {"status": "activated"}
