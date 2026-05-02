"""Unit tests for the AML triage routes (Wave 21, Story 2.6).

Pattern continues `test_sumsub_webhook.py`: in-process FastAPI app +
fake DB pool that records every SQL call. We override
`get_user_org_ids` and `require_roles` shorthand via dependency
overrides so each test can dial RBAC up or down without minting JWTs.

The fake pool understands `conn.transaction()` as a no-op async ctx
manager so the service-layer's atomic UPDATE+audit-log path runs the
same code as in production.
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
# Fake DB infrastructure — records queries, returns scripted fixtures
# ────────────────────────────────────────────────────────────────────


class _FakeTxn:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return None


class _FakeConn:
    def __init__(self, fixtures: list[Any] | None = None):
        # Ordered list of objects returned by fetchrow/fetch in call order.
        # Each entry can be: a single dict (one row), a list[dict] (rows),
        # or None (miss).
        self._fixtures = list(fixtures or [])
        self.queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", (query, params)))
        if not self._fixtures:
            return None
        return self._fixtures.pop(0)

    async def fetch(self, query, *params):
        self.queries.append(("fetch", (query, params)))
        if not self._fixtures:
            return []
        head = self._fixtures.pop(0)
        if head is None:
            return []
        return head if isinstance(head, list) else [head]

    async def execute(self, query, *params):
        self.queries.append(("execute", (query, params)))

    def transaction(self):
        return _FakeTxn()


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        outer = self

        class _Ctx:
            async def __aenter__(_self):
                return outer._conn

            async def __aexit__(_self, *exc):
                return None

        return _Ctx()


# ────────────────────────────────────────────────────────────────────
# App builder — fresh app per test
# ────────────────────────────────────────────────────────────────────


def _build_app(
    fixtures: list[Any] | None = None,
    user: dict | None = None,
    org_ids: list[UUID] | None = None,
) -> tuple[FastAPI, _FakeConn]:
    app = FastAPI()
    app.include_router(compliance_router)

    fake_conn = _FakeConn(fixtures)
    fake_pool = _FakePool(fake_conn)
    app.dependency_overrides[get_db_pool] = lambda: fake_pool

    default_user = user or {
        "id": 42,
        "email": "auditor@orgon.test",
        "role": "company_auditor",
        "is_active": True,
        "full_name": "Test Auditor",
    }
    app.dependency_overrides[get_current_user] = lambda: default_user

    # Default org scope — single org for non-super_admin.
    if org_ids is None and default_user.get("role") not in (
        "super_admin", "platform_admin", "admin"
    ):
        org_ids = [uuid.uuid4()]
    app.dependency_overrides[get_user_org_ids] = lambda: org_ids

    return app, fake_conn


def _row(**kwargs) -> dict:
    """Build a fixture row with sane defaults so tests stay terse."""
    base = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "alert_type": "sumsub:applicantOnHold",
        "severity": "high",
        "status": "open",
        "description": "Sumsub flagged the applicant",
        "transaction_id": None,
        "wallet_id": None,
        "kyc_record_id": None,
        "details": {},
        "assigned_to": None,
        "investigated_by": None,
        "investigated_at": None,
        "investigation_notes": None,
        "resolution": None,
        "reported_to_regulator": False,
        "reported_at": None,
        "report_reference": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "assigned_to_email": None,
        "assigned_to_name": None,
        "investigated_by_email": None,
        "investigated_by_name": None,
        "related_transaction": None,
    }
    base.update(kwargs)
    return base


# ────────────────────────────────────────────────────────────────────
# List endpoint
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_alerts_filter_by_status():
    rows = [_row(status="open"), _row(status="open")]
    app, conn = _build_app(fixtures=[rows])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts?status=open")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"] is None
    op, (sql, params) = conn.queries[0]
    assert op == "fetch"
    assert "a.status = $" in sql
    assert "open" in params


@pytest.mark.asyncio
async def test_list_alerts_pagination_cursor():
    # Return limit+1 rows so the service emits a next_cursor.
    rows = [_row() for _ in range(51)]
    app, _ = _build_app(fixtures=[rows])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts?limit=50")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 50
    assert body["next_cursor"] is not None


@pytest.mark.asyncio
async def test_list_alerts_rbac_scoped_for_non_super_admin():
    org = uuid.uuid4()
    app, conn = _build_app(fixtures=[[]], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts")
    assert r.status_code == 200
    op, (sql, params) = conn.queries[0]
    assert "a.organization_id = ANY($1::uuid[])" in sql
    assert params[0] == [org]


@pytest.mark.asyncio
async def test_list_alerts_super_admin_sees_unscoped():
    app, conn = _build_app(
        fixtures=[[]],
        user={"id": 1, "role": "super_admin", "email": "s", "is_active": True, "full_name": "S"},
        org_ids=None,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts")
    assert r.status_code == 200
    _, (sql, _) = conn.queries[0]
    # No organization-scoping clause in WHERE (only `WHERE TRUE` plus the
    # LIMIT-tail). The column is fine in the SELECT projection.
    assert "a.organization_id = ANY" not in sql
    assert "WHERE TRUE" in sql


@pytest.mark.asyncio
async def test_list_alerts_rejects_signer_role():
    app, _ = _build_app(
        user={"id": 7, "role": "signer", "email": "s", "is_active": True, "full_name": "S"},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_list_alerts_rejects_malformed_cursor():
    app, _ = _build_app(fixtures=[[]])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts?cursor=not-base64!@#$")
    assert r.status_code == 400


# ────────────────────────────────────────────────────────────────────
# Single-alert + related transaction
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_alert_includes_related_transaction():
    alert = _row(
        transaction_id=uuid.uuid4(),
        related_transaction={"id": "tx-1", "amount": "10000"},
    )
    app, _ = _build_app(fixtures=[alert])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/aml/alerts/{alert['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["related_transaction"]["id"] == "tx-1"


@pytest.mark.asyncio
async def test_get_alert_404_when_out_of_scope():
    """A non-super_admin asking for an alert outside their org gets 404,
    not 403 — we must not leak existence."""
    app, _ = _build_app(fixtures=[None])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/aml/alerts/{uuid.uuid4()}")
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Claim endpoint
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_claim_alert_succeeds():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="open", assigned_to=None)
    after = _row(id=aid, organization_id=org, status="investigating", assigned_to=42)
    full = _row(id=aid, organization_id=org, status="investigating", assigned_to=42,
                assigned_to_email="auditor@orgon.test", assigned_to_name="Test Auditor")
    # claim_aml_alert calls: SELECT FOR UPDATE → UPDATE → INSERT audit_log
    # Then route refetches via get_aml_alert: SELECT with JOINs.
    app, conn = _build_app(fixtures=[pre, after, full], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/claim")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "investigating"
    assert body["assigned_to"] == 42
    # An audit_log INSERT happened.
    inserts = [q for op, q in conn.queries if op == "execute"]
    assert any("INSERT INTO audit_log" in sql for sql, _ in inserts)


@pytest.mark.asyncio
async def test_claim_alert_409_when_other_user_holds():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="investigating", assigned_to=99)
    app, _ = _build_app(fixtures=[pre], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/claim")
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["detail"] == "already_claimed"


@pytest.mark.asyncio
async def test_claim_alert_409_when_terminal():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="resolved", assigned_to=42)
    app, _ = _build_app(fixtures=[pre], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/claim")
    assert r.status_code == 409
    assert r.json()["detail"]["detail"] == "terminal_status"


@pytest.mark.asyncio
async def test_claim_alert_idempotent_for_same_user():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="investigating", assigned_to=42)
    after = _row(id=aid, organization_id=org, status="investigating", assigned_to=42)
    full = _row(id=aid, organization_id=org, status="investigating", assigned_to=42,
                assigned_to_email="auditor@orgon.test")
    app, _ = _build_app(fixtures=[pre, after, full], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/claim")
    assert r.status_code == 200
    assert r.json()["assigned_to"] == 42


@pytest.mark.asyncio
async def test_claim_alert_404_when_missing():
    app, _ = _build_app(fixtures=[None])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{uuid.uuid4()}/claim")
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Resolve endpoint
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_alert_writes_audit_log_atomically():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="investigating", assigned_to=42)
    after = _row(id=aid, organization_id=org, status="resolved", assigned_to=42,
                 resolution="No suspicious activity", investigated_by=42)
    full = _row(id=aid, organization_id=org, status="resolved",
                resolution="No suspicious activity")
    app, conn = _build_app(fixtures=[pre, after, full], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/resolve",
            json={"decision": "resolved", "resolution": "No suspicious activity"},
        )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "resolved"
    inserts = [q for op, q in conn.queries if op == "execute"]
    audit_inserts = [s for s, _ in inserts if "INSERT INTO audit_log" in s]
    assert len(audit_inserts) == 1


@pytest.mark.asyncio
async def test_resolve_reported_requires_report_reference():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    app, _ = _build_app(fixtures=[], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/resolve",
            json={"decision": "reported", "resolution": "Filed SAR"},
        )
    assert r.status_code == 422
    assert "report_reference" in r.json()["detail"]


@pytest.mark.asyncio
async def test_resolve_reported_with_reference_succeeds():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="investigating")
    after = _row(id=aid, organization_id=org, status="reported",
                 reported_to_regulator=True, report_reference="SAR-2026-001")
    full = _row(id=aid, organization_id=org, status="reported",
                reported_to_regulator=True, report_reference="SAR-2026-001")
    app, _ = _build_app(fixtures=[pre, after, full], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/resolve",
            json={
                "decision": "reported",
                "resolution": "Reported to Финнадзор",
                "report_reference": "SAR-2026-001",
            },
        )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "reported"
    assert body["reported_to_regulator"] is True
    assert body["report_reference"] == "SAR-2026-001"


@pytest.mark.asyncio
async def test_resolve_terminal_alert_409():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="reported")
    app, _ = _build_app(fixtures=[pre], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/resolve",
            json={"decision": "false_positive", "resolution": "trying to override"},
        )
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────
# Notes
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_append_note_succeeds():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="investigating")
    after = _row(id=aid, organization_id=org, status="investigating",
                 investigation_notes="[2026-05-02] user=42: Looks clean")
    full = _row(id=aid, organization_id=org, status="investigating",
                investigation_notes="[2026-05-02] user=42: Looks clean")
    app, conn = _build_app(fixtures=[pre, after, full], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/notes",
            json={"note": "Looks clean"},
        )
    assert r.status_code == 200
    inserts = [s for op, (s, _) in conn.queries if op == "execute"]
    assert any("INSERT INTO audit_log" in s for s in inserts)


@pytest.mark.asyncio
async def test_append_note_blocked_after_reported():
    aid = uuid.uuid4()
    org = uuid.uuid4()
    pre = _row(id=aid, organization_id=org, status="reported")
    app, _ = _build_app(fixtures=[pre], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            f"/api/v1/compliance/aml/alerts/{aid}/notes",
            json={"note": "trying to add"},
        )
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────
# Stats
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_counts():
    stats_row = {
        "open": 3, "investigating": 1, "resolved_30d": 5,
        "sev_low": 2, "sev_medium": 4, "sev_high": 2, "sev_critical": 1,
    }
    app, _ = _build_app(fixtures=[stats_row])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["open"] == 3
    assert body["investigating"] == 1
    assert body["resolved_30d"] == 5
    assert body["by_severity"]["critical"] == 1


# ════════════════════════════════════════════════════════════════════
# RBAC matrix (parametrized — Sprint 2.6.3)
# ════════════════════════════════════════════════════════════════════
#
# Verifies that non-triage roles get 403 on every state-mutating AML
# endpoint, and that triage roles (company_admin, company_auditor,
# super_admin) can reach the handler. We don't reassert the body —
# the existing tests above already cover successful flows for the
# auditor role; here we only check the auth gate.

# Legacy roles that map to triage roles per backend.rbac.LEGACY_ROLE_MAP:
#   admin   → company_admin    (triage)
#   viewer  → company_auditor  (triage)
#   signer  → company_operator (non-triage)
# We list canonical names only — RBAC tests over the legacy mapping are
# implicit through the require_roles() expansion.
_NON_TRIAGE_ROLES = ["company_operator", "signer", "end_user"]
_TRIAGE_ROLES = ["company_admin", "company_auditor", "super_admin", "platform_admin"]


def _user_for(role: str) -> dict:
    return {
        "id": 1,
        "email": f"{role}@orgon.test",
        "role": role,
        "is_active": True,
        "full_name": role.title(),
    }


@pytest.mark.parametrize("role", _NON_TRIAGE_ROLES)
@pytest.mark.parametrize("method,path", [
    ("GET", "/api/v1/compliance/aml/alerts"),
    ("GET", "/api/v1/compliance/aml/alerts/stats"),
])
@pytest.mark.asyncio
async def test_rbac_non_triage_roles_get_403_on_reads(role, method, path):
    app, _ = _build_app(user=_user_for(role))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.request(method, path)
    assert r.status_code == 403, f"role={role} {method} {path} expected 403 got {r.status_code}"


@pytest.mark.parametrize("role", _NON_TRIAGE_ROLES)
@pytest.mark.parametrize("op,body", [
    ("claim", None),
    ("resolve", {"decision": "resolved", "resolution": "x"}),
    ("notes", {"note": "x"}),
])
@pytest.mark.asyncio
async def test_rbac_non_triage_roles_get_403_on_writes(role, op, body):
    aid = uuid.uuid4()
    app, _ = _build_app(user=_user_for(role))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/compliance/aml/alerts/{aid}/{op}", json=body)
    assert r.status_code == 403, (
        f"role={role} op={op} expected 403 got {r.status_code}"
    )


@pytest.mark.parametrize("role", _TRIAGE_ROLES)
@pytest.mark.asyncio
async def test_rbac_triage_roles_can_read_list(role):
    app, _ = _build_app(
        user=_user_for(role),
        fixtures=[[]],
        # super_admin / platform_admin → no scoping; others → single org.
        org_ids=None if role in ("super_admin", "platform_admin") else [uuid.uuid4()],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/aml/alerts")
    assert r.status_code == 200, f"role={role} should read list, got {r.status_code}"


# ════════════════════════════════════════════════════════════════════
# Cursor round-trip — encode then decode then list
# ════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cursor_round_trip():
    """Use a cursor returned in one response as input to the next call."""
    rows_first = [_row() for _ in range(51)]
    app, _ = _build_app(fixtures=[rows_first])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.get("/api/v1/compliance/aml/alerts?limit=50")
    cursor = r1.json()["next_cursor"]
    assert cursor

    rows_second = [_row()]
    app2, conn2 = _build_app(fixtures=[rows_second])
    async with AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as ac:
        r2 = await ac.get(f"/api/v1/compliance/aml/alerts?limit=50&cursor={cursor}")
    assert r2.status_code == 200
    # Service got the cursor as a tuple of (datetime, UUID) — the WHERE
    # clause must reference both.
    op, (sql, _params) = conn2.queries[0]
    assert "(a.created_at, a.id) <" in sql
