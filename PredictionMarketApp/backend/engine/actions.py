import asyncio
import logging
import time

from backend.database import get_db
from backend.models import Action
from backend.kalshi.client import get_kalshi_client, kalshi_iso_to_unix

logger = logging.getLogger(__name__)

# Upper bound so a rule cannot stall the bot for hours by mistake.
_MAX_PAUSE_MS = 3_600_000


def _resolve_ms(var_key: str | None, literal, variables: dict, fallback: int, label: str) -> int:
    """Milliseconds for PAUSE; clamped to [0, _MAX_PAUSE_MS]."""
    key = (str(var_key or "")).strip()
    if key:
        if key in variables:
            try:
                v = int(round(float(variables[key])))
                return max(0, min(v, _MAX_PAUSE_MS))
            except (TypeError, ValueError):
                pass
        logger.warning("%s variable %r missing or not numeric; using %d ms", label, key, fallback)
        return max(0, min(int(fallback), _MAX_PAUSE_MS))
    if literal is None:
        return max(0, min(int(fallback), _MAX_PAUSE_MS))
    try:
        v = int(round(float(literal)))
        return max(0, min(v, _MAX_PAUSE_MS))
    except (TypeError, ValueError):
        return max(0, min(int(fallback), _MAX_PAUSE_MS))


def _bot_contract_side(bot) -> str:
    raw = dict(bot).get("contract_side")
    s = str(raw or "yes").lower().strip()
    return s if s in ("yes", "no") else "yes"


def _ref_price(variables: dict, contract_side: str) -> float:
    if contract_side == "no":
        return float(variables.get("NO_price", 0))
    return float(variables.get("YES_price", 0))


def _resolve_int(var_key: str | None, literal, variables: dict, fallback: int, label: str) -> int:
    """Resolve an int param: try variable first, then literal, then fallback."""
    key = (str(var_key or "")).strip()
    if key:
        if key in variables:
            try:
                return max(1, int(round(float(variables[key]))))
            except (TypeError, ValueError):
                pass
        logger.warning("%s variable %r missing or not numeric; using %d", label, key, fallback)
        return fallback
    if literal is None:
        return fallback
    try:
        return max(1, int(round(float(literal))))
    except (TypeError, ValueError):
        return fallback


def _resolve_float(var_key: str | None, literal, variables: dict, fallback: float, label: str) -> float:
    """Resolve a float param: try variable first, then literal, then fallback."""
    key = (str(var_key or "")).strip()
    if key:
        if key in variables:
            try:
                return float(variables[key])
            except (TypeError, ValueError):
                pass
        logger.warning("%s variable %r missing or not numeric; using %s", label, key, fallback)
        return fallback
    if literal is None:
        return fallback
    try:
        return float(literal)
    except (TypeError, ValueError):
        return fallback


