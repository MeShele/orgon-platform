"""Wire-up tests for SAR submission endpoints (Wave 24, Story 2.9).

Reuses the FakeAsyncDB pattern from `test_aml_alerts.py`. We script
the alert lookup → org lookup → SAR insert in fixture order so the
service-layer code under test runs the same path as production.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.api.routes_compliance import router as compliance_router
from backend.dependencies import get_current_user, get_db_pool, get_user_org_ids


# ────────────────────────────────────────────────────────────────────
# Fakes
# ────────────────────────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, fixtures=None):
        self._fixtures = list(fixtures or [])
        self.queries: list[tuple[str, str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", query, params))
        if not self._fixtures:
            return None
        head = self._fixtures.pop(0)
        return head

    async def fetch(self, query, *params):
        self.queries.append(("fetch", query, params))
        if not self._fixtures:
            return []
        head = self._fixtures.pop(0)
        return head if isinstance(head, list) else [head]

    async def execute(self, query, *params):
        self.queries.append(("execute", query, params))


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
        "id": 7, "email": "auditor@orgon.test", "full_name": "Test Auditor",
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
        "alert_type": "sumsub:applicantOnHold",
        "severity": "critical",
        "status": "investigating",
        "description": "Sanctions hit",
        "transaction_id": None,
        "wallet_id": None,
        "kyc_record_id": None,
        "details": {"applicantId": "abc"},
        "assigned_to": 7, "investigated_by": None, "investigated_at": None,
        "investigation_notes": None,
        "resolution": "Confirmed sanctioned address",
        "reported_to_regulator": False, "reported_at": None,
        "report_reference": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "assigned_to_email": None, "assigned_to_name": None,
        "investigated_by_email": None, "investigated_by_name": None,
        "related_transaction": None,
    }
    base.update(kw)
    return base


def _org_row(org_id=None):
    return {
        "id": org_id or uuid.uuid4(),
        "name": "Acme Custody KG",
        "legal_address": "Bishkek, Manas 1",
        "country": "KG",
    }


def _sar_row(alert_id, **kw):
    base = {
        "id": uuid.uuid4(),
        "alert_id": alert_id,
        "organization_id": uuid.uuid4(),
        "submitted_by": 7,
        "submission_backend": "manual_export",
        "payload_json": {"schema_version": "orgon.sar.v1"},
        "rendered_markdown": "# SAR\n\n…",
        "status": "prepared",
        "external_reference": None,
        "response_body": "manual_export — payload prepared",
        "submitted_at": datetime.now(timezone.utc),
        "acknowledged_at": None,
    }
    base.update(kw)
    return base


# ────────────────────────────────────────────────────────────────────
# POST /aml/alerts/{id}/sar
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_sar_creates_new_row(monkeypatch):
    """Fresh alert (no existing SAR) → INSERT and return SarSubmissionResponse."""
    monkeypatch.delenv("FINSUPERVISORY_SAR_BACKEND", raising=False)
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    # service flow:
    #  1) get_aml_alert → fetchrow alert (with JOINs)
    #  2) fetchrow existing SAR → None
    #  3) fetchrow organizations
    #  4) fetchrow INSERT INTO sar_submissions RETURNING *
    fixtures = [
        alert,
        None,
        _org_row(org_id=org),
        _sar_row(aid, organization_id=org),
    ]
    app, conn = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/sar", json={})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["alert_id"] == str(aid)
    assert body["submission_backend"] == "manual_export"
    assert body["status"] == "prepared"


@pytest.mark.asyncio
async def test_submit_sar_idempotent_returns_existing(monkeypatch):
    monkeypatch.delenv("FINSUPERVISORY_SAR_BACKEND", raising=False)
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    existing = _sar_row(aid, organization_id=org)
    fixtures = [alert, existing]   # 2nd fetchrow returns existing → short-circuit
    app, conn = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/sar", json={})
    assert r.status_code == 201
    # No INSERT happened — only the two fetchrow lookups.
    inserts = [q for op, q, _ in conn.queries if "INSERT INTO sar_submissions" in q]
    assert inserts == []


@pytest.mark.asyncio
async def test_submit_sar_404_when_alert_out_of_scope():
    aid = uuid.uuid4()
    # First fetchrow (alert lookup) returns None — out-of-scope or missing.
    app, _ = _build_app(fixtures=[None], org_ids=[uuid.uuid4()])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/sar", json={})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submit_sar_422_on_unknown_backend(monkeypatch):
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    # Alert exists, no existing SAR → service tries to resolve backend.
    fixtures = [alert, None, _org_row(org_id=org)]
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/sar",
            json={"backend": "nonexistent"},
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_sar_422_for_api_v1_until_implemented():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    fixtures = [alert, None, _org_row(org_id=org)]
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/sar",
            json={"backend": "api_v1"},
        )
    assert r.status_code == 422
    assert "not implemented" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_sar_dryrun_succeeds(monkeypatch):
    monkeypatch.delenv("FINSUPERVISORY_SAR_BACKEND", raising=False)
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    fixtures = [
        alert, None, _org_row(org_id=org),
        _sar_row(aid, organization_id=org, submission_backend="dryrun",
                 response_body="dryrun — nothing was sent"),
    ]
    app, conn = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/sar",
            json={"backend": "dryrun"},
        )
    assert r.status_code == 201
    assert r.json()["submission_backend"] == "dryrun"


# ────────────────────────────────────────────────────────────────────
# GET endpoints
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_sar_returns_existing_row():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    sar = _sar_row(aid, organization_id=org)
    # service.get_sar_submission flow: get_aml_alert (1 fetchrow) + sar fetchrow.
    fixtures = [alert, sar]
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/aml/alerts/{aid}/sar")
    assert r.status_code == 200
    assert r.json()["alert_id"] == str(aid)


@pytest.mark.asyncio
async def test_get_sar_json_returns_attachment():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    payload = {"schema_version": "orgon.sar.v1", "filing_org": {"name": "Acme"}}
    sar = _sar_row(aid, organization_id=org, payload_json=payload)
    fixtures = [alert, sar]
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/aml/alerts/{aid}/sar.json")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert r.headers["content-type"].startswith("application/json")
    assert json.loads(r.text)["filing_org"]["name"] == "Acme"


@pytest.mark.asyncio
async def test_get_sar_md_returns_markdown():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    sar = _sar_row(aid, organization_id=org,
                   rendered_markdown="# SAR\n\nfor Acme")
    fixtures = [alert, sar]
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/aml/alerts/{aid}/sar.md")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert "# SAR" in r.text


@pytest.mark.asyncio
async def test_get_sar_404_when_no_submission_yet():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    alert = _alert_row(id=aid, organization_id=org)
    fixtures = [alert, None]    # alert exists but no SAR yet
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/aml/alerts/{aid}/sar")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_sar_endpoints_rbac_block_signer():
    aid = uuid.uuid4()
    app, _ = _build_app(
        fixtures=[],
        user={"id": 1, "role": "signer", "email": "s",
              "is_active": True, "full_name": "S"},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/sar", json={})
    assert r.status_code == 403
