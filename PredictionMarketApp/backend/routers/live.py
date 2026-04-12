"""Account-wide live variable snapshot (no bot required)."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.engine.variables import resolve_global_live_variables
from backend.kalshi.client import get_kalshi_client

router = APIRouter(prefix="/api", tags=["live"])

_LIVE_VARS_TIMEOUT_SEC = 25.0


@router.get("/live-variables")
async def get_live_variables_global():
    """Daily PnL and sentiment index aggregates; same data merged into per-bot /live-variables."""
    try:
        vals = await asyncio.wait_for(
            resolve_global_live_variables(),
            timeout=_LIVE_VARS_TIMEOUT_SEC,
        )
    except TimeoutError:
        raise HTTPException(
            504,
            "live-variables timed out; try again",
        )
    return {
        "bot_id": None,
        "scope": "global",
        "kalshi_client_configured": get_kalshi_client() is not None,
        "variables": vals,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
