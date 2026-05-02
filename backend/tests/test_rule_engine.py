"""Tests for the in-house transaction rule engine (Wave 23, Story 2.8).

Covers:
- threshold / velocity / blacklist_address rule types
- action enum (alert | hold | block) → verdict resolution
- strictest-action wins when multiple rules fire
- DB error → no-op verdict 'allow' (defense-in-depth, never blocks tx)
- legacy `check_transaction_against_rules` adapter still works
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from backend.services.compliance_service import ComplianceService


# ────────────────────────────────────────────────────────────────────
# Fake pool — same shape as test_aml_alerts.py but specialised for
# the queries this engine emits.
# ────────────────────────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, fetchrow_seq=None, fetch_seq=None):
        self.fetchrow_seq = list(fetchrow_seq or [])
        self.fetch_seq = list(fetch_seq or [])
        self.queries: list[tuple[str, str, tuple]] = []

    async def fetch(self, query, *params):
        self.queries.append(("fetch", query, params))
        if not self.fetch_seq:
            return []
        return self.fetch_seq.pop(0)

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", query, params))
        if not self.fetchrow_seq:
            return None
        return self.fetchrow_seq.pop(0)

    async def execute(self, query, *params):
        self.queries.append(("execute", query, params))


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        outer = self

        class _Ctx:
            async def __aenter__(_self):
                return outer._conn

            async def __aexit__(_self, *exc):
                return None

        return _Ctx()


def _rule_row(**kwargs):
    base = {
        "id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "rule_name": "test rule",
        "rule_type": "threshold",
        "rule_config": {"threshold_usd": 10000},
        "action": "alert",
        "severity": "medium",
    }
    base.update(kwargs)
    return base


# ────────────────────────────────────────────────────────────────────
# Threshold rule
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_threshold_fires_above_limit():
    org = uuid.uuid4()
    rules = [_rule_row(organization_id=org, rule_config={"threshold_usd": 10000})]
    # First fetch → rules. Then fetchrow → INSERT alert RETURNING id.
    conn = _FakeConn(
        fetch_seq=[rules],
        fetchrow_seq=[{"id": uuid.uuid4()}],
    )
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "12000", "to_address": "0xabc"},
    )
    assert result["verdict"] == "allow"  # action=alert
    assert len(result["triggered"]) == 1
    assert result["triggered"][0]["rule_type"] == "threshold"


@pytest.mark.asyncio
async def test_threshold_does_not_fire_below_limit():
    org = uuid.uuid4()
    rules = [_rule_row(organization_id=org, rule_config={"threshold_usd": 10000})]
    conn = _FakeConn(fetch_seq=[rules])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "5000", "to_address": "0xabc"},
    )
    assert result["verdict"] == "allow"
    assert result["triggered"] == []


@pytest.mark.asyncio
async def test_threshold_with_block_action_blocks():
    org = uuid.uuid4()
    rules = [_rule_row(
        organization_id=org,
        rule_config={"threshold_usd": 10000},
        action="block",
        severity="critical",
    )]
    conn = _FakeConn(fetch_seq=[rules], fetchrow_seq=[{"id": uuid.uuid4()}])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "100000", "to_address": "0xabc"},
    )
    assert result["verdict"] == "block"
    assert result["triggered"][0]["action"] == "block"


# ────────────────────────────────────────────────────────────────────
# Blacklist rule
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_blacklist_fires_on_listed_address():
    org = uuid.uuid4()
    rules = [_rule_row(
        organization_id=org,
        rule_type="blacklist_address",
        rule_config={"addresses": ["0xBAD1", "0xBAD2"]},
        action="block",
    )]
    conn = _FakeConn(fetch_seq=[rules], fetchrow_seq=[{"id": uuid.uuid4()}])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "1", "to_address": "0xbad1"},  # case-insensitive
    )
    assert result["verdict"] == "block"


@pytest.mark.asyncio
async def test_blacklist_misses_when_not_listed():
    org = uuid.uuid4()
    rules = [_rule_row(
        organization_id=org,
        rule_type="blacklist_address",
        rule_config={"addresses": ["0xBAD1"]},
    )]
    conn = _FakeConn(fetch_seq=[rules])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "1", "to_address": "0xclean"},
    )
    assert result["verdict"] == "allow"


# ────────────────────────────────────────────────────────────────────
# Velocity rule
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_velocity_fires_when_count_exceeded():
    org = uuid.uuid4()
    rules = [_rule_row(
        organization_id=org,
        rule_type="velocity",
        rule_config={"count": 5, "window_hours": 1},
        action="hold",
        severity="high",
    )]
    # fetch → rules; fetchrow → COUNT(*) row; fetchrow → alert RETURNING id
    conn = _FakeConn(
        fetch_seq=[rules],
        fetchrow_seq=[{"n": 7}, {"id": uuid.uuid4()}],
    )
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "1", "to_address": "0xabc"},
    )
    assert result["verdict"] == "hold"
    assert result["triggered"][0]["rule_type"] == "velocity"


@pytest.mark.asyncio
async def test_velocity_does_not_fire_below_count():
    org = uuid.uuid4()
    rules = [_rule_row(
        organization_id=org,
        rule_type="velocity",
        rule_config={"count": 5, "window_hours": 1},
    )]
    conn = _FakeConn(fetch_seq=[rules], fetchrow_seq=[{"n": 2}])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "1", "to_address": "0xabc"},
    )
    assert result["verdict"] == "allow"


@pytest.mark.asyncio
async def test_velocity_skips_for_no_org():
    """Velocity is meaningless without an org-scope (would count all rows)."""
    rules = [_rule_row(
        organization_id=None,
        rule_type="velocity",
        rule_config={"count": 5, "window_hours": 1},
    )]
    conn = _FakeConn(fetch_seq=[rules])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=None, tx={"value": "1", "to_address": "0xabc"},
    )
    assert result["verdict"] == "allow"


# ────────────────────────────────────────────────────────────────────
# Multiple rules — strictest wins
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_strictest_action_wins_block_over_hold_over_alert():
    org = uuid.uuid4()
    rules = [
        _rule_row(organization_id=org, rule_config={"threshold_usd": 100}, action="alert"),
        _rule_row(organization_id=org, rule_config={"threshold_usd": 100}, action="hold"),
        _rule_row(organization_id=org, rule_config={"threshold_usd": 100}, action="block"),
    ]
    # 3 rules fire → 3 alert inserts.
    conn = _FakeConn(
        fetch_seq=[rules],
        fetchrow_seq=[
            {"id": uuid.uuid4()}, {"id": uuid.uuid4()}, {"id": uuid.uuid4()},
        ],
    )
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "500", "to_address": "0xabc"},
    )
    assert result["verdict"] == "block"
    assert len(result["triggered"]) == 3


@pytest.mark.asyncio
async def test_hold_when_no_block_present():
    org = uuid.uuid4()
    rules = [
        _rule_row(organization_id=org, rule_config={"threshold_usd": 100}, action="hold"),
        _rule_row(organization_id=org, rule_config={"threshold_usd": 100}, action="alert"),
    ]
    conn = _FakeConn(
        fetch_seq=[rules],
        fetchrow_seq=[{"id": uuid.uuid4()}, {"id": uuid.uuid4()}],
    )
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "500", "to_address": "0xabc"},
    )
    assert result["verdict"] == "hold"


# ────────────────────────────────────────────────────────────────────
# Defense in depth — DB failure does not block tx
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_db_error_during_fetch_returns_allow():
    """If the rules-table fetch raises, we treat it as allow + log."""
    class _BrokenConn:
        async def fetch(self, *a, **k):
            raise RuntimeError("boom")
        def transaction(self):
            class _T:
                async def __aenter__(s): return s
                async def __aexit__(s, *a): return None
            return _T()

    class _BrokenPool:
        def acquire(self):
            class _Ctx:
                async def __aenter__(s): return _BrokenConn()
                async def __aexit__(s, *a): return None
            return _Ctx()

    svc = ComplianceService(_BrokenPool())
    result = await svc.evaluate_transaction_rules(
        org_id=uuid.uuid4(), tx={"value": "1", "to_address": "0xabc"},
    )
    assert result == {"triggered": [], "verdict": "allow"}


# ────────────────────────────────────────────────────────────────────
# Pure-function checkers
# ────────────────────────────────────────────────────────────────────


def test_check_threshold_pure():
    assert ComplianceService._check_threshold(
        {"threshold_usd": 100}, {"value": "150"},
    ) is True
    assert ComplianceService._check_threshold(
        {"threshold_usd": 100}, {"value": "50"},
    ) is False
    # No threshold configured → never fires.
    assert ComplianceService._check_threshold({}, {"value": "1000000"}) is False
    # Bad value type → never fires.
    assert ComplianceService._check_threshold(
        {"threshold_usd": 100}, {"value": "not_a_number"},
    ) is False


def test_check_blacklist_case_insensitive():
    cfg = {"addresses": ["0xABC123"]}
    assert ComplianceService._check_blacklist(cfg, {"to_address": "0xabc123"}) is True
    assert ComplianceService._check_blacklist(cfg, {"to_address": "0xdef456"}) is False
    # Empty list never fires.
    assert ComplianceService._check_blacklist({}, {"to_address": "0xabc"}) is False


# ────────────────────────────────────────────────────────────────────
# Unknown rule type — graceful skip
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_rule_type_no_fire():
    org = uuid.uuid4()
    rules = [_rule_row(organization_id=org, rule_type="ml_xgboost_v9", rule_config={})]
    conn = _FakeConn(fetch_seq=[rules])
    svc = ComplianceService(_FakePool(conn))
    result = await svc.evaluate_transaction_rules(
        org_id=org, tx={"value": "1000000000", "to_address": "0xabc"},
    )
    assert result["verdict"] == "allow"
    assert result["triggered"] == []


# ────────────────────────────────────────────────────────────────────
# Backwards-compat adapter
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_check_transaction_against_rules_returns_list():
    org = uuid.uuid4()
    rules = [_rule_row(organization_id=org, rule_config={"threshold_usd": 100})]
    conn = _FakeConn(fetch_seq=[rules], fetchrow_seq=[{"id": uuid.uuid4()}])
    svc = ComplianceService(_FakePool(conn))
    out = await svc.check_transaction_against_rules(
        org, {"value": "500", "to_address": "0xabc"},
    )
    assert isinstance(out, list)
    assert len(out) == 1
