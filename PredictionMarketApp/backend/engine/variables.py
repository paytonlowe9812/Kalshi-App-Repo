import asyncio
import logging
import time

from backend.database import get_db
from backend.kalshi.client import get_kalshi_client, kalshi_iso_to_unix
from backend.kalshi.implied_prob import (
    book_quotes_pct_from_rest,
    implied_odds_yes_no_from_rest,
    scalar_to_implied_pct,
    yes_spread_is_degenerate,
)
from backend.kalshi.websocket import ws_manager
from backend.kalshi.market_derived import (
    distance_from_strike_from_market,
    last_traded_pct_candidates,
    minutes_to_expiry_from_market,
)

logger = logging.getLogger(__name__)
_trend_unknown_source_logged: set[tuple[int, str]] = set()


def _f(x) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _read_position_fp(p: dict) -> float:
    """Read signed position from a Kalshi market_positions entry.
    Current API: 'position_fp' (fixed-point string e.g. '5.00').
    Legacy API:  'position' (integer). +N = YES contracts, -N = NO contracts."""
    for key in ("position_fp", "position"):
        v = p.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return 0.0


def _real_price(v) -> float | None:
    """Like _f but returns None instead of 0.0 — used so we can detect missing quotes."""
    if v is None:
        return None
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


async def _fetch_market_rest(ticker: str) -> dict | None:
    client = get_kalshi_client()
    if not client:
        return None
    try:
        data = await client.get_market(ticker)
        return data.get("market", data)
    except Exception as e:
        logger.debug("REST get_market(%s) failed: %s", ticker, e)
        return None


def _apply_bot_rest_enrichment(ticker: str, market: dict, variables: dict) -> None:
    """Fill time/distance/last/bid/ask/YES_price from Get Market payload (Kalshi OpenAPI).

    Also corrects YES_price/NO_price when the WS supplied an out-of-range last-trade
    value (e.g. price_dollars='0.001' → 0.1¢) — REST book always wins when available.
    """
    variables["TimeToExpiry"] = minutes_to_expiry_from_market(market)
    variables["DistanceFromStrike"] = distance_from_strike_from_market(market, ticker)

    # REST book quotes (proper bid/ask)
    b = book_quotes_pct_from_rest(market)
    yb, ya = b["yes_bid"], b["yes_ask"]
    has_real_book = (
        yb is not None and ya is not None
        and yb >= 1.0 and ya >= 1.0
        and not yes_spread_is_degenerate(yb, ya)
    )

    if has_real_book:
        # Override YES/NO price and Bid/Ask from the real REST book
        variables["YES_price"] = _f(yb)
        variables["NO_price"] = _f(b["no_bid"]) if b["no_bid"] else round(100.0 - yb, 1)
        variables["Bid"] = _f(yb)
        variables["Ask"] = _f(ya)
    else:
        # Try REST implied (last trade / mid) as YES_price correction
        yi, ni = implied_odds_yes_no_from_rest(market)
        if 1.0 <= yi <= 99.0:
            current_yes = float(variables.get("YES_price", 0))
            # Only override if the current YES_price looks bogus (outside 1-99)
            if not (1.0 <= current_yes <= 99.0):
                variables["YES_price"] = yi
                variables["NO_price"] = ni

        # Bid/Ask: fall back to mid ± 0.5 using the (now-corrected) YES_price
        mid = float(variables.get("YES_price", 0))
        if mid >= 1.0:
            variables["Bid"] = round(max(1.0, mid - 1.0), 2)
            variables["Ask"] = round(min(99.0, mid + 1.0), 2)

    # LastTraded — use the first non-zero REST candidate
    for cand in last_traded_pct_candidates(market):
        lt = scalar_to_implied_pct(cand)
        if lt is not None and lt >= 1.0:
            variables["LastTraded"] = _f(lt)
            break


# Canonical bot-market keys (placeholders when no market is assigned or data missing).
_BOT_MARKET_KEYS = (
    "YES_price",
    "NO_price",
    "LastTraded",
    "Bid",
    "Ask",
    "FillPrice",
    "TimeToExpiry",
    "DistanceFromStrike",
)


def _add_daily_pnl(variables: dict) -> None:
    client = get_kalshi_client()
    daily_pnl = 0.0
    if client:
        try:
            db = get_db()
            logs = db.execute(
                "SELECT SUM(pnl) as total FROM trade_log WHERE date(logged_at) = date('now')"
            ).fetchone()
            daily_pnl = logs["total"] or 0.0
        except Exception:
            pass
    variables["DailyPnL"] = daily_pnl


