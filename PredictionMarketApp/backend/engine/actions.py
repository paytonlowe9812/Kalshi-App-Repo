import asyncio
import logging
import time
import json

import httpx

from backend.database import get_db
from backend.models import Action
from backend.kalshi.client import get_kalshi_client, kalshi_iso_to_unix
from backend.engine.bot_logger import log_event
from backend.engine.position_tracker import record_entry, record_exit

logger = logging.getLogger(__name__)

# Upper bound so a rule cannot stall the bot for hours by mistake.
_MAX_PAUSE_MS = 3_600_000

# ── Order-placement cooldown ──────────────────────────────────────────────────
# Root cause: Kalshi's positions/orders API typically takes 1–4 seconds to
# reflect a just-placed order. During that window every loop tick still sees
# HasPosition=0 / RestingLimitCount=0 and would fire another duplicate order.
#
# Fix: after placing any order, record the timestamp in-process.  The next
# tick's execute() checks this BEFORE calling Kalshi's live API:
#   BUY / LIMIT  — block for 10 s (Kalshi can take 3-4 s to show new position)
#   SELL         — block for 3 s only (exits should be fast; position clears
#                  more quickly after a fill)
#   SELL bypass  — if TimeToExpiry < 1 min the cooldown is waived entirely so
#                  emergency exits always reach the exchange
_BUY_LIMIT_COOLDOWN_SEC = 10.0
_SELL_COOLDOWN_SEC = 3.0
_last_order_placed: dict[int, float] = {}  # bot_id -> time.monotonic()


def _in_buy_limit_cooldown(bot_id: int) -> bool:
    ts = _last_order_placed.get(bot_id, 0.0)
    elapsed = time.monotonic() - ts
    if elapsed < _BUY_LIMIT_COOLDOWN_SEC:
        logger.debug(
            "Bot %s: BUY/LIMIT cooldown active (%.1fs remaining)",
            bot_id, _BUY_LIMIT_COOLDOWN_SEC - elapsed,
        )
        return True
    return False


def _in_sell_cooldown(bot_id: int, variables: dict) -> bool:
    """Sell cooldown with emergency bypass when expiry is imminent."""
    # Emergency bypass: never block a SELL when market expires in < 60 seconds
    tte = _var_float(variables, "TimeToExpiry", 999.0)
    if tte < 1.0:  # < 1 minute to expiry — always allow exit
        return False
    ts = _last_order_placed.get(bot_id, 0.0)
    elapsed = time.monotonic() - ts
    if elapsed < _SELL_COOLDOWN_SEC:
        logger.debug(
            "Bot %s: SELL cooldown active (%.1fs remaining)",
            bot_id, _SELL_COOLDOWN_SEC - elapsed,
        )
        return True
    return False


def _record_order_placed(bot_id: int) -> None:
    _last_order_placed[bot_id] = time.monotonic()


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


def _buy_fill_price(variables: dict) -> float:
    """Best estimate of the actual fill price for a market BUY.
    For a YES/NO bot, Bid/Ask are already flipped to the bot's own side in variables.py.
    A market buy fills at the ask (best offer), so use Ask."""
    ask = variables.get("Ask")
    if ask is not None:
        try:
            v = float(ask)
            if 0 < v < 100:
                return v
        except (TypeError, ValueError):
            pass
    # fallback: mid price
    return float(variables.get("YES_price") or variables.get("NO_price") or 0)


def _sell_fill_price(variables: dict) -> float:
    """Best estimate of the actual fill price for a market SELL.
    A market sell fills at the bid (best bid), so use Bid."""
    bid = variables.get("Bid")
    if bid is not None:
        try:
            v = float(bid)
            if 0 < v < 100:
                return v
        except (TypeError, ValueError):
            pass
    return float(variables.get("YES_price") or variables.get("NO_price") or 0)


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


