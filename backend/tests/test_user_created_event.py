"""`user.created` webhook fire-once semantics.

POST /v1/users is idempotent on (merchant_id, external_id). The
webhook MUST fire exactly once — on the very first INSERT — and never
again on subsequent ON CONFLICT DO UPDATE re-calls. The discriminator
is Postgres's `xmax = 0` returned in the same statement.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.services import end_user_service as eus


class _FakeConn:
    def __init__(self, fetchrow_result: Any = None):
        self._fetchrow_result = fetchrow_result
        self.queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", (query, params)))
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


def _row(*, inserted: bool) -> dict:
    return {
        "id": "aaaa1111-2222-3333-4444-555555555555",
        "merchant_id": "11111111-2222-3333-4444-555555555555",
        "external_id": "ext-42",
        "email": "u@example.com",
        "kyc_status": None,
        "metadata": "{}",
        "created_at": None,
        "updated_at": None,
        "inserted": inserted,
    }


@pytest.mark.asyncio
async def test_user_created_fires_on_insert(monkeypatch):
    pool = _FakePool(_FakeConn(_row(inserted=True)))

    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({
            "merchant_id": merchant_id,
            "event_type": event_type,
            "payload": payload,
            "request_id": request_id,
        })
        return "delivery-xyz"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    out = await eus.create_user(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        external_id="ext-42",
        email="u@example.com",
        request_id="req-abc-123",
    )

    assert "inserted" not in out, "internal discriminator must not leak"
    assert len(captured) == 1, "exactly one publish on a fresh insert"
    ev = captured[0]
    assert ev["event_type"] == "user.created"
    assert ev["merchant_id"] == "11111111-2222-3333-4444-555555555555"
    assert ev["payload"] == {
        "id": "aaaa1111-2222-3333-4444-555555555555",
        "external_id": "ext-42",
        "email": "u@example.com",
        "kyc_status": None,
    }
    assert ev["request_id"] == "req-abc-123"


@pytest.mark.asyncio
async def test_user_created_does_not_fire_on_conflict_update(monkeypatch):
    pool = _FakePool(_FakeConn(_row(inserted=False)))

    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(event_type)
        return "should-not-be-called"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    out = await eus.create_user(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        external_id="ext-42",
        email="u@example.com",
    )

    assert "inserted" not in out
    assert captured == [], "ON CONFLICT DO UPDATE MUST NOT re-fire user.created"


@pytest.mark.asyncio
async def test_user_created_publish_failure_does_not_break_create(monkeypatch):
    """If the webhook publish hiccups (DB blip, etc.), the user creation
    itself still returns successfully — webhooks are best-effort."""
    pool = _FakePool(_FakeConn(_row(inserted=True)))

    async def boom(*a, **kw):
        raise RuntimeError("webhook queue down")

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", boom
    )

    out = await eus.create_user(
        pool,
        merchant_id="11111111-2222-3333-4444-555555555555",
        external_id="ext-42",
        email="u@example.com",
    )
    assert out["id"] == "aaaa1111-2222-3333-4444-555555555555"
