"""Account-wide live variable snapshot (no bot required)."""

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.engine.variables import resolve_global_live_variables
from backend.kalshi.client import get_kalshi_client

router = APIRouter(prefix="/api", tags=["live"])


@router.get("/live-variables")
async def get_live_variables_global():
    """Daily PnL and sentiment index aggregates; same data merged into per-bot /live-variables."""
    vals = await resolve_global_live_variables()
    return {
        "bot_id": None,
        "scope": "global",
        "kalshi_client_configured": get_kalshi_client() is not None,
        "variables": vals,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
