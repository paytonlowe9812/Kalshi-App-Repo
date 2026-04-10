from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

from backend.database import get_db
from backend.models import MarketListCreate, MarketListUpdate, MarketListItemAdd

router = APIRouter(prefix="/api/market-lists", tags=["market-lists"])


def _list_dict(db, list_id: int) -> dict:
    row = db.execute("SELECT * FROM market_lists WHERE id = ?", (list_id,)).fetchone()
    if not row:
        return None
    items = db.execute(
        "SELECT ticker, title, sort_order FROM market_list_items "
        "WHERE list_id = ? ORDER BY sort_order, id",
        (list_id,),
    ).fetchall()
    return {
        "id": row["id"],
        "name": row["name"],
        "sort_order": row["sort_order"],
        "items": [dict(i) for i in items],
    }


@router.get("")
def list_market_lists():
    db = get_db()
    rows = db.execute(
        "SELECT id FROM market_lists ORDER BY sort_order, id"
    ).fetchall()
    return [_list_dict(db, r["id"]) for r in rows]


@router.post("")
def create_market_list(data: MarketListCreate):
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(400, "Name is required")
    db = get_db()
    db.execute(
        "INSERT INTO market_lists (name) VALUES (?)",
        (name,),
    )
    db.commit()
    lid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return _list_dict(db, lid)


@router.put("/{list_id}")
def update_market_list(list_id: int, data: MarketListUpdate):
    db = get_db()
    row = db.execute("SELECT id FROM market_lists WHERE id = ?", (list_id,)).fetchone()
    if not row:
        raise HTTPException(404, "List not found")
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(400, "Name cannot be empty")
        db.execute("UPDATE market_lists SET name = ? WHERE id = ?", (name, list_id))
        db.commit()
    return _list_dict(db, list_id)


@router.delete("/{list_id}")
def delete_market_list(list_id: int):
    db = get_db()
    db.execute("DELETE FROM market_lists WHERE id = ?", (list_id,))
    db.commit()
    return {"status": "deleted"}


@router.post("/{list_id}/items")
def add_market_list_item(list_id: int, data: MarketListItemAdd):
    ticker = (data.ticker or "").strip()
    if not ticker:
        raise HTTPException(400, "Ticker is required")
    db = get_db()
    row = db.execute("SELECT id FROM market_lists WHERE id = ?", (list_id,)).fetchone()
    if not row:
        raise HTTPException(404, "List not found")
    title = (data.title or "").strip() or None
    max_so = db.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM market_list_items WHERE list_id = ?",
        (list_id,),
    ).fetchone()["n"]
    db.execute(
        "INSERT INTO market_list_items (list_id, ticker, title, sort_order) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(list_id, ticker) DO UPDATE SET title = COALESCE(excluded.title, market_list_items.title)",
        (list_id, ticker, title, max_so),
    )
    db.commit()
    return _list_dict(db, list_id)


@router.delete("/{list_id}/items/{ticker:path}")
def remove_market_list_item(list_id: int, ticker: str):
    ticker = unquote(ticker).strip()
    db = get_db()
    db.execute(
        "DELETE FROM market_list_items WHERE list_id = ? AND ticker = ?",
        (list_id, ticker),
    )
    db.commit()
    return {"status": "removed"}
