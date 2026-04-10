import logging
from backend.database import get_db
from backend.models import Action
from backend.kalshi.client import get_kalshi_client

logger = logging.getLogger(__name__)


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

    paper_setting = db.execute(
        "SELECT value FROM settings WHERE key = 'paper_trading_mode'"
    ).fetchone()
    is_paper = bool(bot["is_paper"]) or (paper_setting and paper_setting[0] == "true")
    client = get_kalshi_client()
    ticker = bot["market_ticker"]
    cs = _bot_contract_side(bot)

    if action.type == "BUY":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "BUY contracts")
        if not is_paper and client and ticker:
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
            bot_id, bot["name"], ticker, "PAPER_BUY" if is_paper else "BUY",
            contracts, _ref_price(variables, cs), action.fired_line, is_paper,
        )

    elif action.type == "SELL":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "SELL contracts")
        if not is_paper and client and ticker:
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
            bot_id, bot["name"], ticker, "PAPER_SELL" if is_paper else "SELL",
            contracts, _ref_price(variables, cs), action.fired_line, is_paper,
        )

    elif action.type == "LIMIT":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "LIMIT contracts")
        price_cents = _resolve_float(action.price_var, action.price, variables, 50.0, "LIMIT price")
        price = int(price_cents * 100)
        lim_side = (action.side or cs).lower()
        if lim_side not in ("yes", "no"):
            lim_side = cs
        if not is_paper and client and ticker:
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
            f"PAPER_LIMIT_{lim_side.upper()}" if is_paper else f"LIMIT_{lim_side.upper()}",
            contracts, price_cents, action.fired_line, is_paper,
        )

    elif action.type == "CLOSE":
        if not is_paper and client and ticker:
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
            "PAPER_CLOSE" if is_paper else "CLOSE",
            0, 0, action.fired_line, is_paper,
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

    if action.fired_line is not None:
        db.execute(
            "UPDATE rules SET exec_count = exec_count + 1 WHERE bot_id = ? AND line_number = ?",
            (bot_id, action.fired_line),
        )
        db.commit()


def _log_trade(
    bot_id: int, bot_name: str, ticker: str | None, action_str: str,
    contracts: int, price: float, rule_line: int | None, is_paper: bool,
):
    db = get_db()
    db.execute(
        "INSERT INTO trade_log (bot_id, bot_name, market_ticker, action, contracts, "
        "entry_price, rule_line, is_paper) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (bot_id, bot_name, ticker, action_str, contracts, price, rule_line, int(is_paper)),
    )
    db.commit()
