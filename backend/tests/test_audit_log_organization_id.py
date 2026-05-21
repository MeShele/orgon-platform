"""TD-1 Phase A — verify `audit_log.organization_id` is populated by
new INSERT paths (AuditService.log_action + platform-admin) and that
type coercion is forgiving (UUID, str, garbage → None).

These tests use an in-memory fake to avoid spinning up Postgres. We
inspect the SQL that asyncpg would see and the bound parameters,
which is enough to prove the column is being written.

What we DO test:
* `log_action` SQL writes the `organization_id` column.
* UUID object is bound through unchanged.
* Hex/uuid-string is parsed to UUID.
* Garbage string / wrong type coerces to None (audit row still lands).
* AML helper `_write_audit` includes the column in its SQL too.
* `_write_rule_audit` likewise.

What we DON'T test here (lives in test_aml_alerts.py / integration):
* End-to-end RLS / read-side filtering (Phase B work).
* Backfill of old NULL rows (Phase B).
"""

from __future__ import annotations

import uuid
from typing import Any, List, Tuple
from unittest.mock import AsyncMock

import pytest

from backend.services.audit_service import AuditService


# ────────────────────────────────────────────────────────────────────
# Tiny fake — captures all conn.execute / fetchval calls.
# ────────────────────────────────────────────────────────────────────


class _Connection:
    def __init__(self, fetchval_return: Any = 1):
        self.calls: List[Tuple[str, str, Tuple[Any, ...]]] = []
        self._fetchval_return = fetchval_return

    async def fetchval(self, sql: str, *args: Any) -> Any:
        self.calls.append(("fetchval", sql, args))
        return self._fetchval_return

    async def execute(self, sql: str, *args: Any) -> Any:
        self.calls.append(("execute", sql, args))
        return None


class _Pool:
    """Mimics `asyncpg.Pool` enough for AuditService to acquire+use."""

    def __init__(self, conn: _Connection):
        self.conn = conn

    def acquire(self):
        return _AcquireCM(self.conn)


class _AcquireCM:
    def __init__(self, conn: _Connection):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, *exc):
        return False


# ────────────────────────────────────────────────────────────────────
# AuditService.log_action — INSERT must include organization_id column
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_log_action_writes_organization_id_column() -> None:
    conn = _Connection(fetchval_return=42)
    service = AuditService(db_pool=_Pool(conn))
    org = uuid.uuid4()
    await service.log_action(
        action="aml.alert.claim",
        resource_type="aml_alert",
        resource_id=str(uuid.uuid4()),
        organization_id=org,
    )
    assert len(conn.calls) == 1
    op, sql, args = conn.calls[0]
    assert op == "fetchval"
    # SQL must include the new column. Whitespace-insensitive substring
    # match so future formatting tweaks don't break the test.
    assert "organization_id" in sql
    # 8 bound params now (was 7 before TD-1): the new col is the last.
    assert len(args) == 8
    assert args[-1] == org


@pytest.mark.asyncio
async def test_log_action_parses_string_uuid() -> None:
    conn = _Connection()
    service = AuditService(db_pool=_Pool(conn))
    org_str = str(uuid.uuid4())
    await service.log_action(action="x", organization_id=org_str)
    _, _, args = conn.calls[0]
    assert isinstance(args[-1], uuid.UUID)
    assert str(args[-1]) == org_str


@pytest.mark.asyncio
async def test_log_action_garbage_org_id_coerces_to_none() -> None:
    """A stale caller passes a plain int / non-uuid string → audit row
    still lands, organization_id silently NULL. Sign correctness
    over audit completeness (same rule as TD-2)."""
    conn = _Connection()
    service = AuditService(db_pool=_Pool(conn))
    await service.log_action(action="x", organization_id="not-a-uuid")
    _, _, args = conn.calls[0]
    assert args[-1] is None

    conn2 = _Connection()
    service2 = AuditService(db_pool=_Pool(conn2))
    await service2.log_action(action="x", organization_id=12345)  # int
    _, _, args2 = conn2.calls[0]
    assert args2[-1] is None


@pytest.mark.asyncio
async def test_log_action_missing_org_id_is_none() -> None:
    """Backwards-compat: pre-TD-1 callers that omit organization_id
    still produce a valid INSERT — the new column lands NULL."""
    conn = _Connection()
    service = AuditService(db_pool=_Pool(conn))
    await service.log_action(action="x")
    _, _, args = conn.calls[0]
    assert args[-1] is None


# ────────────────────────────────────────────────────────────────────
# Compliance _write_audit / _write_rule_audit — SQL must carry the col
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compliance_write_audit_includes_organization_id() -> None:
    from backend.services.compliance_service import ComplianceService

    # ComplianceService.__init__ wants a pool; we construct minimal one.
    svc = ComplianceService(pool=_Pool(_Connection()))

    conn = _Connection()
    org = uuid.uuid4()
    await svc._write_audit(
        conn,
        user_id=1,
        action="aml.alert.claim",
        alert_id=uuid.uuid4(),
        details={"k": "v"},
        organization_id=org,
    )
    op, sql, args = conn.calls[0]
    assert "organization_id" in sql
    assert args[-1] == org


@pytest.mark.asyncio
async def test_compliance_write_rule_audit_includes_organization_id() -> None:
    from backend.services.compliance_service import ComplianceService

    svc = ComplianceService(pool=_Pool(_Connection()))
    conn = _Connection()
    org = uuid.uuid4()
    await svc._write_rule_audit(
        conn,
        actor_user_id=7,
        action="rule.create",
        rule_id=uuid.uuid4(),
        details={"after": {}},
        organization_id=org,
    )
    op, sql, args = conn.calls[0]
    assert "organization_id" in sql
    assert args[-1] == org


@pytest.mark.asyncio
async def test_compliance_write_audit_accepts_none_for_global_rules() -> None:
    """Global monitoring rules have organization_id IS NULL. The helper
    must not raise on that — NULL is the right semantic."""
    from backend.services.compliance_service import ComplianceService

    svc = ComplianceService(pool=_Pool(_Connection()))
    conn = _Connection()
    await svc._write_rule_audit(
        conn,
        actor_user_id=None,
        action="rule.delete",
        rule_id=uuid.uuid4(),
        details={"before": {}},
        organization_id=None,
    )
    _, sql, args = conn.calls[0]
    assert "organization_id" in sql
    assert args[-1] is None
