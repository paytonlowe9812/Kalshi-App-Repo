"""Derive display fields from Kalshi REST Market objects (see Get Market schema)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional


def _parse_iso_utc(s: Any) -> Optional[datetime]:
    if s is None or str(s).strip() == "":
        return None
    raw = str(s).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def minutes_to_expiry_from_market(market: dict) -> float:
    """
    Minutes until the nearest future boundary among close / expected / latest expiration.
    Uses official fields: close_time, expected_expiration_time, latest_expiration_time.
    """
    if not market:
        return 0.0
    now = datetime.now(timezone.utc)
    candidates: list[datetime] = []
    for key in ("close_time", "expected_expiration_time", "latest_expiration_time"):
        dt = _parse_iso_utc(market.get(key))
        if dt and dt > now:
            candidates.append(dt)
    if not candidates:
        return 0.0
    soonest = min(candidates)
    return max(0.0, round((soonest - now).total_seconds() / 60.0, 2))


def strike_from_ticker(ticker: str) -> Optional[float]:
    """Kalshi crypto/short markets often encode a numeric strike after -T or -B."""
    if not ticker:
        return None
    for pat in (r"-T([\d.]+)(?:$|[-+])", r"-B([\d.]+)(?:$|[-+])"):
        m = re.search(pat, ticker)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def distance_from_strike_from_market(market: dict, ticker: str) -> float:
    """
    |current_reference - strike| when both exist.
    strike: floor_strike or parsed from ticker.
    reference: expiration_value if it parses as a positive price-like number.
    """
    if not market:
        return 0.0
    strike = market.get("floor_strike")
    if strike is None:
        strike = strike_from_ticker(ticker)
    try:
        s = float(strike) if strike is not None else None
    except (TypeError, ValueError):
        s = None
    if s is None:
        return 0.0
    ev = market.get("expiration_value")
    if ev is None or str(ev).strip() == "":
        return 0.0
    try:
        cur = float(str(ev).replace("$", "").replace(",", "").strip())
    except ValueError:
        return 0.0
    if cur <= 0:
        return 0.0
    return round(abs(cur - s), 4)


def last_traded_pct_candidates(market: dict) -> list[Any]:
    """Ordered preference for last-trade style YES price fields (strings for scalar_to_implied_pct)."""
    if not market:
        return []
    out = []
    for k in ("last_price_dollars", "last_price", "previous_price_dollars"):
        v = market.get(k)
        if v is not None and str(v).strip() != "":
            out.append(v)
    return out
