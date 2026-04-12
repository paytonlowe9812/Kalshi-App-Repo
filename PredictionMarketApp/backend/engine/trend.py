"""
Per-bot price trend tracker.

Runs entirely in-memory on the asyncio event loop — no DB writes, no threads.
update_trend() is called from variables.resolve_all() on every bot loop tick.
It samples the price only when trend_poll_ms have elapsed since the last sample,
so the bot's loop frequency and the trend sampling frequency are independent.
"""

import time
from collections import deque
from dataclasses import dataclass, field

_MAX_HISTORY = 500


@dataclass
class _TrendState:
    prices: deque = field(default_factory=lambda: deque(maxlen=_MAX_HISTORY))
    last_sample_ts: float = 0.0
    consecutive_up: int = 0
    consecutive_down: int = 0


_states: dict[int, _TrendState] = {}


def clear_state(bot_id: int) -> None:
    """Call when a bot is stopped/deleted to free memory."""
    _states.pop(bot_id, None)


def update_trend(
    bot_id: int,
    current_price: float,
    poll_ms: int,
    confirm_count: int,
) -> dict[str, float]:
    """
    Sample current_price if poll_ms have elapsed since the last sample.
    Compare to the previous sample and update consecutive-move counters.

    Returns a dict with four variables ready to merge into the bot's variable map:
      ConsecutiveUp   - how many consecutive samples price strictly increased
      ConsecutiveDown - how many consecutive samples price strictly decreased
      TrendUp         - 1.0 if ConsecutiveUp  >= confirm_count, else 0.0
      TrendDown       - 1.0 if ConsecutiveDown >= confirm_count, else 0.0
    """
    state = _states.setdefault(bot_id, _TrendState())
    now = time.monotonic()
    poll_sec = max(0.05, poll_ms / 1000.0)

    if now - state.last_sample_ts >= poll_sec:
        state.last_sample_ts = now
        prev = state.prices[-1] if state.prices else None
        # Skip when the quote is unchanged vs last sample — Kalshi often repeats the same
        # YES_price for many polls; counting those would stall ConsecutiveUp/Down forever.
        if prev is not None and current_price == prev:
            pass
        else:
            state.prices.append(current_price)
            if prev is not None:
                if current_price > prev:
                    state.consecutive_up += 1
                    state.consecutive_down = 0
                elif current_price < prev:
                    state.consecutive_down += 1
                    state.consecutive_up = 0

    threshold = max(1, confirm_count)
    return {
        "ConsecutiveUp":   float(state.consecutive_up),
        "ConsecutiveDown": float(state.consecutive_down),
        "TrendUp":   1.0 if state.consecutive_up   >= threshold else 0.0,
        "TrendDown": 1.0 if state.consecutive_down >= threshold else 0.0,
    }
