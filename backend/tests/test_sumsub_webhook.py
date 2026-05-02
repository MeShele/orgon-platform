"""Unit tests for the Sumsub webhook receiver.

Approach: instantiate a tiny FastAPI app inside each test, register
the webhook router, override `app.state.sumsub` with a real
`SumsubService` (HMAC verification works without httpx — webhook
verification is local-only), and override `get_db_pool` with an
in-memory fake that records SQL calls.

We do NOT spin up a real Postgres for these tests — the webhook
handler's logic is what we want to verify; SQL parameter binding is
covered indirectly by the parameters threaded through to the fake
connection.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.api.routes_webhooks_sumsub import router as webhooks_sumsub_router
from backend.dependencies import get_db_pool
from backend.services.sumsub_service import SumsubService


WEBHOOK_SECRET = "test-webhook-secret"


# ────────────────────────────────────────────────────────────────────
# Fake DB pool — records every executed query for assertions
# ────────────────────────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, fixtures: list[dict] | None = None):
        self.queries: list[tuple[str, tuple]] = []
        # `fixtures` is a list of dicts that fetchrow returns in order;
        # `None` for "no row" entries.
        self._fixtures = list(fixtures or [])

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", (query, params)))
        if not self._fixtures:
            return None
        head = self._fixtures.pop(0)
        return head

    async def execute(self, query, *params):
        self.queries.append(("execute", (query, params)))


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        # Returning a context manager that yields the same conn.
        class _Ctx:
            async def __aenter__(s):
                return self._conn

            async def __aexit__(s, *a):
                return None

        return _Ctx()


# ────────────────────────────────────────────────────────────────────
# App builder — fresh app per test
# ────────────────────────────────────────────────────────────────────


def _build_app(
    sumsub_enabled: bool = True,
    db_fixtures: list[dict] | None = None,
) -> tuple[FastAPI, _FakeConn]:
    app = FastAPI()
    app.include_router(webhooks_sumsub_router)
    if sumsub_enabled:
        app.state.sumsub = SumsubService(
            app_token="tok",
            secret_key="sec",
            webhook_secret=WEBHOOK_SECRET,
        )
    else:
        app.state.sumsub = None

    fake_conn = _FakeConn(fixtures=db_fixtures)
    fake_pool = _FakePool(fake_conn)
    app.dependency_overrides[get_db_pool] = lambda: fake_pool
    return app, fake_conn


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


# ────────────────────────────────────────────────────────────────────
# Signature verification
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_returns_403_without_signature():
    app, _ = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=b'{"applicantId":"x"}',
            headers={"content-type": "application/json"},
        )
    assert resp.status_code == 403
    assert "Invalid signature" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_returns_403_with_tampered_body():
    app, _ = _build_app()
    body = b'{"applicantId":"x"}'
    sig = _sign(body)
    tampered = body + b" "
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=tampered,
            headers={"X-Payload-Digest": sig, "content-type": "application/json"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_returns_503_when_sumsub_disabled():
    app, _ = _build_app(sumsub_enabled=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=b"{}",
            headers={"X-Payload-Digest": "anything"},
        )
    assert resp.status_code == 503


# ────────────────────────────────────────────────────────────────────
# Routing for unknown applicants
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_ignores_unknown_applicant():
    """Webhook for an applicant we never created — accept (200, ignored)."""
    app, conn = _build_app(db_fixtures=[])  # fetchrow returns None
    body = json.dumps({
        "applicantId": "stranger",
        "type": "applicantReviewed",
        "reviewStatus": "completed",
        "reviewResult": {"reviewAnswer": "GREEN"},
        "correlationId": "evt-1",
    }).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": _sign(body), "content-type": "application/json"},
        )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["ignored"] == "unknown applicant"
    # Only the lookup happened — no UPDATEs.
    op_kinds = [op for op, _ in conn.queries]
    assert op_kinds == ["fetchrow"]


# ────────────────────────────────────────────────────────────────────
# Idempotency
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_idempotent_on_duplicate_correlation_id():
    """Re-delivery of same event ID → no-op success."""
    app, conn = _build_app(
        db_fixtures=[{"user_id": 7, "last_event_id": "evt-dup", "review_status": "completed"}]
    )
    body = json.dumps({
        "applicantId": "applicant-7",
        "type": "applicantReviewed",
        "reviewStatus": "completed",
        "reviewResult": {"reviewAnswer": "GREEN"},
        "correlationId": "evt-dup",
    }).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": _sign(body), "content-type": "application/json"},
        )
    assert resp.status_code == 200
    assert resp.json()["duplicate"] is True
    # Lookup happened, no UPDATE/INSERT.
    assert all(op == "fetchrow" for op, _ in conn.queries)


# ────────────────────────────────────────────────────────────────────
# Status mapping (ADR-5)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "review_status,review_result,expected_mapped",
    [
        ("init", {}, "not_started"),
        ("pending", {}, "pending"),
        ("queued", {}, "pending"),
        ("onHold", {}, "manual_review"),
        ("completed", {"reviewAnswer": "GREEN"}, "approved"),
        ("completed", {"reviewAnswer": "RED"}, "rejected"),
        ("completed", {"reviewAnswer": "RED", "clientComment": "blurry passport"}, "needs_resubmit"),
    ],
)
async def test_webhook_maps_each_status(review_status, review_result, expected_mapped):
    app, conn = _build_app(
        db_fixtures=[{"user_id": 42, "last_event_id": None, "review_status": "init"}]
    )
    body = json.dumps({
        "applicantId": "applicant-42",
        "type": "applicantReviewed",
        "reviewStatus": review_status,
        "reviewResult": review_result,
        "correlationId": f"evt-{review_status}-{review_result.get('reviewAnswer','')}",
    }).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": _sign(body), "content-type": "application/json"},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["mapped_status"] == expected_mapped

    # Two UPDATEs expected: sumsub_applicants cache + kyc_submissions mirror.
    update_count = sum(1 for op, _ in conn.queries if op == "execute")
    assert update_count >= 2


# ────────────────────────────────────────────────────────────────────
# AML alert path
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_writes_aml_alert_on_sanctions_label():
    """When reviewResult.rejectLabels contains an AML/SANCTIONS marker
    AND it's an onHold/RED state, we record an aml_alerts row."""
    app, conn = _build_app(
        db_fixtures=[{"user_id": 99, "last_event_id": None, "review_status": "init"}]
    )
    body = json.dumps({
        "applicantId": "applicant-99",
        "type": "applicantOnHold",
        "reviewStatus": "onHold",
        "reviewResult": {"rejectLabels": ["SANCTIONS", "AML_RISK"]},
        "correlationId": "evt-aml-1",
    }).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": _sign(body), "content-type": "application/json"},
        )
    assert resp.status_code == 200

    # Find the aml_alerts INSERT.
    aml_inserts = [
        (op, args) for op, args in conn.queries
        if op == "execute" and "INSERT INTO aml_alerts" in args[0]
    ]
    assert len(aml_inserts) == 1
    _, (sql, params) = aml_inserts[0]
    # First param is alert_type, second is severity.
    assert params[0] == "sumsub:applicantOnHold"
    assert params[1] == "high"  # SANCTIONS / AML_RISK → high severity


