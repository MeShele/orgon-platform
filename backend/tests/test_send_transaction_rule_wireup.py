"""Wire-up tests for AML rule engine in TransactionService.send_transaction
(Wave 23, Story 2.8).

We mock both the Safina client and the ComplianceService — the goal is
to verify the wire-up logic, not the rule-engine correctness (covered
in `test_rule_engine.py`) or Safina API (covered elsewhere).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest

from backend.safina.models import SendTransactionRequest
from backend.services.transaction_service import (
    TransactionBlockedError,
    TransactionService,
)


# ────────────────────────────────────────────────────────────────────
# Test doubles
# ────────────────────────────────────────────────────────────────────


class _FakeAsyncDB:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []

    async def execute(self, sql: str, params=None):
        self.calls.append((sql, tuple(params) if params else ()))
        return "OK"


class _FakeSafinaClient:
    """Returns a deterministic tx_unid; records calls."""

    def __init__(self):
        self.send_calls: list[dict] = []
        self.next_unid = "fake_unid_001"

    @property
    def is_stub(self) -> bool:
        return False

    async def send_transaction(self, **kwargs):
        self.send_calls.append(kwargs)
        return self.next_unid


class _FakeCompliance:
    """Records rule-evaluation calls and returns a scripted verdict."""

    def __init__(self, verdict: dict | None = None):
        self.calls: list[dict] = []
        self._verdict = verdict or {"triggered": [], "verdict": "allow"}

    async def evaluate_transaction_rules(self, *, org_id, tx):
        self.calls.append({"org_id": org_id, "tx": tx})
        return self._verdict


def _make_service(verdict: dict | None = None):
    db = _FakeAsyncDB()
    client = _FakeSafinaClient()
    compliance = _FakeCompliance(verdict=verdict) if verdict is not None else None
    svc = TransactionService(client, db, compliance=compliance)
    # Bypass validate_transaction (which calls Safina) — assume valid.

    async def _no_validate(token, to_address, value, check_balance):
        return {"valid": True, "errors": [], "warnings": []}

    svc.validate_transaction = _no_validate
    return svc, db, client, compliance


def _request(value="1000", to="0xabc", token="1###w1") -> SendTransactionRequest:
    return SendTransactionRequest(
        token=token, to_address=to, value=value, info="", json_info=None,
    )


# ────────────────────────────────────────────────────────────────────
# No compliance service — backwards-compat
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_no_compliance_service_falls_through_to_pending():
    svc, db, client, compliance = _make_service(verdict=None)
    assert compliance is None
    out = await svc.send_transaction(_request(), validate=True)
    assert out == "fake_unid_001"
    # Status was 'pending' (default) — find the INSERT.
    inserts = [(s, p) for s, p in db.calls if "INSERT INTO transactions" in s]
    assert len(inserts) == 1
    # The status param is the 5th: (token, to, value, unid, status, ...).
    assert inserts[0][1][4] == "pending"


# ────────────────────────────────────────────────────────────────────
# Verdict allow → pending tx, Safina-call happens
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_allow_verdict_does_normal_pending_flow():
    org = str(uuid4())
    svc, db, client, compliance = _make_service(
        verdict={"triggered": [], "verdict": "allow"},
    )
    out = await svc.send_transaction(_request(), validate=True, org_id=org)
    assert out == "fake_unid_001"
    assert len(client.send_calls) == 1
    # Compliance got a UUID-typed org_id, not the bare string.
    assert isinstance(compliance.calls[0]["org_id"], UUID)
    inserts = [(s, p) for s, p in db.calls if "INSERT INTO transactions" in s]
    assert inserts[0][1][4] == "pending"


# ────────────────────────────────────────────────────────────────────
# Verdict hold → tx still goes to Safina but local status='on_hold'
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hold_verdict_calls_safina_and_persists_on_hold():
    org = str(uuid4())
    svc, db, client, compliance = _make_service(
        verdict={
            "triggered": [{
                "rule_id": str(uuid4()), "rule_name": "velocity",
                "rule_type": "velocity", "severity": "high",
                "action": "hold", "alert_id": str(uuid4()),
            }],
            "verdict": "hold",
        },
    )
    out = await svc.send_transaction(_request(), validate=True, org_id=org)
    assert out == "fake_unid_001"
    # Safina was called.
    assert len(client.send_calls) == 1
    # Local row inserted with on_hold status.
    inserts = [(s, p) for s, p in db.calls if "INSERT INTO transactions" in s]
    assert inserts[0][1][4] == "on_hold"


# ────────────────────────────────────────────────────────────────────
# Verdict block → no Safina call, raises TransactionBlockedError
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_block_verdict_raises_and_no_safina_call():
    org = str(uuid4())
    triggered_rules = [{
        "rule_id": str(uuid4()), "rule_name": "huge_threshold",
        "rule_type": "threshold", "severity": "critical",
        "action": "block", "alert_id": str(uuid4()),
    }]
    svc, db, client, compliance = _make_service(
        verdict={"triggered": triggered_rules, "verdict": "block"},
    )
    with pytest.raises(TransactionBlockedError) as excinfo:
        await svc.send_transaction(_request(), validate=True, org_id=org)
    # No Safina call.
    assert len(client.send_calls) == 0
    # No tx INSERT either — block means it never existed.
    inserts = [s for s, _ in db.calls if "INSERT INTO transactions" in s]
    assert inserts == []
    # Exception carries the triggered rules for the route to surface.
    assert excinfo.value.triggered == triggered_rules


# ────────────────────────────────────────────────────────────────────
# Bad org_id string is logged and treated as no-org (still calls compliance)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bad_org_id_string_falls_back_to_none():
    svc, db, client, compliance = _make_service(
        verdict={"triggered": [], "verdict": "allow"},
    )
    out = await svc.send_transaction(
        _request(), validate=True, org_id="not-a-uuid",
    )
    assert out == "fake_unid_001"
    # Compliance got None for org_id (bad input → ignored, only globals apply).
    assert compliance.calls[0]["org_id"] is None


# ────────────────────────────────────────────────────────────────────
# Validate=False bypass still runs rule engine
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_false_still_runs_rule_engine():
    """An operator setting `validate=False` only skips the input/balance
    check — AML rules must still gate. Otherwise the bypass is a hole."""
    org = str(uuid4())
    svc, db, client, compliance = _make_service(
        verdict={
            "triggered": [{
                "rule_id": str(uuid4()), "rule_name": "blacklist",
                "rule_type": "blacklist_address", "severity": "critical",
                "action": "block", "alert_id": None,
            }],
            "verdict": "block",
        },
    )
    with pytest.raises(TransactionBlockedError):
        await svc.send_transaction(_request(), validate=False, org_id=org)
    assert len(client.send_calls) == 0


# ────────────────────────────────────────────────────────────────────
# Compliance receives the converted Safina value, not the raw input
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compliance_sees_converted_value():
    """The Safina converter swaps `.` → `,` before send; rule engine
    must see the same bytes that hit the chain (so threshold rules
    written in Safina-format match)."""
    org = str(uuid4())
    svc, db, client, compliance = _make_service(
        verdict={"triggered": [], "verdict": "allow"},
    )
    out = await svc.send_transaction(
        _request(value="1.5"), validate=True, org_id=org,
    )
    assert out == "fake_unid_001"
    seen_value = compliance.calls[0]["tx"]["value"]
    # Period was replaced by comma — that's what Safina actually got.
    assert seen_value == "1,5"


# ────────────────────────────────────────────────────────────────────
# Multiple triggered rules — verdict still controls the flow
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_multiple_triggered_rules_block_when_any_is_block():
    org = str(uuid4())
    svc, db, client, compliance = _make_service(
        verdict={
            "triggered": [
                {"rule_name": "alert_only", "action": "alert", "severity": "low",
                 "rule_id": str(uuid4()), "rule_type": "threshold", "alert_id": None},
                {"rule_name": "block_one", "action": "block", "severity": "critical",
                 "rule_id": str(uuid4()), "rule_type": "blacklist_address",
                 "alert_id": None},
            ],
            "verdict": "block",
        },
    )
    with pytest.raises(TransactionBlockedError) as excinfo:
        await svc.send_transaction(_request(), validate=True, org_id=org)
    assert len(excinfo.value.triggered) == 2
    assert client.send_calls == []