def _position_fp(p: dict) -> float:
    """Read signed position from a Kalshi market_positions entry.
    Current API uses 'position_fp' (fixed-point string, e.g. '5.00').
    Legacy API used 'position' (integer). Try both.
    +N = N YES contracts, -N = N NO contracts."""
    for key in ("position_fp", "position"):
        v = p.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def _var_float(variables: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(variables.get(key, default))
    except (TypeError, ValueError):
        return default


def _has_market_position(variables: dict) -> bool:
    """True if Kalshi reports any net position on this bot market (see variables.resolve_all)."""
    if _var_float(variables, "HasPosition", 0) >= 0.5:
        return True
    return abs(_var_float(variables, "PositionSize", 0)) > 1e-9


def _has_resting_limit(variables: dict) -> bool:
    return int(round(_var_float(variables, "RestingLimitCount", 0))) > 0


async def _exchange_position_and_resting(client, ticker: str) -> tuple[bool, int]:
    """Live Kalshi read for this ticker: (has_open_position, resting_limit_count).

    Rule variables are resolved once per bot loop tick; orders can appear on the exchange
    before the next resolve_all(), so vars may still show HasPosition=0 and RestingLimitCount=0
    for several hundred ms. Refresh here immediately before submit to stop duplicate orders.
    """
    has_pos = False
    resting = 0
    if not client or not ticker:
        return has_pos, resting
    try:
        positions = await client.get_positions()
        for p in positions.get("market_positions", []) or []:
            if (p.get("ticker") or "") != ticker:
                continue
            pos = _position_fp(p)
            if abs(pos) > 1e-9:
                has_pos = True
            break
        odata = await client.get_orders(ticker=ticker, status="resting", limit=200)
        for o in odata.get("orders", []) or []:
            if (o.get("type") or "").lower() == "limit":
                resting += 1
    except Exception as e:
        logger.debug("Live position/resting refresh failed: %s", e)
    return has_pos, resting


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


def _limit_action_from_rule_params(action_params: str | None) -> str:
    """Best-effort parse of LIMIT direction from stored action_params JSON."""
    try:
        params = json.loads(action_params or "{}")
    except (TypeError, ValueError):
        params = {}
    raw_action = str(params.get("order_action") or "").strip().lower()
    if raw_action in ("buy", "sell"):
        return raw_action
    # Backward compatibility for very old rules that encoded direction in "side".
    raw_side = str(params.get("side") or "").strip().lower()
    if raw_side in ("yes", "no"):
        return "sell" if raw_side == "no" else "buy"
    return ""


def _resolve_limit_order_action(db, bot_id: int, action: Action) -> str:
    """
    Resolve LIMIT buy/sell direction robustly.

    Primary source is action.order_action from evaluator parse.
    If that is missing/invalid, re-read action_params for fired_line from DB so
    execution still honors saved rule direction.
    """
    raw = str(action.order_action or "").strip().lower()
    if action.fired_line is not None:
        row = db.execute(
            "SELECT action_params FROM rules WHERE bot_id = ? AND line_number = ? LIMIT 1",
            (bot_id, action.fired_line),
        ).fetchone()
        if row:
            recovered = _limit_action_from_rule_params(row["action_params"])
            if recovered in ("buy", "sell"):
                return recovered
    if raw in ("buy", "sell"):
        return raw
    return "buy"


def _resting_limit_is_buy(order: dict) -> bool:
    """
    True only when a resting limit order is explicitly a BUY.

    Safety rule: if order direction is missing/unknown, treat it as non-buy so
    CANCEL_STALE never cancels LIMIT SELL exits by accident.
    """
    raw_action = str(order.get("action") or order.get("order_action") or "").strip().lower()
    if raw_action in ("buy", "sell"):
        return raw_action == "buy"
    return False


async def execute(bot_id: int, action: Action, variables: dict):
    db = get_db()
    bot = db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
    if not bot:
        return

    client = get_kalshi_client()
    ticker = bot["market_ticker"]
    cs = _bot_contract_side(bot)
    # Bump exec_count only when something real happened (avoids x33 from repeated THEN hits).
    count_this_line = False

    def _api_err_msg(exc: BaseException) -> str:
        if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
            try:
                return f"{exc.response.status_code} {exc.response.text[:400]}"
            except Exception:
                pass
        return str(exc)

    if action.type == "BUY":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "BUY contracts")
        sent = False
        bot_name = dict(bot).get("name", "")
        if _in_buy_limit_cooldown(bot_id):
            log_event(bot_id, bot_name, "DEBUG", "SKIPPED_COOLDOWN",
                      "BUY cooldown active — skipping", {"action": "BUY"})
        else:
            live_pos, live_resting = await _exchange_position_and_resting(client, ticker)
            if _has_market_position(variables) or live_pos:
                logger.debug("Bot %s BUY skipped: position on %s (vars or live API)", bot_id, ticker)
                log_event(bot_id, bot_name, "DEBUG", "SKIPPED_GUARD",
                          f"BUY skipped: already positioned on {ticker}", {"action": "BUY"})
            elif live_resting > 0:
                logger.debug(
                    "Bot %s BUY skipped: %s resting limit(s) on %s (live API; vars can lag)",
                    bot_id, live_resting, ticker,
                )
                log_event(bot_id, bot_name, "DEBUG", "SKIPPED_GUARD",
                          f"BUY skipped: resting limit(s) on {ticker}", {"action": "BUY", "resting": live_resting})
            elif client and ticker:
                try:
                    await client.create_order(
                        ticker=ticker, contract_side=cs,
                        order_action="buy", count=contracts, type="market",
                    )
                    sent = True
                except Exception as e:
                    logger.error("BUY order failed: %s", _api_err_msg(e))
                    log_event(bot_id, bot_name, "ERROR", "ORDER_ERROR",
                              f"BUY order failed: {_api_err_msg(e)}", {"action": "BUY", "ticker": ticker})
            else:
                if not client:
                    logger.warning("BUY skipped: no active Kalshi API key.")
                elif not ticker:
                    logger.warning("BUY skipped: bot has no market_ticker.")
        if sent:
            _record_order_placed(bot_id)
            record_entry(bot_id, ticker, contracts)
            count_this_line = True
            log_event(bot_id, bot_name, "INFO", "ORDER_PLACED",
                      f"BUY {contracts} @ market  [{ticker}]",
                      {"action": "BUY", "contracts": contracts, "ticker": ticker})
            _log_trade(bot_id, bot["name"], ticker, "BUY",
                       contracts, _buy_fill_price(variables), action.fired_line)

    elif action.type == "SELL":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "SELL contracts")
        sent = False
        bot_name = dict(bot).get("name", "")
        if _in_sell_cooldown(bot_id, variables):
            log_event(bot_id, bot_name, "DEBUG", "SKIPPED_COOLDOWN",
                      "SELL cooldown active — skipping", {"action": "SELL"})
        else:
            live_pos, _ = await _exchange_position_and_resting(client, ticker)
            if not _has_market_position(variables) and not live_pos:
                logger.debug("Bot %s SELL skipped: flat on %s (vars and live API)", bot_id, ticker)
                log_event(bot_id, bot_name, "DEBUG", "SKIPPED_GUARD",
                          f"SELL skipped: no position on {ticker}", {"action": "SELL"})
            elif client and ticker:
                try:
                    await client.create_order(
                        ticker=ticker, contract_side=cs,
                        order_action="sell", count=contracts, type="market",
                    )
                    sent = True
                except Exception as e:
                    logger.error("SELL order failed: %s", _api_err_msg(e))
                    log_event(bot_id, bot_name, "ERROR", "ORDER_ERROR",
                              f"SELL order failed: {_api_err_msg(e)}", {"action": "SELL", "ticker": ticker})
            else:
                if not client:
                    logger.warning("SELL skipped: no active Kalshi API key.")
                elif not ticker:
                    logger.warning("SELL skipped: bot has no market_ticker.")
        if sent:
            _record_order_placed(bot_id)
            record_exit(bot_id, ticker)
            count_this_line = True
            log_event(bot_id, bot_name, "INFO", "ORDER_PLACED",
                      f"SELL {contracts} @ market  [{ticker}]",
                      {"action": "SELL", "contracts": contracts, "ticker": ticker})
            _log_trade(bot_id, bot["name"], ticker, "SELL",
                       contracts, _sell_fill_price(variables), action.fired_line)

    elif action.type == "LIMIT":
        contracts = _resolve_int(action.contracts_var, action.contracts, variables, 1, "LIMIT contracts")
        price_cents = _resolve_float(action.price_var, action.price, variables, 50.0, "LIMIT price")
        try:
            off = float(action.price_offset) if action.price_offset is not None else 0.0
        except (TypeError, ValueError):
            off = 0.0
        price_cents = price_cents + off
        api_price = max(1, min(99, int(round(price_cents))))
        # contract_side: which side of the binary (yes/no) — from action.side or bot default
        lim_side = (action.side or cs).lower()
        if lim_side not in ("yes", "no"):
            lim_side = cs
        # order_action: buy (entering) or sell (exiting) — from action.order_action
        lim_action = _resolve_limit_order_action(db, bot_id, action)
        is_sell_limit = (lim_action == "sell")
        sent = False
        bot_name = dict(bot).get("name", "")
        if not is_sell_limit and _in_buy_limit_cooldown(bot_id):
            log_event(bot_id, bot_name, "DEBUG", "SKIPPED_COOLDOWN",
                      "BUY/LIMIT cooldown active — skipping", {"action": "LIMIT"})
        else:
            live_pos, live_resting = await _exchange_position_and_resting(client, ticker)
            if is_sell_limit:
                # Sell limit — only makes sense when we have a position to exit
                if not _has_market_position(variables) and not live_pos:
                    logger.debug("Bot %s LIMIT SELL skipped: no position on %s", bot_id, ticker)
                    log_event(bot_id, bot_name, "DEBUG", "SKIPPED_GUARD",
                              f"LIMIT SELL skipped: no position on {ticker}", {"action": "LIMIT_SELL"})
                elif client and ticker:
                    try:
                        await client.create_order(
                            ticker=ticker, contract_side=lim_side,
                            order_action="sell", count=contracts,
                            type="limit", price=api_price,
                        )
                        sent = True
                    except Exception as e:
                        logger.error("Limit sell order failed: %s", _api_err_msg(e))
                        log_event(bot_id, bot_name, "ERROR", "ORDER_ERROR",
                                  f"LIMIT SELL order failed: {_api_err_msg(e)}",
                                  {"action": "LIMIT_SELL", "ticker": ticker, "price": api_price})
            else:
                # Buy limit — skip if already positioned or already have a resting limit
                if _has_market_position(variables) or live_pos:
                    logger.debug("Bot %s LIMIT BUY skipped: position on %s", bot_id, ticker)
                    log_event(bot_id, bot_name, "DEBUG", "SKIPPED_GUARD",
                              f"LIMIT BUY skipped: already positioned on {ticker}", {"action": "LIMIT"})
                elif _has_resting_limit(variables) or live_resting > 0:
                    logger.debug("Bot %s LIMIT BUY skipped: resting limit on %s", bot_id, ticker)
                    log_event(bot_id, bot_name, "DEBUG", "SKIPPED_GUARD",
                              f"LIMIT skipped: resting limit already on {ticker}", {"action": "LIMIT"})
                elif client and ticker:
                    try:
                        await client.create_order(
                            ticker=ticker, contract_side=lim_side,
                            order_action="buy", count=contracts,
                            type="limit", price=api_price,
                        )
                        sent = True
                    except Exception as e:
                        logger.error("Limit buy order failed: %s", _api_err_msg(e))
                        log_event(bot_id, bot_name, "ERROR", "ORDER_ERROR",
                                  f"LIMIT order failed: {_api_err_msg(e)}",
                                  {"action": "LIMIT", "ticker": ticker, "price": api_price, "side": lim_side})
                else:
                    if not client:
                        logger.warning("LIMIT skipped: no active Kalshi API key.")
                    elif not ticker:
                        logger.warning("LIMIT skipped: bot has no market_ticker.")
        if sent:
            if is_sell_limit:
                _record_order_placed(bot_id)
                record_exit(bot_id, ticker)
                count_this_line = True
                log_event(bot_id, bot_name, "INFO", "ORDER_PLACED",
                          f"LIMIT SELL {contracts} @ {api_price}¢  [{ticker}]",
                          {"action": "LIMIT_SELL", "contracts": contracts, "price": api_price, "ticker": ticker})
                _log_trade(bot_id, bot["name"], ticker, f"LIMIT_{lim_side.upper()}_SELL",
                           contracts, float(api_price), action.fired_line)
            else:
                _record_order_placed(bot_id)
                record_entry(bot_id, ticker, contracts)
                count_this_line = True
                log_event(bot_id, bot_name, "INFO", "ORDER_PLACED",
                          f"LIMIT BUY {contracts} @ {api_price}¢  [{ticker}]  side={lim_side}",
                          {"action": "LIMIT", "contracts": contracts, "price": api_price, "side": lim_side, "ticker": ticker})
                _log_trade(bot_id, bot["name"], ticker, f"LIMIT_{lim_side.upper()}",
                           contracts, float(api_price), action.fired_line)

    elif action.type == "CLOSE":
        close_orders = 0
        if client and ticker:
            try:
                positions = await client.get_positions()
                for p in positions.get("market_positions", []):
                    if p.get("ticker") == ticker:
                        pos = _position_fp(p)
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
                            close_orders += 1
                        break
            except Exception as e:
                logger.error("Close failed: %s", _api_err_msg(e))
        else:
            if not client:
                logger.warning("CLOSE skipped: no active Kalshi API key.")
            elif not ticker:
                logger.warning("CLOSE skipped: bot has no market_ticker.")
        if close_orders > 0:
            _record_order_placed(bot_id)
            record_exit(bot_id, ticker)
            count_this_line = True
            _log_trade(
                bot_id, bot["name"], ticker,
                "CLOSE",
                0, 0, action.fired_line,
            )

    elif action.type == "SET_VAR":
        if action.var_name and action.value is not None:
            count_this_line = True
            db.execute(
                "INSERT OR REPLACE INTO variables (bot_id, name, value) VALUES (?, ?, ?)",
                (bot_id, action.var_name, str(action.value)),
            )
            db.commit()

    elif action.type == "STOP":
        count_this_line = True
        db.execute(
            "UPDATE bots SET status = 'stopped', updated_at = datetime('now') WHERE id = ?",
            (bot_id,),
        )
        db.commit()

    elif action.type in ("LOG", "ALERT"):
        count_this_line = True
        logger.info(f"Bot {bot_id} {action.type}: {action.message}")

    elif action.type == "NOOP":
        count_this_line = True
        pass

    elif action.type == "PAUSE":
        ms = _resolve_ms(action.ms_var, action.ms, variables, 0, "PAUSE")
        if ms > 0:
            count_this_line = True
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
                    if not _resting_limit_is_buy(o):
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
            count_this_line = True
            _log_trade(
                bot_id,
                bot["name"],
                ticker,
                "CANCEL_STALE",
                n_cancel,
                0.0,
                action.fired_line,
            )

    if action.fired_line is not None and count_this_line:
        db.execute(
            "UPDATE rules SET exec_count = exec_count + 1 WHERE bot_id = ? AND line_number = ?",
            (bot_id, action.fired_line),
        )
        db.commit()


