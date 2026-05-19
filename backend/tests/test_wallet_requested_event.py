"""`wallet.requested` fires once at the moment ORGON enqueues a new
wallet provisioning request — long before Safina returns an address.

Purpose: give the merchant a `t=0` signal so their UI can show an
honest "generating address, usually 60-90s" timer instead of a silent
spinner. `wallet.activated` follows when Safina actually fills `addr`.

Tests target `_emit_wallet_requested` directly — the public helper
that both `provision_user_wallet` and `provision_treasury_wallet`
call after a fresh INSERT (NOT on ON CONFLICT race or reuse).
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.services import merchant_wallet_service as mws


class _FakeConn:
    def __init__(self, fetchrow_result: Any = None):
        self._fetchrow_result = fetchrow_result
        self.queries: list = []

    async def fetchrow(self, query, *params):
        self.queries.append((query, params))
        return self._fetchrow_result


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


@pytest.mark.asyncio
async def test_emit_user_deposit_payload(monkeypatch):
    pool = _FakePool(_FakeConn({"id": "deliv-1"}))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({"merchant_id": merchant_id, "event_type": event_type, "payload": payload})
        return "deliv-1"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    await mws._emit_wallet_requested(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        wallet_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        end_user_id="ccccccc1-2222-3333-4444-555555555555",
        network=5010,
        purpose="user_deposit",
    )

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event_type"] == "wallet.requested"
    assert ev["merchant_id"] == "11111111-2222-3333-4444-555555555555"

    p = ev["payload"]
    assert p["wallet_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert p["end_user_id"] == "ccccccc1-2222-3333-4444-555555555555"
    assert p["network"] == 5010
    assert p["purpose"] == "user_deposit"
    # Hint matters — without it merchant has no honest UX signal
    assert p["estimated_activation_seconds"] == 90


@pytest.mark.asyncio
async def test_emit_treasury_payload_has_null_end_user(monkeypatch):
    """Treasury wallets are merchant-owned; `end_user_id` MUST be null
    in the payload — important so merchant UI doesn't try to associate
    a non-existent user with the wallet."""
    pool = _FakePool(_FakeConn({"id": "deliv-2"}))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload)

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    await mws._emit_wallet_requested(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        wallet_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        end_user_id=None,
        network=5010,
        purpose="treasury",
    )

    assert captured[0]["end_user_id"] is None
    assert captured[0]["purpose"] == "treasury"


@pytest.mark.asyncio
async def test_emit_each_treasury_kind(monkeypatch):
    """The four treasury kinds all flow through the same helper. None
    of them should be coerced to `user_deposit` or rejected."""
    captured: list[str] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload["purpose"])

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    pool = _FakePool(_FakeConn(None))
    for kind in ("treasury", "fee", "hot", "cold"):
        await mws._emit_wallet_requested(
            pool,
            merchant_id="11111111-2222-3333-4444-555555555555",
            wallet_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            end_user_id=None,
            network=5010,
            purpose=kind,
        )

    assert captured == ["treasury", "fee", "hot", "cold"]


@pytest.mark.asyncio
async def test_emit_publish_failure_is_non_fatal(monkeypatch):
    """A webhook queue blip must NOT propagate out of provisioning.
    Failed wallet.requested is logged-and-dropped, the wallet still
    exists in our DB and `wallet.activated` will fire later when
    Safina is ready."""
    pool = _FakePool(_FakeConn(None))

    async def boom(*a, **kw):
        raise RuntimeError("webhook queue down")

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", boom
    )

    # Must not raise
    await mws._emit_wallet_requested(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        wallet_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        end_user_id=None,
        network=5010,
        purpose="treasury",
    )