@pytest.mark.asyncio
async def test_webhook_does_not_write_aml_for_clean_review():
    app, conn = _build_app(
        db_fixtures=[{"user_id": 50, "last_event_id": None, "review_status": "init"}]
    )
    body = json.dumps({
        "applicantId": "applicant-50",
        "type": "applicantReviewed",
        "reviewStatus": "completed",
        "reviewResult": {"reviewAnswer": "GREEN"},
        "correlationId": "evt-clean",
    }).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": _sign(body), "content-type": "application/json"},
        )
    assert resp.status_code == 200
    # No aml_alerts INSERT.
    assert not any(
        op == "execute" and "INSERT INTO aml_alerts" in args[0]
        for op, args in conn.queries
    )


# ────────────────────────────────────────────────────────────────────
# Malformed JSON
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_webhook_returns_400_on_malformed_json_body():
    """HMAC verifies on raw bytes — but if those bytes aren't JSON we
    can't proceed. Sumsub itself never sends malformed JSON; this is
    a robustness test for fuzz/scan attempts."""
    app, _ = _build_app()
    body = b"not-a-json"
    sig = _sign(body)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": sig, "content-type": "application/json"},
        )
    assert resp.status_code == 400
    assert "Malformed JSON" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_payload_without_applicant_id_is_ignored():
    """Sumsub occasionally sends meta-events with no applicantId
    (e.g. test-pings). We accept (200, ignored) so the dashboard
    shows green."""
    app, _ = _build_app()
    body = json.dumps({"type": "ping"}).encode()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/webhooks/sumsub",
            content=body,
            headers={"X-Payload-Digest": _sign(body), "content-type": "application/json"},
        )
    assert resp.status_code == 200
    assert resp.json()["ignored"] == "no applicantId"
