"""
Per-bot local position state.

Kalshi's market_positions API returns the NET signed position across all bots
on the same ticker (+N = N YES contracts, -N = N NO contracts).  When a YES
bot and a NO bot both hold 1 contract on the same market the net is 0, so both
bots see HasPosition=0 and keep firing indefinitely.

This module maintains a per-bot position cache that is updated immediately
after every order placement and is used to override the Kalshi net figure in
variables.resolve_all().  The cache is in-process only (resets on restart) so
on the first tick after a restart we fall back to Kalshi's API and re-sync.
"""

import threading

_lock = threading.Lock()

# (bot_id, ticker) -> local position size.
# Positive = we hold a long position (YES or NO side).
# None     = unknown / not yet initialised (fall back to Kalshi).
_positions: dict[tuple[int, str], float] = {}


def record_entry(bot_id: int, ticker: str | None, contracts: float) -> None:
    """Call after a BUY or LIMIT is placed successfully."""
    if not ticker:
        return
    with _lock:
        _positions[(bot_id, ticker)] = float(contracts)


def record_exit(bot_id: int, ticker: str | None) -> None:
    """Call after a SELL or CLOSE is placed successfully."""
    if not ticker:
        return
    with _lock:
        _positions[(bot_id, ticker)] = 0.0


def get_local_position(bot_id: int, ticker: str | None) -> float | None:
    """
    Return the bot's known local position, or None if we don't have local state
    yet (e.g. first tick after a server restart).
    """
    if not ticker:
        return None
    with _lock:
        return _positions.get((bot_id, ticker))


def clear_bot(bot_id: int) -> None:
    """Remove all local state for a bot (called when bot is deleted)."""
    with _lock:
        keys = [k for k in _positions if k[0] == bot_id]
        for k in keys:
            del _positions[k]
