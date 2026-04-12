"""
In-process ring-buffer for bot debug events.
Written by the executor/evaluator on every significant event.
Polled by /api/logs/bot-events (SSE or plain JSON long-poll).
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading

_MAX_EVENTS = 3000  # keep last 3000 entries in memory

@dataclass
class BotEvent:
    id: int
    ts: str           # ISO timestamp
    bot_id: int
    bot_name: str
    level: str        # INFO | WARN | DEBUG | ERROR
    event: str        # short tag: ORDER_PLACED, SKIPPED_COOLDOWN, TICK_IDLE, etc.
    message: str      # human-readable line
    details: dict = field(default_factory=dict)

_lock = threading.Lock()
_events: deque = deque(maxlen=_MAX_EVENTS)
_counter = 0

def log_event(bot_id: int, bot_name: str, level: str, event: str, message: str, details: dict = None):
    global _counter
    with _lock:
        _counter += 1
        entry = BotEvent(
            id=_counter,
            ts=datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
            bot_id=bot_id,
            bot_name=bot_name or f"bot#{bot_id}",
            level=level,
            event=event,
            message=message,
            details=details or {},
        )
        _events.append(entry)

def get_events(since_id: int = 0, bot_id: int = None, limit: int = 200):
    with _lock:
        result = []
        for e in _events:
            if e.id <= since_id:
                continue
            if bot_id is not None and e.bot_id != bot_id:
                continue
            result.append(e)
        return result[-limit:]
