"""`/v1/compliance/rules` contract — single pane of glass.

The HMAC-route mirrors the JWT compliance-rule CRUD with two
deliberate differences:

1. Scope is **only** the caller's merchant. Global rules
   (`organization_id IS NULL`) are NEVER surfaced — even via direct
   GET by id. An external orchestrator should not be able to read
   platform-wide policy.
2. Rules created here are tagged `source='api'` for UI badging and
   audit clarity.

Tests target the service-layer touch-points; FastAPI route plumbing
is exercised separately by the boot-smoke + manual smoke harness.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest


MERCHANT_A = UUID("11111111-2222-3333-4444-555555555555")


class _FakeConn:
    """Programmable mock conn — pops queued results in order."""

    def __init__(
        self,
        fetchrow_results: list[Any] | None = None,
        fetch_results: list[Any] | None = None,
        execute_results: list[Any] | None = None,
    ):
        self._fr = list(fetchrow_results or [])
        self._fa = list(fetch_results or [])
        self._ex = list(execute_results or [])
        self.queries: list[tuple[str, str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", query, params))
        return self._fr.pop(0) if self._fr else None

    async def fetch(self, query, *params):
        self.queries.append(("fetch", query, params))
        return self._fa.pop(0) if self._fa else []

    async def execute(self, query, *params):
        self.queries.append(("execute", query, params))
        return self._ex.pop(0) if self._ex else "OK"

    def transaction(self):
        outer = self

        class _Tx:
            async def __aenter__(self_inner):
                return outer

            async def __aexit__(self_inner, *exc):
                return None

        return _Tx()


class _FakeAcq:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return None


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _FakeAcq(self._conn)


def _rule_row(
    *,
    rid: UUID | None = None,
    org_id: UUID | None = MERCHANT_A,
    rule_name: str = "high-value",
    rule_type: str = "threshold",
    rule_config: dict | None = None,
    action: str = "alert",
    severity: str = "medium",
    is_active: bool = True,
    source: str = "ui",
    created_by: int | None = None,
):
    return {
        "id": rid or uuid4(),
        "organization_id": org_id,
        "rule_name": rule_name,
        "rule_type": rule_type,
        "description": None,
        "rule_config": rule_config or {"threshold_usd": 50000},
        "action": action,
        "severity": severity,
        "is_active": is_active,
        "source": source,
        "created_at": datetime(2026, 5, 19, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 5, 19, tzinfo=timezone.utc),
        "created_by": created_by,
    }


# ─────────────── create_monitoring_rule writes source ───────────────


@pytest.mark.asyncio
async def test_create_writes_source_api_with_null_actor():
    """Service must accept actor_user_id=None and source='api' from
    the HMAC route — both are new in Wave 34."""
    from backend.services.compliance_service import ComplianceService

    new_id = uuid4()
    inserted = _rule_row(rid=new_id, source="api")
    # fetchrow #1 = INSERT RETURNING *, #2 = audit_log execute is via
    # execute(), not fetchrow.
    conn = _FakeConn(fetchrow_results=[inserted])
    pool = _FakePool(conn)
    svc = ComplianceService(pool)

    row = await svc.create_monitoring_rule(
        organization_id=MERCHANT_A,
        rule_name="high-value",
        rule_type="threshold",
        description=None,
        rule_config={"threshold_usd": 50000},
        action="alert",
        severity="medium",
        is_active=True,
        actor_user_id=None,
        source="api",
    )
    assert row["source"] == "api"
    assert row["id"] == new_id

    # The INSERT query must include the `source` column + bind it as $10
    insert_calls = [q for q in conn.queries if q[0] == "fetchrow" and "INSERT" in q[1]]
    assert len(insert_calls) == 1
    _, query, params = insert_calls[0]
    assert "source" in query.lower()
    # actor_user_id is param $9 (created_by), source is $10
    assert params[8] is None
    assert params[9] == "api"


@pytest.mark.asyncio
async def test_create_defaults_source_to_ui_when_omitted():
    """Existing JWT-route call sites must keep working unchanged —
    the `source` kwarg defaults to 'ui'."""
    from backend.services.compliance_service import ComplianceService

    inserted = _rule_row(source="ui", created_by=42)
    conn = _FakeConn(fetchrow_results=[inserted])
    svc = ComplianceService(_FakePool(conn))

    await svc.create_monitoring_rule(
        organization_id=MERCHANT_A,
        rule_name="x",
        rule_type="velocity",
        description=None,
        rule_config={"count": 5, "window_hours": 1},
        action="alert",
        severity="medium",
        is_active=True,
        actor_user_id=42,
    )

    _, _, params = [q for q in conn.queries if "INSERT" in q[1]][0]
    assert params[9] == "ui"
    assert params[8] == 42


# ─────────────── list/get scope behavior ───────────────


@pytest.mark.asyncio
async def test_list_with_include_global_false_excludes_platform_rules():
    """The /v1/* surface MUST pass include_global=False — otherwise
    an external orchestrator could see ORGON-team-level policy."""
    from backend.services.compliance_service import ComplianceService

    conn = _FakeConn(fetch_results=[[]])
    svc = ComplianceService(_FakePool(conn))

    await svc.list_monitoring_rules(org_ids=[MERCHANT_A], include_global=False)

    _, query, _ = conn.queries[0]
    # When include_global=False, the IS NULL branch must NOT be in the
    # WHERE clause.
    assert "organization_id = ANY" in query
    assert "organization_id IS NULL" not in query


@pytest.mark.asyncio
async def test_get_returns_none_for_other_merchant():
    """Cross-merchant rule_id lookup returns None — caller maps to 404
    (route does this; service stays generic)."""
    from backend.services.compliance_service import ComplianceService

    conn = _FakeConn(fetchrow_results=[None])
    svc = ComplianceService(_FakePool(conn))

    row = await svc.get_monitoring_rule(uuid4(), org_ids=[MERCHANT_A])
    assert row is None


# ─────────────── route-layer config validation ───────────────


def test_validate_threshold_requires_threshold_usd():
    from backend.api.routes_public_v1 import _validate_v1_rule_config
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        _validate_v1_rule_config("threshold", {})
    assert ei.value.status_code == 422
    assert "threshold_usd" in ei.value.detail


def test_validate_velocity_requires_positive_ints():
    from backend.api.routes_public_v1 import _validate_v1_rule_config
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        _validate_v1_rule_config("velocity", {"count": 0, "window_hours": 1})
    assert ei.value.status_code == 422


def test_validate_blacklist_requires_addresses_list():
    from backend.api.routes_public_v1 import _validate_v1_rule_config
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _validate_v1_rule_config("blacklist_address", {"addresses": []})

    with pytest.raises(HTTPException):
        _validate_v1_rule_config("blacklist_address", {"addresses": [1, 2]})

    # Happy path — list of strings passes
    _validate_v1_rule_config("blacklist_address", {"addresses": ["Taddr1", "Taddr2"]})


def test_validate_e07_types_accept_opaque_config():
    """E-07 extensions (velocity_amount_usd, recipient_whitelist,
    time_window, recipient_geo_block) currently accept any config
    shape — engine validates at evaluation time. Verify we don't
    accidentally hard-block them at the API layer."""
    from backend.api.routes_public_v1 import _validate_v1_rule_config

    # Should not raise for any of these
    for kind in (
        "velocity_amount_usd",
        "recipient_whitelist",
        "time_window",
        "recipient_geo_block",
    ):
        _validate_v1_rule_config(kind, {"anything": "goes"})
        _validate_v1_rule_config(kind, {})


# ─────────────── response-shaper ───────────────


def test_rule_to_public_shape():
    """The route returns `_rule_to_public` shape — pin the contract
    so it doesn't silently drift away from the docs."""
    from backend.api.routes_public_v1 import _rule_to_public

    rid = uuid4()
    out = _rule_to_public(_rule_row(rid=rid, source="api"))

    assert out == {
        "id": str(rid),
        "organization_id": str(MERCHANT_A),
        "rule_name": "high-value",
        "rule_type": "threshold",
        "description": None,
        "rule_config": {"threshold_usd": 50000},
        "action": "alert",
        "severity": "medium",
        "is_active": True,
        "source": "api",
        "created_at": "2026-05-19T00:00:00+00:00",
        "updated_at": "2026-05-19T00:00:00+00:00",
    }


def test_rule_to_public_strips_created_by():
    """`created_by` is an internal user_id and must NOT leak to the
    external orchestrator — they get no actionable info from it."""
    from backend.api.routes_public_v1 import _rule_to_public

    out = _rule_to_public(_rule_row(created_by=42))
    assert "created_by" not in out


def test_rule_to_public_defaults_source_to_ui_for_legacy_rows():
    """Rows created before migration 054 have NULL/missing source —
    we surface 'ui' as the safest default (it's what migration 054
    backfills via DEFAULT)."""
    from backend.api.routes_public_v1 import _rule_to_public

    row = _rule_row()
    row["source"] = None
    out = _rule_to_public(row)
    assert out["source"] == "ui"
