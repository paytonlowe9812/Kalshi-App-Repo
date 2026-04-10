import csv
import io
import json
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.database import get_db

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def get_logs(
    bot_id: Optional[int] = None,
    market: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    action: Optional[str] = None,
):
    db = get_db()
    where_clauses = []
    params = []
    if bot_id:
        where_clauses.append("bot_id = ?")
        params.append(bot_id)
    if market:
        where_clauses.append("market_ticker = ?")
        params.append(market)
    if from_date:
        where_clauses.append("date(logged_at) >= ?")
        params.append(from_date)
    if to_date:
        where_clauses.append("date(logged_at) <= ?")
        params.append(to_date)
    if action:
        where_clauses.append("action = ?")
        params.append(action)

    where = " AND ".join(where_clauses) if where_clauses else "1=1"
    rows = db.execute(
        f"SELECT * FROM trade_log WHERE {where} ORDER BY logged_at DESC", params
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/export")
def export_logs(
    format: str = "csv",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    db = get_db()
    params = []
    where = "1=1"
    if from_date and to_date:
        where = "date(logged_at) BETWEEN ? AND ?"
        params = [from_date, to_date]

    rows = db.execute(
        f"SELECT * FROM trade_log WHERE {where} ORDER BY logged_at DESC", params
    ).fetchall()
    data = [dict(r) for r in rows]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(data, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=trades.json"},
        )

    output = io.StringIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    content = output.getvalue().encode()
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trades.csv"},
    )
