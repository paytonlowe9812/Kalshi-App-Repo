from typing import Optional
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.kalshi.client import get_kalshi_client

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/summary")
async def portfolio_summary():
    db = get_db()
    client = get_kalshi_client()

    total_value = 0.0
    today_pnl = 0.0
    if client:
        try:
            balance = await client.get_balance()
            total_value = balance.get("balance", 0) / 100.0
        except Exception:
            pass

    logs_today = db.execute(
        "SELECT SUM(pnl) as total FROM trade_log WHERE date(logged_at) = date('now')"
    ).fetchone()
    today_pnl = logs_today["total"] or 0.0

    total_trades = db.execute("SELECT COUNT(*) as c FROM trade_log").fetchone()["c"]
    wins = db.execute("SELECT COUNT(*) as c FROM trade_log WHERE pnl > 0").fetchone()["c"]
    win_rate = round((wins / total_trades * 100) if total_trades > 0 else 0, 1)

    best = db.execute(
        "SELECT date(logged_at) as d, SUM(pnl) as total FROM trade_log GROUP BY d ORDER BY total DESC LIMIT 1"
    ).fetchone()
    worst = db.execute(
        "SELECT date(logged_at) as d, SUM(pnl) as total FROM trade_log GROUP BY d ORDER BY total ASC LIMIT 1"
    ).fetchone()

    return {
        "total_value": total_value,
        "today_pnl": today_pnl,
        "win_rate": win_rate,
        "total_trades": total_trades,
        "wins": wins,
        "best_day": {"date": best["d"], "pnl": best["total"]} if best and best["total"] else None,
        "worst_day": {"date": worst["d"], "pnl": worst["total"]} if worst and worst["total"] else None,
    }


@router.get("/chart")
def portfolio_chart(
    range: str = "today",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    breakdown: Optional[int] = None,
):
    db = get_db()
    where = "1=1"
    params = []

    if range == "today":
        where = "date(logged_at) = date('now')"
    elif from_date and to_date:
        where = "date(logged_at) BETWEEN ? AND ?"
        params = [from_date, to_date]

    if breakdown:
        rows = db.execute(
            f"SELECT bot_id, bot_name, date(logged_at) as date, SUM(pnl) as pnl "
            f"FROM trade_log WHERE {where} GROUP BY bot_id, date ORDER BY date",
            params,
        ).fetchall()
    else:
        rows = db.execute(
            f"SELECT date(logged_at) as date, SUM(pnl) as pnl "
            f"FROM trade_log WHERE {where} GROUP BY date ORDER BY date",
            params,
        ).fetchall()

    return [dict(r) for r in rows]


@router.get("/positions")
async def get_positions():
    client = get_kalshi_client()
    if not client:
        return {"positions": []}
    try:
        return await client.get_positions()
    except Exception as e:
        raise HTTPException(502, f"Kalshi API error: {e}")