async def execute(bot_id: int, action: Action, variables: dict):
    db = get_db()
    bot = db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
    if not bot:
        return

    client = get_kalshi_client()
    ticker = bot["market_ticker"]
    cs = _bot_contract_side(bot)

    if action.type == "BUY":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "BUY contracts")
        if client and ticker:
            try:
                await client.create_order(
                    ticker=ticker,
                    contract_side=cs,
                    order_action="buy",
                    count=contracts,
                    type="market",
                )
            except Exception as e:
                logger.error(f"Order failed: {e}")
        _log_trade(
            bot_id, bot["name"], ticker, "BUY",
            contracts, _ref_price(variables, cs), action.fired_line,
        )

    elif action.type == "SELL":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "SELL contracts")
        if client and ticker:
            try:
                await client.create_order(
                    ticker=ticker,
                    contract_side=cs,
                    order_action="sell",
                    count=contracts,
                    type="market",
                )
            except Exception as e:
                logger.error(f"Order failed: {e}")
        _log_trade(
            bot_id, bot["name"], ticker, "SELL",
            contracts, _ref_price(variables, cs), action.fired_line,
        )

    elif action.type == "LIMIT":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "LIMIT contracts")
        price_cents = _resolve_float(action.price_var, action.price, variables, 50.0, "LIMIT price")
        price = int(price_cents * 100)
        lim_side = (action.side or cs).lower()
        if lim_side not in ("yes", "no"):
            lim_side = cs
        if client and ticker:
            try:
                await client.create_order(
                    ticker=ticker,
                    contract_side=lim_side,
                    order_action="buy",
                    count=contracts,
                    type="limit",
                    price=price,
                )
            except Exception as e:
                logger.error(f"Limit order failed: {e}")
        _log_trade(
            bot_id, bot["name"], ticker,
            f"LIMIT_{lim_side.upper()}",
            contracts, price_cents, action.fired_line,
        )

    elif action.type == "CLOSE":
        if client and ticker:
            try:
                positions = await client.get_positions()
                for p in positions.get("market_positions", []):
                    if p.get("ticker") == ticker:
                        pos = p.get("position", 0)
                        count = abs(pos)
                        if count > 0:
                            if pos > 0:
                                await client.create_order(
                                    ticker=ticker,
                                    contract_side="yes",
                                    order_action="sell",
                                    count=count,
                                    type="market",
                                )
                            else:
                                await client.create_order(
                                    ticker=ticker,
                                    contract_side="no",
                                    order_action="sell",
                                    count=count,
                                    type="market",
                                )
                        break
            except Exception as e:
                logger.error(f"Close failed: {e}")
        _log_trade(
            bot_id, bot["name"], ticker,
            "CLOSE",
            0, 0, action.fired_line,
        )

    elif action.type == "SET_VAR":
        if action.var_name and action.value is not None:
            db.execute(
                "INSERT OR REPLACE INTO variables (bot_id, name, value) VALUES (?, ?, ?)",
                (bot_id, action.var_name, str(action.value)),
            )
            db.commit()

    elif action.type == "STOP":
        db.execute(
            "UPDATE bots SET status = 'stopped', updated_at = datetime('now') WHERE id = ?",
            (bot_id,),
        )
        db.commit()

    elif action.type in ("LOG", "ALERT"):
        logger.info(f"Bot {bot_id} {action.type}: {action.message}")

    elif action.type == "NOOP":
        pass

    elif action.type == "PAUSE":
        ms = _resolve_ms(action.ms_var, action.ms, variables, 0, "PAUSE")
        if ms > 0:
            await asyncio.sleep(ms / 1000.0)

    elif action.type == "CANCEL_STALE":
        max_age = _resolve_ms(
            action.max_age_ms_var,
            action.max_age_ms,
            variables,
            60_000,
            "CANCEL_STALE max_age_ms",
        )
        n_cancel = 0
        if client and ticker and max_age >= 0:
            try:
                data = await client.get_orders(ticker=ticker, status="resting", limit=200)
                now = time.time()
                for o in data.get("orders") or []:
                    if (o.get("type") or "").lower() != "limit":
                        continue
                    oid = o.get("order_id")
                    if not oid:
                        continue
                    ts = kalshi_iso_to_unix(o.get("created_time"))
                    if ts is None:
                        continue
                    age_ms = (now - ts) * 1000.0
                    if age_ms >= max_age:
                        try:
                            await client.cancel_order(oid)
                            n_cancel += 1
                        except Exception as e:
                            logger.warning("Cancel order %s failed: %s", oid, e)
            except Exception as e:
                logger.error("CANCEL_STALE: %s", e)
        if n_cancel > 0:
            _log_trade(
                bot_id,
                bot["name"],
                ticker,
                "CANCEL_STALE",
                n_cancel,
                0.0,
                action.fired_line,
            )

    if action.fired_line is not None:
        db.execute(
            "UPDATE rules SET exec_count = exec_count + 1 WHERE bot_id = ? AND line_number = ?",
            (bot_id, action.fired_line),
        )
        db.commit()


def _log_trade(
    bot_id: int, bot_name: str, ticker: str | None, action_str: str,
    contracts: int, price: float, rule_line: int | None,
):
    db = get_db()
    db.execute(
        "INSERT INTO trade_log (bot_id, bot_name, market_ticker, action, contracts, "
        "entry_price, rule_line, is_paper) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
        (bot_id, bot_name, ticker, action_str, contracts, price, rule_line),
    )
    db.commit()
