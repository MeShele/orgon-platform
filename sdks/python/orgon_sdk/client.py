from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Optional
from urllib.parse import urlencode, urlparse

import httpx

DEFAULT_BASE = "https://orgon.asystem.ai"


class OrgonError(RuntimeError):
    """Typed error matching the server's standardized envelope:

        {"error": "<code>", "message": "<...>", "request_id": "..."}
    """

    def __init__(self, status: int, body: Any, message: str):
        super().__init__(message)
        self.status = status
        self.body = body


class _ResourceBase:
    def __init__(self, request):
        self._request = request


class _Users(_ResourceBase):
    def create(self, *, external_id: str, email: str, kyc_status: Optional[str] = None, metadata: Optional[dict] = None) -> dict:
        body = {"external_id": external_id, "email": email}
        if kyc_status is not None:
            body["kyc_status"] = kyc_status
        if metadata is not None:
            body["metadata"] = metadata
        return self._request("POST", "/v1/users", body=body)

    def get(self, user_id: str) -> dict:
        return self._request("GET", f"/v1/users/{user_id}")

    def list(self, *, cursor: Optional[str] = None, limit: int = 50) -> dict:
        return self._request("GET", "/v1/users", query={"cursor": cursor, "limit": limit})

    def update(self, user_id: str, **fields) -> dict:
        return self._request("PATCH", f"/v1/users/{user_id}", body=fields)


class _Wallets(_ResourceBase):
    def create(self, *, network, end_user_id: Optional[str] = None, treasury: Optional[str] = None, info: Optional[str] = None) -> dict:
        body = {"network": str(network)}
        if end_user_id:
            body["end_user_id"] = end_user_id
        if treasury:
            body["treasury"] = treasury
        if info is not None:
            body["info"] = info
        return self._request("POST", "/v1/wallets", body=body)

    def get(self, wallet_id: str) -> dict:
        return self._request("GET", f"/v1/wallets/{wallet_id}")

    def list_for_user(self, user_id: str) -> dict:
        return self._request("GET", f"/v1/users/{user_id}/wallets")


class _Transactions(_ResourceBase):
    def send(self, *, wallet_id: str, to_address: str, amount: str, asset: str = "TRX", info: Optional[str] = None) -> dict:
        body = {"wallet_id": wallet_id, "to_address": to_address, "amount": amount, "asset": asset}
        if info is not None:
            body["info"] = info
        return self._request("POST", "/v1/transactions", body=body)

    def sign(self, tx_id: str) -> dict:
        return self._request("POST", f"/v1/transactions/{tx_id}/sign")

    def get(self, tx_id: str) -> dict:
        return self._request("GET", f"/v1/transactions/{tx_id}")

    def list(self, *, wallet_id: Optional[str] = None, cursor: Optional[str] = None, limit: int = 50) -> dict:
        return self._request("GET", "/v1/transactions", query={"wallet_id": wallet_id, "cursor": cursor, "limit": limit})


class _Deposits(_ResourceBase):
    def list_for_wallet(self, wallet_id: str, *, cursor: Optional[str] = None, limit: int = 50) -> dict:
        return self._request("GET", f"/v1/wallets/{wallet_id}/deposits", query={"cursor": cursor, "limit": limit})

    def list_for_user(self, user_id: str, *, cursor: Optional[str] = None, limit: int = 50) -> dict:
        return self._request("GET", f"/v1/users/{user_id}/deposits", query={"cursor": cursor, "limit": limit})


class _WebhooksConfig(_ResourceBase):
    def get(self) -> dict:
        return self._request("GET", "/v1/webhooks/config")

    def update(self, *, url: Optional[str] = None, secret: Optional[str] = None) -> dict:
        body = {}
        if url is not None:
            body["url"] = url
        if secret is not None:
            body["secret"] = secret
        return self._request("PUT", "/v1/webhooks/config", body=body)


class _Webhooks(_ResourceBase):
    def __init__(self, request):
        super().__init__(request)
        self.config = _WebhooksConfig(request)

    def deliveries(self, *, cursor: Optional[str] = None, limit: int = 50) -> dict:
        return self._request("GET", "/v1/webhooks/deliveries", query={"cursor": cursor, "limit": limit})

    def test(self, *, event_type: str = "webhook.test", payload: Optional[dict] = None) -> dict:
        body = {"event_type": event_type}
        if payload is not None:
            body["payload"] = payload
        return self._request("POST", "/v1/webhooks/test", body=body)


class _Invoices(_ResourceBase):
    def list(self, *, limit: int = 24) -> dict:
        return self._request("GET", "/v1/invoices", query={"limit": limit})


class OrgonClient:
    """Synchronous client. For async usage see `OrgonAsyncClient` (planned)."""

    def __init__(
        self,
        api_key: str,
        secret: str,
        base_url: str = DEFAULT_BASE,
        *,
        http_client: Optional[httpx.Client] = None,
    ):
        if not api_key:
            raise ValueError("api_key required")
        if not secret:
            raise ValueError("secret required")
        self._key = api_key
        self._secret = secret
        self._base = base_url.rstrip("/")
        self._http = http_client or httpx.Client(timeout=15.0)

        self.users = _Users(self._request)
        self.wallets = _Wallets(self._request)
        self.transactions = _Transactions(self._request)
        self.deposits = _Deposits(self._request)
        self.webhooks = _Webhooks(self._request)
        self.invoices = _Invoices(self._request)

    @property
    def sandbox(self) -> bool:
        return self._key.startswith("okt_")

    def ping(self) -> dict:
        return self._request("GET", "/v1/ping")

    def health(self) -> dict:
        # Unsigned endpoint.
        r = self._http.get(f"{self._base}/v1/health")
        return r.json()

    def _request(self, method: str, path: str, *, body: Any = None, query: Optional[dict] = None) -> Any:
        clean_query = {k: str(v) for k, v in (query or {}).items() if v is not None and v != ""}
        url = self._base + path
        if clean_query:
            url += "?" + urlencode(clean_query)
        raw = json.dumps(body, separators=(",", ":")) if body is not None else ""
        ts = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        # Sign only the path (no query), matching the server.
        sig_path = urlparse(url).path
        msg = f"{ts}\n{nonce}\n{method.upper()}\n{sig_path}\n".encode() + raw.encode()
        sig = hmac.new(self._secret.encode(), msg, hashlib.sha256).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-ORGON-Key": self._key,
            "X-ORGON-Timestamp": ts,
            "X-ORGON-Nonce": nonce,
            "X-ORGON-Signature": sig,
        }
        r = self._http.request(method.upper(), url, headers=headers, content=raw or None)
        text = r.text or ""
        try:
            parsed = json.loads(text) if text else None
        except Exception:
            parsed = text
        if r.status_code >= 400:
            msg_str = ""
            if isinstance(parsed, dict):
                msg_str = parsed.get("message") or parsed.get("error") or ""
            raise OrgonError(r.status_code, parsed, msg_str or f"ORGON {r.status_code}")
        return parsed
