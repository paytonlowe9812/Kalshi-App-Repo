import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.models import BotCreate, BotUpdate, BotMove
from backend.kalshi.websocket import ws_manager

router = APIRouter(prefix="/api/bots", tags=["bots"])


SHORT_DURATION_SERIES = {"KXBTC15M", "KXETH15M", "KXSOL15M"}


def _contract_side_value(row) -> str:
    try:
        raw = row["contract_side"]
    except (KeyError, IndexError):
        raw = None
    if raw is None:
        raw = "yes"
    s = str(raw).lower().strip()
    return s if s in ("yes", "no") else "yes"


def _bot_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "group_id": row["group_id"],
        "market_ticker": row["market_ticker"],
        "trigger_type": row["trigger_type"],
        "trigger_value": row["trigger_value"],
        "trigger_time": row["trigger_time"],
        "status": row["status"],
        "is_paper": bool(row["is_paper"]),
        "error_message": row["error_message"],
        "last_run_at": row["last_run_at"],
        "run_count": row["run_count"],
        "sort_order": row["sort_order"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "auto_roll": bool(row["auto_roll"]) if row["auto_roll"] is not None else False,
        "series_ticker": row["series_ticker"] or _infer_series(row["market_ticker"] or "") or None,
        "roll_count": row["roll_count"] if row["roll_count"] is not None else 0,
        "last_roll_at": row["last_roll_at"],
        "contract_side": _contract_side_value(row),
    }


def _infer_series(ticker: str) -> str | None:
    """Extract series ticker from a market ticker (e.g., KXBTC15M-26APR... -> KXBTC15M)."""
    if not ticker:
        return None
    parts = ticker.split("-")
    return parts[0] if parts else None


def _ensure_series_ticker(db, bot_id: int) -> None:
    """Persist series_ticker when missing so auto-roll and API clients stay consistent."""
    row = db.execute(
        "SELECT market_ticker, series_ticker FROM bots WHERE id = ?", (bot_id,)
    ).fetchone()
    if not row or not (row["market_ticker"] or "").strip():
        return
    if row["series_ticker"] and str(row["series_ticker"]).strip():
        return
    inf = _infer_series(row["market_ticker"])
    if inf:
        db.execute(
            "UPDATE bots SET series_ticker = ?, updated_at = datetime('now') WHERE id = ?",
            (inf, bot_id),
        )
        db.commit()


@router.get("")
def list_bots():
    db = get_db()
    rows = db.execute("SELECT * FROM bots ORDER BY sort_order, id").fetchall()
    return [_bot_dict(r) for r in rows]


@router.post("")
def create_bot(data: BotCreate):
    db = get_db()
    series = data.series_ticker or _infer_series(data.market_ticker or "")
    auto_roll = data.auto_roll
    if not auto_roll and series and series in SHORT_DURATION_SERIES:
        auto_roll = True
    cs = (data.contract_side or "yes").lower().strip()
    if cs not in ("yes", "no"):
        cs = "yes"
    db.execute(
        "INSERT INTO bots (name, group_id, market_ticker, trigger_type, trigger_value, "
        "trigger_time, is_paper, auto_roll, series_ticker, contract_side) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data.name,
            data.group_id,
            data.market_ticker,
            data.trigger_type,
            data.trigger_value,
            data.trigger_time,
            int(data.is_paper),
            int(auto_roll),
            series,
            cs,
        ),
    )
    db.commit()
    bot_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return {"id": bot_id, "status": "created"}


@router.get("/{id}/available-variables")
def get_available_variables(id: int):
    db = get_db()
    row = db.execute("SELECT * FROM bots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Bot not found")

    groups = []

    groups.append({
        "label": "MARKET DATA",
        "vars": [
            {"name": "YES_price", "desc": "YES implied price (0-100)"},
            {"name": "NO_price",  "desc": "NO implied price (0-100)"},
            {"name": "Bid",       "desc": "Best bid for your contract side (0-100)"},
            {"name": "Ask",       "desc": "Best ask for your contract side (0-100)"},
            {"name": "LastTraded","desc": "Last traded price (0-100)"},
            {"name": "FillPrice", "desc": "Your entry price on this market"},
            {"name": "TimeToExpiry",      "desc": "Minutes until market expiry"},
            {"name": "DistanceFromStrike","desc": "Distance of current price from strike"},
        ],
    })

    groups.append({
        "label": "PORTFOLIO",
        "vars": [
            {"name": "PositionSize", "desc": "Contracts held in this market"},
            {"name": "DailyPnL",     "desc": "Today's realised P&L"},
        ],
    })

    indexes = db.execute("SELECT * FROM sentiment_indexes").fetchall()
    for idx in indexes:
        markets = db.execute(
            "SELECT * FROM sentiment_index_markets WHERE index_id = ?", (idx["id"],)
        ).fetchall()
        iname = idx['name']
        index_vars: list[dict] = [
            {"name": f"{iname}.Score",     "desc": "Average YES % across all markets in index"},
            {"name": f"{iname}.AvgYES",    "desc": "Average YES implied % in index"},
            {"name": f"{iname}.AvgNO",     "desc": "Average NO implied % in index"},
            {"name": f"{iname}.BullCount", "desc": "Number of markets with YES > 50"},
            {"name": f"{iname}.BearCount", "desc": "Number of markets with YES ≤ 50"},
        ]
        # Per-market vars: duplicate labels in one index overwrite in the engine (last row wins).
        # Dedupe the dropdown the same way; include ticker in description for disambiguation.
        by_name: dict[str, dict] = {}
        for m in markets:
            raw = (m["label"] or "").strip()
            label = raw or (m["ticker"] or "").strip() or "market"
            tkr = (m["ticker"] or "").strip()
            tick = f" [{tkr}]" if tkr else ""
            yes_name = f"{label}.YES"
            no_name = f"{label}.NO"
            by_name[yes_name] = {
                "name": yes_name,
                "desc": f"YES implied %{tick}" if tick else "YES implied %",
                "ticker": tkr or None,
            }
            by_name[no_name] = {
                "name": no_name,
                "desc": f"NO implied %{tick}" if tick else "NO implied %",
                "ticker": tkr or None,
            }
        index_vars.extend(sorted(by_name.values(), key=lambda v: v["name"]))
        if index_vars:
            groups.append({"label": f"INDEX: {idx['name']}", "vars": index_vars})

    user_vars = db.execute(
        "SELECT name, value FROM variables WHERE bot_id = ?", (id,)
    ).fetchall()
    if user_vars:
        groups.append({
            "label": "USER VARIABLES",
            "vars": [{"name": v["name"], "desc": f"= {v['value']}"} for v in user_vars],
        })

    return {"groups": groups}