async def _add_sentiment_indexes(variables: dict, unavailable: set[str]) -> None:
    db = get_db()
    indexes = db.execute("SELECT * FROM sentiment_indexes").fetchall()
    index_ticker_set: set[str] = set()
    index_sections: list[tuple] = []
    for idx in indexes:
        markets = db.execute(
            "SELECT * FROM sentiment_index_markets WHERE index_id = ?", (idx["id"],)
        ).fetchall()
        index_sections.append((idx, markets))
        for m in markets:
            t = (m["ticker"] or "").strip()
            if t:
                index_ticker_set.add(t)

    rest_by_index_ticker: dict[str, dict] = {}
    if index_ticker_set and get_kalshi_client():

        async def _fetch_one(tkr: str):
            mk = await _fetch_market_rest(tkr)
            return tkr, mk

        pairs = await asyncio.gather(
            *[_fetch_one(t) for t in index_ticker_set],
            return_exceptions=True,
        )
        for item in pairs:
            if not (isinstance(item, tuple) and len(item) == 2):
                continue
            tkr, mk = item
            if isinstance(mk, dict):
                rest_by_index_ticker[tkr] = mk

    for idx, markets in index_sections:
        total_yes = 0.0
        total_no = 0.0
        bull = 0
        bear = 0
        for m in markets:
            raw = (m["label"] or "").strip()
            label = raw or (m["ticker"] or "").strip() or "market"
            tkr = (m["ticker"] or "").strip()
            snap = ws_manager.get_cached_market(tkr) if tkr else None
            y = n = None

            market_rest = rest_by_index_ticker.get(tkr) if tkr else None
            if market_rest:
                y, n = implied_odds_yes_no_from_rest(market_rest)
            elif snap and snap.yes_price is not None and snap.no_price is not None:
                y = float(snap.yes_price)
                n = float(snap.no_price)
            elif (
                snap
                and snap.yes_bid_pct is not None
                and snap.yes_ask_pct is not None
                and not yes_spread_is_degenerate(snap.yes_bid_pct, snap.yes_ask_pct)
            ):
                y = round((float(snap.yes_bid_pct) + float(snap.yes_ask_pct)) / 2.0, 1)
                n = round(100.0 - y, 1)
            if y is None:
                y = n = 50.0
                unavailable.add(f"{label}.YES")
                unavailable.add(f"{label}.NO")
            total_yes += y
            total_no += n
            if y > 50:
                bull += 1
            else:
                bear += 1
            variables[f"{label}.YES"] = y
            variables[f"{label}.NO"] = n
        count = len(markets) or 1
        variables[f"{idx['name']}.Score"] = round(total_yes / count, 1)
        variables[f"{idx['name']}.BullCount"] = float(bull)
        variables[f"{idx['name']}.BearCount"] = float(bear)
        variables[f"{idx['name']}.AvgYES"] = round(total_yes / count, 1)
        variables[f"{idx['name']}.AvgNO"] = round(total_no / count, 1)


async def resolve_global_live_variables() -> dict[str, float]:
    """Account-wide and index sentiment values (no bot market required)."""
    variables: dict[str, float] = {}
    unavailable: set[str] = set()
    _add_daily_pnl(variables)
    await _add_sentiment_indexes(variables, unavailable)
    return variables


