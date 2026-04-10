import csv
import io
import json
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.database import get_db

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/trades")
def export_trades(
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
            headers={"Content-Disposition": "attachment; filename=trades_export.json"},
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
        headers={"Content-Disposition": "attachment; filename=trades_export.csv"},
    )
