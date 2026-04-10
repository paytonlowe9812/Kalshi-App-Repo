"""Kalshi quote math: order-book prices (bid/ask per side) vs implied odds (fair % from last or mid)."""

from __future__ import annotations

from typing import Any, Optional, Tuple


def _float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def yes_spread_is_degenerate(
    bid: Optional[float], ask: Optional[float], min_spread: float = 98.5
) -> bool:
    """
    Kalshi often exposes no real YES liquidity as bid ~0 and ask ~100 (or similarly
    extreme). Taking mid yields ~50, which looks like live odds but is not meaningful.
    """
    if bid is None or ask is None:
        return False
    return (ask - bid) >= min_spread


def scalar_to_implied_pct(val: Any) -> Optional[float]:
    """
    Kalshi REST/WS: *_dollars fields are strings like \"0.480\" (multiply by 100).
    Legacy numeric cents use 1-99 (integer 1 is 1 cent, not $1.00).
    """
    if val is None or val == "":
        return None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        try:
            x = float(s)
        except (TypeError, ValueError):
            return None
        return round(min(100.0, max(0.0, x * 100.0)), 1)
    f = _float(val)
    if f is None:
        return None
    if 0 < f < 1:
        return round(f * 100.0, 1)
    if 1 <= f <= 99:
        return round(f, 1)
    if f <= 0:
        return 0.0
    return round(min(100.0, max(0.0, f)), 1)


def book_quotes_pct_from_rest(market: dict) -> dict[str, Optional[float]]:
    """YES/NO bid and ask as 0-100 (order book prices), from REST market object."""
    if not market:
        return {k: None for k in ("yes_bid", "yes_ask", "no_bid", "no_ask")}
    out: dict[str, Optional[float]] = {}
    for api, key in (
        ("yes_bid_dollars", "yes_bid"),
        ("yes_ask_dollars", "yes_ask"),
        ("no_bid_dollars", "no_bid"),
        ("no_ask_dollars", "no_ask"),
    ):
        out[key] = scalar_to_implied_pct(market.get(api))
    if out["yes_bid"] is None:
        out["yes_bid"] = scalar_to_implied_pct(market.get("yes_bid"))
    if out["yes_ask"] is None:
        out["yes_ask"] = scalar_to_implied_pct(market.get("yes_ask"))
    if out["no_bid"] is None:
        out["no_bid"] = scalar_to_implied_pct(market.get("no_bid"))
    if out["no_ask"] is None:
        out["no_ask"] = scalar_to_implied_pct(market.get("no_ask"))
    _fill_no_from_yes_bid_ask(out)
    return out


def _fill_no_from_yes_bid_ask(out: dict[str, Optional[float]]) -> None:
    """Binary contract: derive NO book from YES when NO legs are absent (common on WS ticker)."""
    yb, ya, nb, na = out["yes_bid"], out["yes_ask"], out["no_bid"], out["no_ask"]
    if yb is None or ya is None:
        return
    if nb is None:
        out["no_bid"] = round(100.0 - ya, 1)
    if na is None:
        out["no_ask"] = round(100.0 - yb, 1)


