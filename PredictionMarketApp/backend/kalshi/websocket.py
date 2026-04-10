import asyncio
import json
import time
import base64
import logging
from typing import Optional
import websockets

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

from backend.models import MarketSnapshot
from backend.kalshi.implied_prob import (
    book_quotes_pct_from_ws,
    implied_odds_yes_no_from_ws,
    scalar_to_implied_pct,
)

logger = logging.getLogger(__name__)

KALSHI_WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"
KALSHI_DEMO_WS_URL = "wss://demo-api.kalshi.co/trade-api/ws/v2"


def _normalize_pem(pem_text: str) -> str:
    text = pem_text.strip()
    for kind in ("RSA PRIVATE KEY", "PRIVATE KEY", "EC PRIVATE KEY"):
        header = f"-----BEGIN {kind}-----"
        footer = f"-----END {kind}-----"
        if header in text and footer in text:
            start = text.index(header) + len(header)
            end = text.index(footer)
            b64 = text[start:end].replace("\n", "").replace("\r", "").replace(" ", "")
            lines = [b64[i : i + 64] for i in range(0, len(b64), 64)]
            return header + "\n" + "\n".join(lines) + "\n" + footer + "\n"
    return text


def _load_rsa_key(pem_text: str):
    normalized = _normalize_pem(pem_text)
    pem_bytes = normalized.encode() if isinstance(normalized, str) else normalized
    return serialization.load_pem_private_key(
        pem_bytes, password=None, backend=default_backend()
    )


class KalshiWebSocketManager:
    def __init__(self):
        self.cache: dict[str, MarketSnapshot] = {}
        self._ws = None
        self._subscribed_tickers: set[str] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._key_id: Optional[str] = None
        self._private_key_pem: Optional[str] = None
        self._rsa_key = None
        self._demo: bool = False
        self._cmd_id = 0

    def _next_cmd_id(self) -> int:
        self._cmd_id += 1
        return self._cmd_id

    def _subscribe_params(self, market_tickers: list[str]) -> dict:
        """Kalshi: send_initial_snapshot delivers current ticker state immediately."""
        return {
            "channels": ["ticker"],
            "market_tickers": market_tickers,
            "send_initial_snapshot": True,
        }

    def configure(self, key_id: str, private_key_pem: str, demo: bool = False):
        self._key_id = key_id
        self._private_key_pem = private_key_pem
        self._demo = demo
        try:
            self._rsa_key = _load_rsa_key(private_key_pem)
        except Exception as e:
            logger.error("WebSocket: failed to load RSA private key: %s", e)
            self._rsa_key = None

    @property
    def ws_url(self) -> str:
        return KALSHI_DEMO_WS_URL if self._demo else KALSHI_WS_URL

    def _build_auth_headers(self) -> dict:
        if not self._key_id or not self._rsa_key:
            return {}
        ts = str(int(time.time() * 1000))
        path = "/trade-api/ws/v2"
        message = f"{ts}GET{path}".encode("utf-8")
        signature = self._rsa_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        sig_b64 = base64.b64encode(signature).decode("utf-8")
        return {
            "KALSHI-ACCESS-KEY": self._key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sig_b64,
        }

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def subscribe(self, tickers: list[str]):
        new_tickers = set(tickers) - self._subscribed_tickers
        if not new_tickers:
            return
        self._subscribed_tickers.update(new_tickers)
        for ticker in new_tickers:
            if ticker not in self.cache:
                self.cache[ticker] = MarketSnapshot(ticker=ticker)
        if self._ws:
            try:
                await self._ws.send(
                    json.dumps(
                        {
                            "id": self._next_cmd_id(),
                            "cmd": "subscribe",
                            "params": self._subscribe_params(list(new_tickers)),
                        }
                    )
                )
            except Exception:
                logger.warning("Failed to send subscribe message")

    async def unsubscribe(self, tickers: list[str]):
        remove = set(tickers) & self._subscribed_tickers
        if not remove:
            return
        self._subscribed_tickers -= remove
        for t in remove:
            self.cache.pop(t, None)

    def get_cached_market(self, ticker: str) -> Optional[MarketSnapshot]:
        return self.cache.get(ticker)

    async def _run_loop(self):
        while self._running:
            try:
                headers = self._build_auth_headers()
                async with websockets.connect(
                    self.ws_url, additional_headers=headers
                ) as ws:
                    self._ws = ws
                    if self._subscribed_tickers:
                        await ws.send(
                            json.dumps(
                                {
                                    "id": self._next_cmd_id(),
                                    "cmd": "subscribe",
                                    "params": self._subscribe_params(
                                        list(self._subscribed_tickers)
                                    ),
                                }
                            )
                        )
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw_msg)
                            await self._on_message(msg)
                        except json.JSONDecodeError:
                            continue
            except websockets.ConnectionClosed:
                logger.info("WebSocket connection closed, reconnecting...")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            if self._running:
                await asyncio.sleep(5)

    async def _on_message(self, msg: dict):
        msg_type = msg.get("type", "")
        if msg_type == "error":
            logger.warning("Kalshi WebSocket error: %s", msg.get("msg", msg))
            return
        if msg_type == "ticker" and "msg" in msg:
            data = msg["msg"]
            ticker = data.get("market_ticker", "")
            if ticker in self.cache:
                snap = self.cache[ticker]
                book = book_quotes_pct_from_ws(data)
                snap.yes_bid_pct = book["yes_bid"]
                snap.yes_ask_pct = book["yes_ask"]
                snap.no_bid_pct = book["no_bid"]
                snap.no_ask_pct = book["no_ask"]
                y_imp, n_imp = implied_odds_yes_no_from_ws(data)
                snap.yes_price, snap.no_price = y_imp, n_imp
                lt = scalar_to_implied_pct(data.get("price_dollars"))
                if lt is None:
                    lt = scalar_to_implied_pct(data.get("last_price"))
                if lt is not None:
                    snap.last_traded = lt
                if book["yes_bid"] is not None:
                    snap.bid = book["yes_bid"]
                if book["yes_ask"] is not None:
                    snap.ask = book["yes_ask"]
                vol_fp = data.get("volume_fp")
                if vol_fp is not None and str(vol_fp).strip() != "":
                    try:
                        snap.volume = int(float(vol_fp))
                    except (TypeError, ValueError):
                        pass
                elif data.get("volume") is not None:
                    try:
                        snap.volume = int(data["volume"])
                    except (TypeError, ValueError):
                        snap.volume = data.get("volume", snap.volume)


ws_manager = KalshiWebSocketManager()


def get_all_tickers() -> list[str]:
    from backend.database import get_db
    db = get_db()
    bot_rows = db.execute(
        "SELECT DISTINCT market_ticker FROM bots WHERE market_ticker IS NOT NULL AND market_ticker != ''"
    ).fetchall()
    index_rows = db.execute(
        "SELECT DISTINCT ticker FROM sentiment_index_markets"
    ).fetchall()
    tickers = set()
    for r in bot_rows:
        tickers.add(r["market_ticker"])
    for r in index_rows:
        tickers.add(r["ticker"])
    return list(tickers)