@router.get("/{id}/live-variables")
async def get_live_variables(id: int):
    """Resolved variable values for the active bot (Kalshi + indexes + user vars)."""
    db = get_db()
    if not db.execute("SELECT 1 FROM bots WHERE id = ?", (id,)).fetchone():
        raise HTTPException(404, "Bot not found")
    from backend.engine.variables import resolve_all
    from backend.kalshi.client import get_kalshi_client

    vals = await resolve_all(id)
    return {
        "bot_id": id,
        "kalshi_client_configured": get_kalshi_client() is not None,
        "variables": vals,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{id}")
def get_bot(id: int):
    db = get_db()
    row = db.execute("SELECT * FROM bots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Bot not found")
    _ensure_series_ticker(db, id)
    row = db.execute("SELECT * FROM bots WHERE id = ?", (id,)).fetchone()
    bot = _bot_dict(row)
    rules = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number", (id,)
    ).fetchall()
    bot["rules"] = [dict(r) for r in rules]
    return bot


@router.put("/{id}")
def update_bot(id: int, data: BotUpdate):
    db = get_db()
    row = db.execute("SELECT * FROM bots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Bot not found")
    updates = []
    params = []
    for field in ["name", "group_id", "market_ticker", "trigger_type", "trigger_value", "trigger_time", "series_ticker"]:
        val = getattr(data, field, None)
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)
    if data.is_paper is not None:
        updates.append("is_paper = ?")
        params.append(int(data.is_paper))
    if data.auto_roll is not None:
        updates.append("auto_roll = ?")
        params.append(int(data.auto_roll))
    if data.contract_side is not None:
        cs = data.contract_side.lower().strip()
        if cs in ("yes", "no"):
            updates.append("contract_side = ?")
            params.append(cs)
    if data.market_ticker is not None and data.series_ticker is None:
        inferred = _infer_series(data.market_ticker)
        if inferred:
            updates.append("series_ticker = ?")
            params.append(inferred)
    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(id)
        db.execute(f"UPDATE bots SET {', '.join(updates)} WHERE id = ?", params)
        db.commit()
    _ensure_series_ticker(db, id)
    return {"status": "updated"}


@router.delete("/{id}")
def delete_bot(id: int):
    db = get_db()
    db.execute("DELETE FROM bots WHERE id = ?", (id,))
    db.commit()
    return {"status": "deleted"}


@router.post("/{id}/start")
async def start_bot(id: int):
    from backend.engine.executor import start_bot_execution

    db = get_db()
    row = db.execute("SELECT * FROM bots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Bot not found")
    if row["market_ticker"]:
        await ws_manager.subscribe([row["market_ticker"]])
    db.execute(
        "UPDATE bots SET status = 'running', error_message = NULL WHERE id = ?",
        (id,),
    )
    db.commit()
    await start_bot_execution(id)
    return {"status": "running"}


@router.post("/{id}/stop")
async def stop_bot(id: int):
    from backend.engine.executor import stop_bot_execution

    db = get_db()
    db.execute("UPDATE bots SET status = 'stopped' WHERE id = ?", (id,))
    db.commit()
    await stop_bot_execution(id)
    return {"status": "stopped"}


@router.post("/{id}/copy")
def copy_bot(id: int):
    db = get_db()
    row = db.execute("SELECT * FROM bots WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(404, "Bot not found")
    db.execute(
        "INSERT INTO bots (name, group_id, market_ticker, trigger_type, trigger_value, "
        "trigger_time, is_paper, auto_roll, series_ticker) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row["name"] + " (Copy)",
            row["group_id"],
            row["market_ticker"],
            row["trigger_type"],
            row["trigger_value"],
            row["trigger_time"],
            row["is_paper"],
            row["auto_roll"],
            row["series_ticker"],
        ),
    )
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    rules = db.execute(
        "SELECT * FROM rules WHERE bot_id = ? ORDER BY line_number", (id,)
    ).fetchall()
    for r in rules:
        db.execute(
            "INSERT INTO rules (bot_id, line_number, line_type, left_operand, operator, right_operand, "
            "action_type, action_params, group_id, group_logic) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id, r["line_number"], r["line_type"], r["left_operand"],
                r["operator"], r["right_operand"], r["action_type"],
                r["action_params"], r["group_id"], r["group_logic"],
            ),
        )
    db.commit()
    return {"id": new_id, "status": "copied"}


@router.post("/{id}/move")
def move_bot(id: int, data: BotMove):
    db = get_db()
    db.execute(
        "UPDATE bots SET group_id = ?, updated_at = datetime('now') WHERE id = ?",
        (data.group_id, id),
    )
    db.commit()
    return {"status": "moved"}
