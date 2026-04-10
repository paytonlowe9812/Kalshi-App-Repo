import httpx
import time
import base64
import logging
from typing import Optional
from urllib.parse import urlparse

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
DEMO_URL = "https://demo-api.kalshi.co/trade-api/v2"


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
    def __init__(self, key_id: str, private_key_pem: str, demo: bool = False):
        self.key_id = key_id
        self._private_key_pem = private_key_pem
        self.base_url = DEMO_URL if demo else BASE_URL
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
        result = await self.get_events(
            limit=5, status="open",
            series_ticker=series_ticker, with_nested_markets=True,
        )
        events = result.get("events", [])
        if not events:
            return None

        all_markets = []
        for evt in events:
            for m in evt.get("markets", []):
                status = m.get("status", "")
                if status not in ("active", "open"):
                    continue
                if m.get("ticker") == current_ticker:
                    continue
                all_markets.append(m)

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
            "type": type,
        }
        if price is not None:
            body["yes_price"] = price
        return await self._request("POST", "/portfolio/orders", json=body)

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


def get_kalshi_client() -> Optional[KalshiClient]:
    return _active_client


def set_kalshi_client(client: KalshiClient):
    global _active_client
    _active_client = client