def implied_odds_yes_no_from_rest(market: dict) -> Tuple[float, float]:
    """
    Fair implied YES/NO % (odds view): prefer mid YES bid/ask (matches live quotes),
    then last trade, then NO book. Stale last prints no longer override a real book.
    """
    if not market:
        return 50.0, 50.0
    b = book_quotes_pct_from_rest(market)
    yb, ya = b["yes_bid"], b["yes_ask"]
    if yb is not None and ya is not None and not yes_spread_is_degenerate(yb, ya):
        y = round((yb + ya) / 2, 1)
        return y, round(100.0 - y, 1)
    last = scalar_to_implied_pct(market.get("last_price_dollars"))
    if last is None:
        last = scalar_to_implied_pct(market.get("last_price"))
    if last is not None:
        return last, round(100.0 - last, 1)
    nb, na = b["no_bid"], b["no_ask"]
    if nb is not None and na is not None and not yes_spread_is_degenerate(nb, na):
        nm = round((nb + na) / 2, 1)
        return round(100.0 - nm, 1), nm
    yes_pair_degenerate = (
        yb is not None and ya is not None and yes_spread_is_degenerate(yb, ya)
    )
    if not yes_pair_degenerate:
        if yb is not None:
            return yb, round(100.0 - yb, 1)
        if ya is not None:
            return ya, round(100.0 - ya, 1)
    no_pair_degenerate = (
        nb is not None and na is not None and yes_spread_is_degenerate(nb, na)
    )
    if not no_pair_degenerate:
        if nb is not None:
            return round(100.0 - nb, 1), nb
        if na is not None:
            return round(100.0 - na, 1), na
    return 50.0, 50.0


def book_quotes_pct_from_ws(data: dict) -> dict[str, Optional[float]]:
    """
    WebSocket ticker uses yes_bid_dollars / yes_ask_dollars / price_dollars (strings),
    not yes_bid / last_price. See https://docs.kalshi.com/websockets/market-ticker
    """
    if not data:
        return {k: None for k in ("yes_bid", "yes_ask", "no_bid", "no_ask")}
    out: dict[str, Optional[float]] = {}
    for api_dollar, legacy, key in (
        ("yes_bid_dollars", "yes_bid", "yes_bid"),
        ("yes_ask_dollars", "yes_ask", "yes_ask"),
        ("no_bid_dollars", "no_bid", "no_bid"),
        ("no_ask_dollars", "no_ask", "no_ask"),
    ):
        v = scalar_to_implied_pct(data.get(api_dollar))
        if v is None:
            v = scalar_to_implied_pct(data.get(legacy))
        out[key] = v
    _fill_no_from_yes_bid_ask(out)
    return out


def implied_odds_yes_no_from_ws(data: dict) -> Tuple[float, float]:
    """Implied odds from WS ticker: YES mid from book, then price_dollars / last_price."""
    if not data:
        return 50.0, 50.0
    b = book_quotes_pct_from_ws(data)
    yb, ya = b["yes_bid"], b["yes_ask"]
    if yb is not None and ya is not None and not yes_spread_is_degenerate(yb, ya):
        y = round((yb + ya) / 2, 1)
        return y, round(100.0 - y, 1)
    last = scalar_to_implied_pct(data.get("price_dollars"))
    if last is None:
        last = scalar_to_implied_pct(data.get("last_price"))
    if last is not None:
        return last, round(100.0 - last, 1)
    nb, na = b["no_bid"], b["no_ask"]
    if nb is not None and na is not None and not yes_spread_is_degenerate(nb, na):
        nm = round((nb + na) / 2, 1)
        return round(100.0 - nm, 1), nm
    yes_pair_degenerate = (
        yb is not None and ya is not None and yes_spread_is_degenerate(yb, ya)
    )
    if not yes_pair_degenerate:
        for side in (yb, ya):
            if side is not None:
                return side, round(100.0 - side, 1)
    no_pair_degenerate = (
        nb is not None and na is not None and yes_spread_is_degenerate(nb, na)
    )
    if not no_pair_degenerate:
        for side in (nb, na):
            if side is not None:
                return round(100.0 - side, 1), side
    yp = scalar_to_implied_pct(data.get("yes_price"))
    if yp is not None:
        return yp, round(100.0 - yp, 1)
    np = scalar_to_implied_pct(data.get("no_price"))
    if np is not None:
        return round(100.0 - np, 1), np
    return 50.0, 50.0


def implied_yes_no_pct_from_rest_market(market: dict) -> Tuple[float, float]:
    """Back-compat alias for implied odds (not order-book bids)."""
    return implied_odds_yes_no_from_rest(market)
