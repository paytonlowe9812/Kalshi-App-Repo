import asyncio
import httpx
import time
import base64
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"


def kalshi_iso_to_unix(s: str | None) -> float | None:
    """Parse Kalshi API date-time string to UTC unix seconds."""
    if not s or not isinstance(s, str):
        return None
    try:
        t = s.strip()
        if t.endswith("Z"):
            t = t[:-1] + "+00:00"
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def _normalize_pem(pem_text: str) -> str:
    """Re-wrap a PEM key that lost its newlines (e.g. pasted into a single-line input)."""
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


class KalshiClient:
    def __init__(self, key_id: str, private_key_pem: str):
        self.key_id = key_id
        self._private_key_pem = private_key_pem
        self.base_url = BASE_URL
        self._client: Optional[httpx.AsyncClient] = None
        self._rsa_key = None
        try:
            self._rsa_key = _load_rsa_key(private_key_pem)
        except Exception as e:
            logger.error("Failed to load RSA private key: %s", e)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _sign_request(self, method: str, path: str) -> dict:
        if not self._rsa_key:
            raise RuntimeError(
                "RSA private key not loaded. "
                "Ensure key_secret is a valid PEM-encoded RSA private key."
            )
        ts = str(int(time.time() * 1000))
        full_path = urlparse(self.base_url + path).path.split("?")[0]
        message = f"{ts}{method.upper()}{full_path}".encode("utf-8")
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
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-ACCESS-SIGNATURE": sig_b64,
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        headers = self._sign_request(method, path)
        resp = await client.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def test_connection(self) -> dict:
        try:
            result = await self._request("GET", "/exchange/status")
            return {"valid": True, "data": result}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def get_markets(
        self,
        limit: int = 100,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        event_ticker: Optional[str] = None,
        series_ticker: Optional[str] = None,
        tickers: Optional[str] = None,
        mve_filter: Optional[str] = None,
    ) -> dict:
        params: dict = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if event_ticker:
            params["event_ticker"] = event_ticker
        if series_ticker:
            params["series_ticker"] = series_ticker
        if tickers:
            params["tickers"] = tickers
        if mve_filter:
            params["mve_filter"] = mve_filter
        return await self._request("GET", "/markets", params=params)

    async def get_series_list(
        self,
        category: Optional[str] = None,
        tags: Optional[str] = None,
        include_volume: bool = False,
    ) -> dict:
        params: dict = {}
        if category:
            params["category"] = category
        if tags:
            params["tags"] = tags
        if include_volume:
            params["include_volume"] = "true"
        return await self._request("GET", "/series", params=params)

    async def get_events(
        self,
        limit: int = 50,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        with_nested_markets: bool = False,
    ) -> dict:
        params: dict = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if with_nested_markets:
            params["with_nested_markets"] = "true"
        return await self._request("GET", "/events", params=params)

    async def find_next_contract(
        self,
        series_ticker: str,
        current_ticker: Optional[str] = None,
    ) -> Optional[str]:
        """Find the next open contract in a series, picking the nearest-the-money strike."""
        result = await self.get_markets(series_ticker=series_ticker, status="open", limit=10)
        all_markets = [
            m for m in result.get("markets", [])
            if m.get("status") in ("active", "open")
        ]

        if not all_markets:
            return None

        # For series with a single market per event (e.g., BTC 15m up/down),
        # just pick the soonest-closing one.
        # For multi-strike events, pick the nearest-the-money strike.
        by_event: dict[str, list] = {}
        for m in all_markets:
            by_event.setdefault(m.get("event_ticker", ""), []).append(m)

        candidates = []
        for evt_ticker, strikes in by_event.items():
            if len(strikes) == 1:
                candidates.append(strikes[0])
            else:
                def _yes_cents(mk):
                    try:
                        return round(float(mk.get("yes_bid_dollars", "0")) * 100)
                    except (TypeError, ValueError):
                        return 0
                best = min(strikes, key=lambda s: abs(_yes_cents(s) - 50))
                candidates.append(best)

        candidates.sort(key=lambda m: m.get("close_time", ""))
        return candidates[0].get("ticker") if candidates else None

    async def get_market(self, ticker: str) -> dict:
        return await self._request("GET", f"/markets/{ticker}")

    async def get_orderbook(self, ticker: str) -> dict:
        return await self._request("GET", f"/markets/{ticker}/orderbook")

    async def get_market_history(
        self, ticker: str, limit: int = 100, min_ts: Optional[int] = None
    ) -> dict:
        params: dict = {"limit": limit}
        if min_ts:
            params["min_ts"] = min_ts
        return await self._request("GET", f"/markets/{ticker}/history", params=params)

    async def create_order(
        self,
        ticker: str,
        *,
        contract_side: str,
        order_action: str,
        count: int,
        type: str = "market",
        price: Optional[int] = None,
    ) -> dict:
        """contract_side: yes | no. order_action: buy | sell."""
        cs = (contract_side or "yes").lower()
        api_side = "yes" if cs in ("yes", "y") else "no"
        act = (order_action or "buy").lower()
        api_action = "buy" if act == "buy" else "sell"
        body: dict = {
            "ticker": ticker,
            "action": api_action,
            "side": api_side,
            "count": count,
        }
        order_type = (type or "market").strip().lower()
        # Kalshi expects yes_price / no_price in cents, each 1-99 (CreateOrderRequest).
        # type=market without a price is rejected or ineffective on current trade-api; use an
        # aggressive IOC limit (buy at 99 / sell at 1 on the order side) as market-like behavior.
        if order_type == "market":
            body["type"] = "limit"
            body["time_in_force"] = "immediate_or_cancel"
            if api_action == "buy":
                if api_side == "yes":
                    body["yes_price"] = 99
                else:
                    body["no_price"] = 99
            else:
                if api_side == "yes":
                    body["yes_price"] = 1
                else:
                    body["no_price"] = 1
        else:
            body["type"] = order_type
            if price is not None:
                p = max(1, min(99, int(round(price))))
                if api_side == "yes":
                    body["yes_price"] = p
                else:
                    body["no_price"] = p
        return await self._request("POST", "/portfolio/orders", json=body)

    async def get_orders(
        self,
        *,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> dict:
        params: dict = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        return await self._request("GET", "/portfolio/orders", params=params)

    async def cancel_order(self, order_id: str) -> dict:
        return await self._request("DELETE", f"/portfolio/orders/{order_id}")

    async def get_positions(self) -> dict:
        return await self._request("GET", "/portfolio/positions")

    async def get_fills(
        self, min_ts: Optional[int] = None, max_ts: Optional[int] = None
    ) -> dict:
        params: dict = {}
        if min_ts:
            params["min_ts"] = min_ts
        if max_ts:
            params["max_ts"] = max_ts
        return await self._request("GET", "/portfolio/fills", params=params)

    async def get_balance(self) -> dict:
        return await self._request("GET", "/portfolio/balance")

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()


_active_client: Optional[KalshiClient] = None
# (key_id, key_secret PEM) for the in-memory REST client; must match DB active row.
_active_cred_signature: Optional[tuple[str, str]] = None


def get_kalshi_client() -> Optional[KalshiClient]:
    """Return the REST client for the API key row with is_active=1.

    The Test Connection button uses a temporary client only; bots and orders use
    this singleton. We re-read the DB each time so the process never trades with
    a stale or never-initialized client while the DB already has an active key.
    """
    global _active_client, _active_cred_signature

    from backend.database import get_db

    db = get_db()
    row = db.execute(
        "SELECT key_id, key_secret FROM api_keys WHERE is_active = 1 ORDER BY id LIMIT 1"
    ).fetchone()
    if not row:
        _active_client = None
        _active_cred_signature = None
        return None

    sig = (row["key_id"], row["key_secret"])
    if _active_client is not None and _active_cred_signature == sig:
        return _active_client

    old = _active_client
    _active_client = KalshiClient(row["key_id"], row["key_secret"])
    _active_cred_signature = sig
    if old is not None and old is not _active_client:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            loop.create_task(old.close())
    return _active_client


def set_kalshi_client(client: Optional[KalshiClient]) -> None:
    """Set the REST client (e.g. at startup). Signature must match get_kalshi_client()."""
    global _active_client, _active_cred_signature
    _active_client = client
    if client is None:
        _active_cred_signature = None
    else:
        _active_cred_signature = (client.key_id, client._private_key_pem)
