from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import ApiKeyCreate, ApiKeyUpdate
from backend.kalshi.client import KalshiClient, set_kalshi_client
from backend.kalshi.websocket import ws_manager, get_all_tickers

router = APIRouter(prefix="/api/keys", tags=["keys"])


async def _apply_kalshi_from_key_row(row) -> None:
    """Point REST + WebSocket clients at production Kalshi API."""
    client = KalshiClient(row["key_id"], row["key_secret"])
    set_kalshi_client(client)
    await ws_manager.stop()
    ws_manager.configure(row["key_id"], row["key_secret"])
    await ws_manager.start()
    tickers = get_all_tickers()
    if tickers:
        await ws_manager.subscribe(tickers)


@router.get("")
def list_keys():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, key_id, is_active, last_used, created_at FROM api_keys"
    ).fetchall()
    return [dict(row) for row in rows]


@router.post("")
def add_key(data: ApiKeyCreate):
    db = get_db()
    db.execute(
        "INSERT INTO api_keys (name, key_id, key_secret, is_demo) VALUES (?, ?, ?, 0)",
        (data.name, data.key_id, data.key_secret),
    )
    db.commit()
    key_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": key_id, "status": "created"}


@router.put("/{id}")
async def update_key(id: int, data: ApiKeyUpdate):
    db = get_db()
    row = db.execute("SELECT * FROM api_keys WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Key not found")
    if data.name is not None:
        db.execute("UPDATE api_keys SET name = ? WHERE id = ?", (data.name, id))
    if data.is_active is not None:
        db.execute("UPDATE api_keys SET is_active = ? WHERE id = ?", (int(data.is_active), id))
    db.commit()

    active = db.execute(
        "SELECT * FROM api_keys WHERE is_active = 1 LIMIT 1"
    ).fetchone()
    if active and int(active["id"]) == int(id):
        row_after = db.execute("SELECT * FROM api_keys WHERE id = ?", (id,)).fetchone()
        if row_after:
            await _apply_kalshi_from_key_row(row_after)

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
    row = db.execute("SELECT * FROM api_keys WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Key not found")
    client = KalshiClient(row["key_id"], row["key_secret"])
    result = await client.test_connection()
    try:
        # Test uses a throwaway client; trading uses get_kalshi_client(). If this row
        # is the active key, install REST + WS so "CONNECTION OK" matches live trading.
        if result.get("valid") and int(row["is_active"] or 0) == 1:
            await _apply_kalshi_from_key_row(row)
    finally:
        await client.close()
    return result


@router.post("/{id}/activate")
async def activate_key(id: int):
    db = get_db()
    row = db.execute("SELECT id FROM api_keys WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Key not found")
    db.execute("UPDATE api_keys SET is_active = 0")
    db.execute("UPDATE api_keys SET is_active = 1 WHERE id = ?", (id,))
    db.execute(
        "UPDATE api_keys SET last_used = datetime('now') WHERE id = ?", (id,)
    )
    db.commit()

    row_after = db.execute("SELECT * FROM api_keys WHERE id = ?", (id,)).fetchone()
    await _apply_kalshi_from_key_row(row_after)

    return {"status": "activated"}
