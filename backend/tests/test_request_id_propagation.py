"""Correlation-ID propagation tests (E-02).

We verify that the `request_id` parameter threads through the
business-logic surfaces that persist state — webhook publisher and
the Safina HTTP client outbound header. The middleware-side
generation is exercised by the live `/v1/*` integration suite.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.services import webhook_publisher as wp


# ────────────────────────────────────────────────────────────────────
# Fake pool (same shape as test_idempotency).
# ────────────────────────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, fetchrow_result: Any = None):
        self._fetchrow_result = fetchrow_result
        self.queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", (query, params)))
        return self._fetchrow_result

    async def execute(self, query, *params):
        self.queries.append(("execute", (query, params)))


class _FakeAcq:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc_info):
        return None


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _FakeAcq(self._conn)


# ────────────────────────────────────────────────────────────────────
# webhook_publisher — originating_request_id reaches the INSERT
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_event_records_request_id():
    conn = _FakeConn(fetchrow_result={"id": "00000000-0000-0000-0000-0000000000aa"})
    pool = _FakePool(conn)

    delivery_id = await wp.publish_event(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        event_type=wp.EV_TX_CONFIRMED,
        payload={"tx_id": "T1"},
        request_id="req-abc-123",
    )
    assert delivery_id == "00000000-0000-0000-0000-0000000000aa"

    assert len(conn.queries) == 1
    op, (query, params) = conn.queries[0]
    assert op == "fetchrow"
    assert "INSERT INTO webhook_deliveries" in query
    assert "originating_request_id" in query
    # params order: ($1 merchant_id::uuid, $2 event_type, $3 payload, $4 request_id)
    assert str(params[0]) == "11111111-2222-3333-4444-555555555555"
    assert params[1] == wp.EV_TX_CONFIRMED
    assert json.loads(params[2]) == {"tx_id": "T1"}
    assert params[3] == "req-abc-123"


@pytest.mark.asyncio
async def test_publish_event_none_request_id_inserts_null():
    """Cron-driven events (no API origin) MUST pass NULL, not 'None'."""
    conn = _FakeConn(fetchrow_result={"id": "00000000-0000-0000-0000-0000000000bb"})
    pool = _FakePool(conn)

    await wp.publish_event(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        event_type=wp.EV_WALLET_DEPOSIT,
        payload={},
    )
    op, (query, params) = conn.queries[0]
    assert params[3] is None, "request_id must be a real NULL, not the string 'None'"


# ────────────────────────────────────────────────────────────────────
# Safina client — X-Origin-Request-Id forwarded when supplied
# ────────────────────────────────────────────────────────────────────


class _FakeSafinaSigner:
    """Just enough surface for SafinaPayClient._request to call."""
    address = "0xfeedfacefeedfacefeedfacefeedfacefeedface"

    def sign_get(self):
        return {"X-Sig-Sample": "g"}

    def sign_post(self, data):
        return {"X-Sig-Sample": "p"}


class _FakeHttpResponse:
    def __init__(self, payload: Any):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeHttpClient:
    def __init__(self):
        self.calls: list[tuple[str, str, dict]] = []
        self.is_closed = False

    async def get(self, url, headers=None):
        self.calls.append(("GET", url, dict(headers or {})))
        return _FakeHttpResponse({"ok": True})

    async def post(self, url, headers=None, content=None):
        self.calls.append(("POST", url, dict(headers or {})))
        return _FakeHttpResponse({"ok": True})

    async def aclose(self):
        self.is_closed = True


@pytest.mark.asyncio
async def test_safina_client_forwards_origin_request_id():
    from backend.safina.client import SafinaPayClient

    client = SafinaPayClient(signer=_FakeSafinaSigner())
    fake_http = _FakeHttpClient()
    client._client = fake_http  # bypass _get_client lazy init

    await client._request("GET", "ping", origin_request_id="req-xyz")

    assert len(fake_http.calls) == 1
    method, url, headers = fake_http.calls[0]
    assert headers.get("X-Origin-Request-Id") == "req-xyz"
    assert headers.get("X-Sig-Sample") == "g", "signer headers must survive merge"


@pytest.mark.asyncio
async def test_safina_client_omits_origin_request_id_when_none():
    from backend.safina.client import SafinaPayClient

    client = SafinaPayClient(signer=_FakeSafinaSigner())
    fake_http = _FakeHttpClient()
    client._client = fake_http

    await client._request("POST", "tx", {"amount": "1"})

    _, _, headers = fake_http.calls[0]
    assert "X-Origin-Request-Id" not in headers
    # And lowercase variant — don't leak any variant
    assert not any(k.lower() == "x-origin-request-id" for k in headers)