async def _resolve_all_core(
    bot_id: int,
) -> tuple[dict[str, float], set[str]]:
    db = get_db()
    bot = db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,)).fetchone()
    ticker = (dict(bot).get("market_ticker") or "").strip() if bot else ""

    variables = await resolve_global_live_variables()
    unavailable: set[str] = set()

    if bot and ticker:
        market_rest = await _fetch_market_rest(ticker) if get_kalshi_client() else None
        snap = ws_manager.get_cached_market(ticker)
        cs = str(dict(bot).get("contract_side") or "yes").lower().strip()

        filled_from_ws = False
        if snap:
            tight_book = (
                snap.yes_bid_pct is not None
                and snap.yes_ask_pct is not None
                and snap.yes_bid_pct >= 1.0
                and snap.yes_ask_pct >= 1.0
                and not yes_spread_is_degenerate(snap.yes_bid_pct, snap.yes_ask_pct)
            )
            # Only trust the WS implied price if it's in a sane 1-99¢ range.
            # A stale WS last-trade like price_dollars="0.001" → 0.1¢ is not usable.
            has_implied = (
                snap.yes_price is not None and snap.no_price is not None
                and 1.0 <= snap.yes_price <= 99.0
            )
            if tight_book:
                variables["YES_price"] = _f(snap.yes_bid_pct)
                variables["NO_price"] = _f(snap.no_bid_pct)
                filled_from_ws = True
            elif has_implied:
                variables["YES_price"] = _f(snap.yes_price)
                variables["NO_price"] = _f(snap.no_price)
                filled_from_ws = True
            if filled_from_ws:
                # LastTraded — only set if it looks like a real trade price (≥ 1¢)
                lt = snap.last_traded
                variables["LastTraded"] = _f(lt) if (lt is not None and lt >= 1.0) else 0.0

                if tight_book:
                    variables["Bid"] = _f(snap.yes_bid_pct)
                    variables["Ask"] = _f(snap.yes_ask_pct)
                else:
                    # Degenerate WS book — use implied mid ± 1.0 as placeholder.
                    # _apply_bot_rest_enrichment will overwrite with real REST values below.
                    mid = variables.get("YES_price")
                    if mid is not None and float(mid) >= 1.0:
                        variables["Bid"] = round(max(1.0, float(mid) - 1.0), 2)
                        variables["Ask"] = round(min(99.0, float(mid) + 1.0), 2)
                    else:
                        variables["Bid"] = 0.0
                        variables["Ask"] = 0.0
                variables["FillPrice"] = _get_fill_price(bot_id, ticker)
                variables["TimeToExpiry"] = _f(snap.minutes_to_expiry)
                variables["DistanceFromStrike"] = _f(snap.distance_from_strike)

        if not filled_from_ws:
            if market_rest:
                b = book_quotes_pct_from_rest(market_rest)
                yb, ya = b["yes_bid"], b["yes_ask"]
                # Require real centavo-scale quotes (>= 1.0) — subpenny values like
                # yes_bid_dollars="0.0000" are not a tradeable book.
                has_real_yes_book = (
                    yb is not None and ya is not None
                    and yb >= 1.0 and ya >= 1.0
                    and not yes_spread_is_degenerate(yb, ya)
                )
                if has_real_yes_book:
                    variables["YES_price"] = _f(yb)
                    variables["NO_price"] = _f(b["no_bid"]) if b["no_bid"] else round(100.0 - yb, 1)
                else:
                    yi, ni = implied_odds_yes_no_from_rest(market_rest)
                    # Only use the implied value if it's in a sane 1-99 range.
                    if 1.0 <= yi <= 99.0:
                        variables["YES_price"] = _f(yi)
                        variables["NO_price"] = _f(ni)
                    else:
                        # Try NO book as a proxy for YES implied price.
                        # Only use if the inferred YES price is also >= 1.0 (centavo-scale).
                        nb, na = b["no_bid"], b["no_ask"]
                        inferred_yes = None
                        if (
                            nb is not None and na is not None
                            and nb >= 1.0 and na >= 1.0
                            and not yes_spread_is_degenerate(nb, na)
                        ):
                            no_mid = round((nb + na) / 2.0, 1)
                            candidate = round(100.0 - no_mid, 1)
                            if candidate >= 1.0:
                                inferred_yes = candidate
                                variables["YES_price"] = candidate
                                variables["NO_price"] = no_mid
                        if inferred_yes is None:
                            variables["YES_price"] = 0.0
                            variables["NO_price"] = 0.0

                # Bid/Ask: use real YES book if available (>= 1.0), else use
                # mid ± 1.0 only when mid is a valid centavo-scale price.
                if has_real_yes_book:
                    variables["Bid"] = _f(yb)
                    variables["Ask"] = _f(ya)
                else:
                    mid = float(variables.get("YES_price", 0))
                    if mid >= 1.0:
                        variables["Bid"] = round(max(1.0, mid - 1.0), 2)
                        variables["Ask"] = round(min(99.0, mid + 1.0), 2)
                    else:
                        variables["Bid"] = 0.0
                        variables["Ask"] = 0.0

                # LastTraded — try REST fields first, then WS snapshot last_traded
                lt = scalar_to_implied_pct(market_rest.get("last_price_dollars"))
                if lt is None or lt < 1.0:
                    lt = scalar_to_implied_pct(market_rest.get("last_price"))
                if (lt is None or lt < 1.0) and snap and snap.last_traded is not None:
                    lt = snap.last_traded
                variables["LastTraded"] = _f(lt) if (lt and lt >= 1.0) else 0.0

                variables["FillPrice"] = _get_fill_price(bot_id, ticker)
                variables["TimeToExpiry"] = 0.0
                variables["DistanceFromStrike"] = 0.0
            else:
                if get_kalshi_client() is None:
                    logger.warning(
                        "No active Kalshi API key: cannot load market %s (configure Keys in CONFIG)",
                        ticker,
                    )
                for k in ("YES_price", "NO_price", "LastTraded", "Bid", "Ask", "FillPrice", "TimeToExpiry", "DistanceFromStrike"):
                    variables[k] = 0.0
                    unavailable.add(k)

        if market_rest and (filled_from_ws or "YES_price" in variables):
            _apply_bot_rest_enrichment(ticker, market_rest, variables)

        # Flip Bid/Ask to the NO book when the bot trades the NO side.
        # Binary contract: no_bid = 100 - yes_ask, no_ask = 100 - yes_bid.
        if cs == "no" and "Bid" in variables and "Ask" in variables:
            yes_bid = variables["Bid"]
            yes_ask = variables["Ask"]
            variables["Bid"] = round(100.0 - yes_ask, 2)
            variables["Ask"] = round(100.0 - yes_bid, 2)
            # Keep LastTraded consistent with the selected contract side.
            # Only flip if we have a real non-zero value (avoid 100 - 0 = 100 nonsense).
            lt = variables.get("LastTraded", 0.0)
            if lt and lt > 0:
                variables["LastTraded"] = round(100.0 - lt, 2)

    elif bot:
        for k in _BOT_MARKET_KEYS:
            variables[k] = 0.0
            unavailable.add(k)

    from backend.engine.position_tracker import get_local_position

    client = get_kalshi_client()
    local_pos = get_local_position(bot_id, ticker) if (bot and ticker) else None
    position_size = 0.0

    if local_pos is not None:
        position_size = local_pos
    elif client:
        try:
            positions = await client.get_positions()
            pos_list = positions.get("market_positions", [])
            if bot and ticker:
                cs = str(dict(bot).get("contract_side") or "yes").lower().strip()
                for p in pos_list:
                    if p.get("ticker") == ticker:
                        raw = _read_position_fp(p)
                        if cs == "no":
                            position_size = max(0.0, -raw)
                        else:
                            position_size = max(0.0, raw)
                        break
        except Exception:
            pass

    variables["PositionSize"] = position_size
    variables["HasPosition"] = 1.0 if position_size > 1e-9 else 0.0
    variables["AbsPositionSize"] = abs(position_size)

    resting_count = 0.0
    oldest_age_sec = 0.0
    if client and bot and ticker:
        try:
            odata = await client.get_orders(ticker=ticker, status="resting", limit=200)
            now = time.time()
            oldest_delta = 0.0
            for o in odata.get("orders") or []:
                if (o.get("type") or "").lower() != "limit":
                    continue
                ts = kalshi_iso_to_unix(o.get("created_time"))
                if ts is None:
                    continue
                resting_count += 1.0
                delta = max(0.0, now - ts)
                if delta > oldest_delta:
                    oldest_delta = delta
            oldest_age_sec = oldest_delta
        except Exception as e:
            logger.debug("get_orders for resting vars failed: %s", e)

    variables["RestingLimitCount"] = resting_count
    variables["OldestRestingLimitAgeSec"] = oldest_age_sec

    user_vars = db.execute(
        "SELECT name, value FROM variables WHERE bot_id = ?", (bot_id,)
    ).fetchall()
    for v in user_vars:
        try:
            variables[v["name"]] = float(v["value"])
        except (ValueError, TypeError):
            variables[v["name"]] = 0.0

    # Trend tracker — sampled at trend_poll_ms cadence, independent of loop speed
    if bot:
        from backend.engine.trend import update_trend as _update_trend
        b = dict(bot)
        poll_ms = int(b.get("trend_poll_ms") or 1000)
        confirm_count = int(b.get("trend_confirm_count") or 3)
        price_source = (b.get("trend_price_source") or "YES_price").strip() or "YES_price"
        if price_source not in variables and ticker:
            lk = (bot_id, price_source)
            if lk not in _trend_unknown_source_logged:
                _trend_unknown_source_logged.add(lk)
                logger.warning(
                    "Bot %s: trend_price_source %r is not in the variable map (check spelling "
                    "vs rule editor dropdown); trending will see 0.0",
                    bot_id,
                    price_source,
                )
        current_price = float(variables.get(price_source) or 0.0)
        variables.update(_update_trend(bot_id, current_price, poll_ms, confirm_count))

    return variables, unavailable


async def resolve_all(bot_id: int) -> dict[str, float]:
    variables, _ = await _resolve_all_core(bot_id)
    return variables


def _get_fill_price(bot_id: int, ticker: str) -> float:
    db = get_db()
    row = db.execute(
        "SELECT entry_price FROM trade_log WHERE bot_id = ? AND market_ticker = ? "
        "ORDER BY logged_at DESC LIMIT 1",
        (bot_id, ticker),
    ).fetchone()
    return row["entry_price"] if row and row["entry_price"] else 0.0