def _log_trade(
    bot_id: int, bot_name: str, ticker: str | None, action_str: str,
    contracts: int, price: float, rule_line: int | None,
):
    """Insert a trade-log row and, for SELL/CLOSE actions, match it to the
    most recent open BUY/LIMIT row for the same bot+market to back-fill
    exit_price and pnl on both the entry row and this new row."""
    db = get_db()
    row_pnl: float | None = None

    if action_str in ("SELL", "CLOSE") and ticker:
        # Find the last entry that hasn't been closed yet (exit_price IS NULL)
        open_row = db.execute(
            "SELECT id, entry_price, contracts FROM trade_log "
            "WHERE bot_id = ? AND market_ticker = ? "
            "  AND action IN ('BUY','LIMIT_YES','LIMIT_NO') "
            "  AND exit_price IS NULL "
            "ORDER BY logged_at DESC LIMIT 1",
            (bot_id, ticker),
        ).fetchone()

        if open_row and open_row["entry_price"] is not None:
            entry_p = float(open_row["entry_price"])
            exit_p  = float(price) if price else 0.0
            n       = int(contracts or open_row["contracts"] or 1)
            # P&L in dollars: price is already in cents (0-99)
            # For YES bots: (sell_cents - buy_cents) / 100 * n
            # For NO bots:  entry_price is stored as NO_price cents, same formula
            calc_pnl = round((exit_p - entry_p) / 100.0 * n, 4)
            row_pnl  = calc_pnl
            # Back-fill the opening row
            db.execute(
                "UPDATE trade_log SET exit_price = ?, pnl = ? WHERE id = ?",
                (exit_p, calc_pnl, open_row["id"]),
            )

    db.execute(
        "INSERT INTO trade_log (bot_id, bot_name, market_ticker, action, contracts, "
        "entry_price, pnl, rule_line, is_paper) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
        (bot_id, bot_name, ticker, action_str, contracts, price, row_pnl, rule_line),
    )
    db.commit()
