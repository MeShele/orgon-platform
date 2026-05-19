"""`policy.triggered` payload contract pinning.

ORGON's in-house rule engine (E-07) emits `policy.triggered` whenever
a `transaction_monitoring_rule` matches and the rule's action is NOT
informational `alert`. Pure alerts stay in the AML alerts queue;
only `hold` / `block` / `request_approval` rise to the wire.

This test locks the payload shape from
`compliance_service._publish_policy_triggered` so a future refactor
can't silently change what merchants receive.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest

from backend.services.compliance_service import ComplianceService


class _FakeConn:
    def __init__(self, fetchrow_result: Any = None):
        self._fetchrow_result = fetchrow_result
        self.queries: list = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", query, params))
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


def _rule() -> dict:
    return {
        "id": UUID("11111111-2222-3333-4444-555555555555"),
        "rule_name": "high-value-send",
        "rule_type": "threshold",
        "severity": "high",
    }


def _tx() -> dict:
    return {
        "transaction_id": UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        "to_address": "T_outbound_42",
        "value": "50000.000000",
        "token": "USDT",
        "network": 5010,
        "wallet_id": UUID("99999999-8888-7777-6666-555555555555"),
    }


@pytest.mark.asyncio
async def test_policy_triggered_payload_for_block_action(monkeypatch):
    """`block` action emits with full payload shape, alert_id present."""
    pool = _FakePool(_FakeConn({"id": "deliv-uuid"}))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({"event_type": event_type, "payload": payload, "merchant_id": merchant_id})
        return "deliv-1"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    svc = ComplianceService(pool)
    alert_id = UUID("cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa")
    await svc._publish_policy_triggered(
        merchant_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        rule=_rule(),
        action="block",
        alert_id=alert_id,
        tx=_tx(),
    )

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event_type"] == "policy.triggered"
    assert ev["merchant_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    p = ev["payload"]
    assert p["rule_id"] == "11111111-2222-3333-4444-555555555555"
    assert p["rule_name"] == "high-value-send"
    assert p["rule_type"] == "threshold"
    assert p["severity"] == "high"
    assert p["action"] == "block"
    assert p["alert_id"] == "cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa"

    tx = p["tx"]
    assert tx["transaction_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert tx["to_address"] == "T_outbound_42"
    assert tx["value"] == "50000.000000"
    assert isinstance(tx["value"], str), "value MUST be string for JSON-safe decimal"
    assert tx["token"] == "USDT"
    assert tx["network"] == 5010
    assert tx["wallet_id"] == "99999999-8888-7777-6666-555555555555"


@pytest.mark.asyncio
async def test_policy_triggered_alert_id_null_when_not_provided(monkeypatch):
    """Alert insert may race the emit — payload tolerates a null alert_id."""
    pool = _FakePool(_FakeConn(None))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload)

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    await ComplianceService(pool)._publish_policy_triggered(
        merchant_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        rule=_rule(),
        action="hold",
        alert_id=None,
        tx=_tx(),
    )
    assert captured[0]["alert_id"] is None
    assert captured[0]["action"] == "hold"


@pytest.mark.asyncio
async def test_policy_triggered_request_approval_action(monkeypatch):
    """The `request_approval` action is a real wire value — not synthesized."""
    pool = _FakePool(_FakeConn(None))
    captured: list[str] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload["action"])

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    await ComplianceService(pool)._publish_policy_triggered(
        merchant_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        rule=_rule(),
        action="request_approval",
        alert_id=None,
        tx=_tx(),
    )
    assert captured == ["request_approval"]


@pytest.mark.asyncio
async def test_policy_triggered_publish_failure_is_non_fatal(monkeypatch):
    """Webhook queue hiccup must not break rule evaluation upstream."""
    pool = _FakePool(_FakeConn(None))

    async def boom(*a, **kw):
        raise RuntimeError("queue down")

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", boom
    )

    # Must not raise — _publish_policy_triggered wraps in try/except
    await ComplianceService(pool)._publish_policy_triggered(
        merchant_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        rule=_rule(),
        action="block",
        alert_id=None,
        tx=_tx(),
    )
