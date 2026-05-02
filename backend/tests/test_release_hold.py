"""Tests for the release-from-hold endpoint (Wave 26, Story 2.11)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.api.routes_compliance import router as compliance_router
from backend.dependencies import get_current_user, get_db_pool, get_user_org_ids


# ────────────────────────────────────────────────────────────────────
# Fakes (same shape as test_aml_alerts.py / test_monitoring_rules.py)
# ────────────────────────────────────────────────────────────────────


class _FakeTxn:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return None


class _FakeConn:
    def __init__(self, fixtures=None):
        self._fixtures = list(fixtures or [])
        self.queries: list[tuple[str, str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", query, params))
        if not self._fixtures:
            return None
        return self._fixtures.pop(0)

    async def fetch(self, query, *params):
        self.queries.append(("fetch", query, params))
        if not self._fixtures:
            return []
        head = self._fixtures.pop(0)
        return head if isinstance(head, list) else [head]

    async def execute(self, query, *params):
        self.queries.append(("execute", query, params))

    def transaction(self):
        return _FakeTxn()


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        outer = self

        class _Ctx:
            async def __aenter__(_s):
                return outer._conn

            async def __aexit__(_s, *exc):
                return None

        return _Ctx()


def _build_app(fixtures=None, user=None, org_ids=None):
    app = FastAPI()
    app.include_router(compliance_router)
    fake_conn = _FakeConn(fixtures)
    app.dependency_overrides[get_db_pool] = lambda: _FakePool(fake_conn)
    default_user = user or {
        "id": 5, "email": "auditor@orgon.test", "full_name": "Test Auditor",
        "role": "company_auditor", "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: default_user
    if org_ids is None and default_user.get("role") not in (
        "super_admin", "platform_admin", "admin"
    ):
        org_ids = [uuid.uuid4()]
    app.dependency_overrides[get_user_org_ids] = lambda: org_ids
    return app, fake_conn


def _alert_row(**kw):
    base = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "alert_type": "rule:threshold",
        "severity": "high",
        "status": "open",
        "description": "Threshold $10k tripped",
        "transaction_id": None,
        "wallet_id": None,
        "kyc_record_id": None,
        "details": {},
        "assigned_to": 5,
        "investigated_by": None,
        "investigated_at": None,
        "investigation_notes": None,
        "resolution": None,
        "reported_to_regulator": False,
        "reported_at": None,
        "report_reference": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(kw)
    return base


# ────────────────────────────────────────────────────────────────────
# Happy path
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_release_hold_succeeds_and_audits():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    tx_id = uuid.uuid4()
    pre_alert = _alert_row(id=aid, organization_id=org, transaction_id=tx_id)
    tx_locked = {"id": tx_id, "unid": "tx_unid_1", "status": "on_hold"}
    tx_after = {"id": tx_id, "unid": "tx_unid_1", "status": "pending"}
    fixtures = [pre_alert, tx_locked, tx_after]
    app, conn = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/release-hold",
            json={"reason": "Manual review cleared the false positive"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tx_status"] == "pending"
    assert body["tx_unid"] == "tx_unid_1"
    # Audit-log INSERT happened.
    audits = [s for op, s, _ in conn.queries if op == "execute" and "audit_log" in s]
    assert len(audits) == 1


# ────────────────────────────────────────────────────────────────────
# Error branches
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_release_hold_404_when_alert_missing():
    app, _ = _build_app(fixtures=[None])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{uuid.uuid4()}/release-hold",
            json={"reason": "anything"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_release_hold_422_when_alert_has_no_tx():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre_alert = _alert_row(id=aid, organization_id=org, transaction_id=None)
    app, _ = _build_app(fixtures=[pre_alert], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/release-hold",
            json={"reason": "x"},
        )
    assert r.status_code == 422
    assert "no linked transaction" in r.json()["detail"]


@pytest.mark.asyncio
async def test_release_hold_409_when_tx_not_held():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    tx_id = uuid.uuid4()
    pre_alert = _alert_row(id=aid, organization_id=org, transaction_id=tx_id)
    # Tx is already pending, not on_hold — release is a no-op.
    tx_locked = {"id": tx_id, "unid": "tx_unid_1", "status": "pending"}
    fixtures = [pre_alert, tx_locked]
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/release-hold",
            json={"reason": "x"},
        )
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["detail"] == "not_held"
    assert body["detail"]["current"]["status"] == "pending"


@pytest.mark.asyncio
async def test_release_hold_422_when_reason_blank():
    aid = uuid.uuid4()
    app, _ = _build_app(fixtures=[])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/release-hold",
            json={"reason": ""},
        )
    # Pydantic's min_length=1 surfaces as 422.
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_release_hold_403_for_signer():
    aid = uuid.uuid4()
    app, _ = _build_app(
        user={"id": 9, "role": "signer", "email": "s",
              "full_name": "S", "is_active": True},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/release-hold",
            json={"reason": "x"},
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_release_hold_404_for_other_org():
    """Auditor of a different org → 404 (don't leak existence)."""
    aid = uuid.uuid4()
    other_org = uuid.uuid4()
    # FOR UPDATE returns None for out-of-scope alert → not_found → 404.
    fixtures = [None]
    app, _ = _build_app(fixtures=fixtures, org_ids=[other_org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/release-hold",
            json={"reason": "x"},
        )
    assert r.status_code == 404
