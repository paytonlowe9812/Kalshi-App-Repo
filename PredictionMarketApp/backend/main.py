import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, get_db
from backend.engine.executor import start_scheduler
from backend.engine.index_auto_roll import (
    start_index_auto_roll_worker,
    stop_index_auto_roll_worker,
)
from backend.kalshi.client import KalshiClient, set_kalshi_client
from backend.kalshi.websocket import ws_manager, get_all_tickers

from backend.routers import (
    assistant,
    settings,
    keys,
    bots,
    groups,
    rules,
    markets,
    market_lists,
    indexes,
    portfolio,
    logs,
    export,
    simulator,
    license,
    variables,
    snapshots,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    db = get_db()
    active_key = db.execute(
        "SELECT key_id, key_secret FROM api_keys WHERE is_active = 1 LIMIT 1"
    ).fetchone()
    if active_key:
        client = KalshiClient(active_key["key_id"], active_key["key_secret"])
        set_kalshi_client(client)
        ws_manager.configure(active_key["key_id"], active_key["key_secret"])
        await ws_manager.start()
        tickers = get_all_tickers()
        if tickers:
            await ws_manager.subscribe(tickers)

    await start_scheduler()
    await start_index_auto_roll_worker()
    yield
    await stop_index_auto_roll_worker()
    await ws_manager.stop()


app = FastAPI(title="Kalshi Bot Builder", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(settings.router)
app.include_router(assistant.router)
app.include_router(keys.router)
app.include_router(bots.router)
app.include_router(groups.router)
app.include_router(rules.router)
app.include_router(markets.router)
app.include_router(market_lists.router)
app.include_router(indexes.router)
app.include_router(portfolio.router)
app.include_router(logs.router)
app.include_router(export.router)
app.include_router(simulator.router)
app.include_router(license.router)
app.include_router(variables.router)
app.include_router(snapshots.router)

frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
