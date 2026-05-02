"""Tests for monitoring-rules CRUD endpoints (Wave 25, Story 2.10).

Covers:
- Per-rule_type config validation (422)
- RBAC: read-only roles vs write roles vs global-rule restriction
- CRUD round-trip via FakeAsyncDB
- Audit-log writes on create/update/delete
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from backend.api.routes_compliance import router as compliance_router
from backend.dependencies import get_current_user, get_db_pool, get_user_org_ids


# ────────────────────────────────────────────────────────────────────
# Fakes
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
        "id": 5, "email": "admin@orgon.test", "full_name": "Co Admin",
        "role": "company_admin", "is_active": True,
    }
    app.dependency_overrides[get_current_user] = lambda: default_user
    if org_ids is None and default_user.get("role") not in (
        "super_admin", "platform_admin", "admin"
    ):
        org_ids = [uuid.uuid4()]
    app.dependency_overrides[get_user_org_ids] = lambda: org_ids
    return app, fake_conn


def _rule_row(**kw):
    base = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "rule_name": "ten-k threshold",
        "rule_type": "threshold",
        "description": "Block tx > $10k",
        "rule_config": {"threshold_usd": 10000},
        "action": "block",
        "severity": "critical",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "created_by": 5,
    }
    base.update(kw)
    return base


# ────────────────────────────────────────────────────────────────────
# List + read
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_rules_returns_visible_rows():
    org = uuid.uuid4()
    rules = [_rule_row(organization_id=org), _rule_row(organization_id=None)]
    app, _ = _build_app(fixtures=[rules], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/rules")
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_rules_super_admin_sees_unscoped():
    rules = [_rule_row()]
    app, conn = _build_app(
        fixtures=[rules],
        user={"id": 1, "role": "super_admin", "email": "s",
              "full_name": "S", "is_active": True},
        org_ids=None,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/rules")
    assert r.status_code == 200
    # No org-scoping clause when org_ids=None.
    op, sql, _ = conn.queries[0]
    assert "organization_id = ANY" not in sql


@pytest.mark.asyncio
async def test_list_rules_403_for_signer():
    app, _ = _build_app(
        user={"id": 9, "role": "signer", "email": "s",
              "full_name": "S", "is_active": True},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/rules")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_rule_404_when_missing():
    app, _ = _build_app(fixtures=[None])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/compliance/rules/{uuid.uuid4()}")
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Create
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_threshold_rule():
    org = uuid.uuid4()
    new_row = _rule_row(organization_id=org)
    # service.create_monitoring_rule: fetchrow INSERT RETURNING + execute audit_log
    app, conn = _build_app(fixtures=[new_row], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": str(org),
                "rule_name": "test",
                "rule_type": "threshold",
                "rule_config": {"threshold_usd": 5000},
                "action": "alert",
                "severity": "medium",
            },
        )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["rule_type"] == "threshold"
    # Audit-log INSERT happened.
    audit = [s for op, s, _ in conn.queries if "audit_log" in s and op == "execute"]
    assert audit


@pytest.mark.asyncio
async def test_create_velocity_rule_validates_count_and_window():
    org = uuid.uuid4()
    app, _ = _build_app(fixtures=[], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Missing window_hours.
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": str(org),
                "rule_name": "fast",
                "rule_type": "velocity",
                "rule_config": {"count": 10},
                "action": "hold",
                "severity": "high",
            },
        )
    assert r.status_code == 422
    assert "window_hours" in r.json()["detail"]


@pytest.mark.asyncio
async def test_create_blacklist_validates_addresses_list():
    org = uuid.uuid4()
    app, _ = _build_app(fixtures=[], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": str(org),
                "rule_name": "blocklist",
                "rule_type": "blacklist_address",
                "rule_config": {"addresses": []},   # empty
                "action": "block",
                "severity": "critical",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_threshold_requires_threshold_usd():
    org = uuid.uuid4()
    app, _ = _build_app(fixtures=[], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": str(org),
                "rule_name": "bad",
                "rule_type": "threshold",
                "rule_config": {},
                "action": "alert",
                "severity": "medium",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_global_rule_blocked_for_non_super_admin():
    """company_admin cannot create global rules (organization_id null)."""
    org = uuid.uuid4()
    app, _ = _build_app(fixtures=[], org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": None,
                "rule_name": "global",
                "rule_type": "threshold",
                "rule_config": {"threshold_usd": 100},
            },
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_rule_for_other_org_blocked():
    own = uuid.uuid4()
    other = uuid.uuid4()
    app, _ = _build_app(fixtures=[], org_ids=[own])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": str(other),
                "rule_name": "x",
                "rule_type": "threshold",
                "rule_config": {"threshold_usd": 100},
            },
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_create_global_rule_allowed_for_super_admin():
    new_row = _rule_row(organization_id=None)
    app, _ = _build_app(
        fixtures=[new_row],
        user={"id": 1, "role": "super_admin", "email": "s",
              "full_name": "S", "is_active": True},
        org_ids=None,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "organization_id": None,
                "rule_name": "global threshold",
                "rule_type": "threshold",
                "rule_config": {"threshold_usd": 50000},
                "action": "alert",
                "severity": "high",
            },
        )
    assert r.status_code == 201
    assert r.json()["organization_id"] is None


# ────────────────────────────────────────────────────────────────────
# Update / delete
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_rule_partial_update():
    org = uuid.uuid4()
    rid = uuid.uuid4()
    pre = _rule_row(id=rid, organization_id=org, is_active=True)
    after = _rule_row(id=rid, organization_id=org, is_active=False)
    # Route flow: get_monitoring_rule (fetchrow) → update_monitoring_rule
    # (FOR UPDATE fetchrow → UPDATE fetchrow → audit_log execute).
    fixtures = [pre, pre, after]
    app, conn = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.patch(
            f"/api/v1/compliance/rules/{rid}",
            json={"is_active": False},
        )
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_patch_rule_revalidates_config_on_change():
    org = uuid.uuid4()
    rid = uuid.uuid4()
    pre = _rule_row(id=rid, organization_id=org, rule_type="threshold")
    fixtures = [pre]   # only the get_monitoring_rule lookup before validation fails
    app, _ = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.patch(
            f"/api/v1/compliance/rules/{rid}",
            json={"rule_config": {}},   # missing threshold
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_patch_global_rule_blocked_for_company_admin():
    rid = uuid.uuid4()
    pre = _rule_row(id=rid, organization_id=None)
    app, _ = _build_app(fixtures=[pre], org_ids=[uuid.uuid4()])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.patch(
            f"/api/v1/compliance/rules/{rid}",
            json={"is_active": False},
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_rule_204_writes_audit():
    org = uuid.uuid4()
    rid = uuid.uuid4()
    pre = _rule_row(id=rid, organization_id=org)
    fixtures = [pre, pre]   # get_monitoring_rule + FOR UPDATE inside delete
    app, conn = _build_app(fixtures=fixtures, org_ids=[org])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.delete(f"/api/v1/compliance/rules/{rid}")
    assert r.status_code == 204
    # audit_log INSERT happened.
    audit = [s for op, s, _ in conn.queries if "audit_log" in s and op == "execute"]
    assert audit


@pytest.mark.asyncio
async def test_delete_rule_404_when_missing():
    app, _ = _build_app(fixtures=[None])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.delete(f"/api/v1/compliance/rules/{uuid.uuid4()}")
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────
# Auditor read-only
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auditor_can_list_rules():
    org = uuid.uuid4()
    app, _ = _build_app(
        fixtures=[[]],
        user={"id": 9, "role": "company_auditor", "email": "a",
              "full_name": "Auditor", "is_active": True},
        org_ids=[org],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/compliance/rules")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_auditor_cannot_create_rule():
    app, _ = _build_app(
        user={"id": 9, "role": "company_auditor", "email": "a",
              "full_name": "Auditor", "is_active": True},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(
            "/api/v1/compliance/rules",
            json={
                "rule_name": "x", "rule_type": "threshold",
                "rule_config": {"threshold_usd": 1},
            },
        )
    assert r.status_code == 403
