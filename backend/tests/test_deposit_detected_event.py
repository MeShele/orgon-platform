"""`wallet.deposit.detected` payload contract pinning.

We exercise `_persist_deposit` end-to-end with a fake pool: it must
INSERT into `deposits`, return True on a fresh insert (False on ON
CONFLICT replay), and emit `wallet.deposit.detected` with a payload
shape that matches the public contract documented in `WEBHOOKS.md`.

The `block_timestamp` field in particular was historically emitted
but missing from the public doc — these tests lock it in so the
divergence can't re-appear.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from backend.services import deposit_watcher as dw
from backend.services.deposit_sources import DepositEvent


class _FakeConn:
    def __init__(self, fetchrow_result: Any = None):
        self._fetchrow_result = fetchrow_result
        self.queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", (query, params)))
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


def _wallet() -> dict:
    return {
        "id": "11111111-2222-3333-4444-555555555555",
        "merchant_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "end_user_id": "99999999-8888-7777-6666-555555555555",
        "network": 5010,
        "addr": "TXYZdeadbeef",
    }


def _event(*, block_ts_ms: int = 1_716_000_000_000) -> DepositEvent:
    return DepositEvent(
        tx_hash="0xfeedbeefcafe",
        log_index=2,
        from_address="TSender123",
        asset="USDT",
        amount=Decimal("100.000000"),
        block_number=98765,
        block_ts_ms=block_ts_ms,
    )


@pytest.mark.asyncio
async def test_persist_deposit_emits_full_payload(monkeypatch):
    """On a successful INSERT, publish wallet.deposit.detected with
    every field documented in WEBHOOKS.md, including block_timestamp."""
    pool = _FakePool(_FakeConn({"id": "ddddd111-2222-3333-4444-555555555555"}))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({
            "merchant_id": merchant_id,
            "event_type": event_type,
            "payload": payload,
        })
        return "deliv-1"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    ok = await dw._persist_deposit(pool, w=_wallet(), ev=_event())
    assert ok is True

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event_type"] == "wallet.deposit.detected"
    assert ev["merchant_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    payload = ev["payload"]
    # Contract fields per WEBHOOKS.md — every key must be present
    assert payload["deposit_id"] == "ddddd111-2222-3333-4444-555555555555"
    assert payload["wallet_id"] == "11111111-2222-3333-4444-555555555555"
    assert payload["end_user_id"] == "99999999-8888-7777-6666-555555555555"
    assert payload["network"] == 5010
    assert payload["tx_hash"] == "0xfeedbeefcafe"
    assert payload["log_index"] == 2
    assert payload["from_address"] == "TSender123"
    assert payload["to_address"] == "TXYZdeadbeef"
    assert payload["asset"] == "USDT"
    # amount MUST be a decimal-string, not numeric — JSON-safe across SDK languages
    assert payload["amount"] == "100.000000"
    assert isinstance(payload["amount"], str)
    assert payload["confirmations"] == 0
    assert payload["block_number"] == 98765
    # block_timestamp MUST be ISO8601 UTC, NOT raw ms — this was the
    # gap that prompted the Wave 30 doc audit
    assert payload["block_timestamp"].endswith("+00:00")
    assert "T" in payload["block_timestamp"]


@pytest.mark.asyncio
async def test_persist_deposit_emits_null_block_timestamp_when_ts_missing(monkeypatch):
    """Chains that don't surface block ts produce null block_timestamp."""
    pool = _FakePool(_FakeConn({"id": "ddddd111-2222-3333-4444-555555555555"}))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload)

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    await dw._persist_deposit(pool, w=_wallet(), ev=_event(block_ts_ms=0))
    assert captured[0]["block_timestamp"] is None


@pytest.mark.asyncio
async def test_persist_deposit_treasury_wallet_emits_null_end_user_id(monkeypatch):
    """end_user_id is null for treasury / fee / hot / cold wallets."""
    pool = _FakePool(_FakeConn({"id": "ddddd111-2222-3333-4444-555555555555"}))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload)

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    treasury_wallet = _wallet()
    treasury_wallet["end_user_id"] = None
    await dw._persist_deposit(pool, w=treasury_wallet, ev=_event())
    assert captured[0]["end_user_id"] is None


@pytest.mark.asyncio
async def test_persist_deposit_skip_on_conflict_no_publish(monkeypatch):
    """ON CONFLICT (network, tx_hash, log_index) DO NOTHING ⇒ returns
    None from RETURNING. No webhook fires — replays must not re-emit."""
    pool = _FakePool(_FakeConn(None))  # fetchrow returns None on conflict
    captured: list = []

    async def fake_publish(*a, **kw):
        captured.append(kw["event_type"])

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    ok = await dw._persist_deposit(pool, w=_wallet(), ev=_event())
    assert ok is False
    assert captured == [], "duplicate detection (ON CONFLICT) MUST NOT re-fire deposit.detected"


@pytest.mark.asyncio
async def test_persist_deposit_publish_failure_is_non_fatal(monkeypatch):
    """A webhook queue hiccup must NOT break deposit recording itself.
    The deposit row landed; logging the warning is sufficient."""
    pool = _FakePool(_FakeConn({"id": "ddddd111-2222-3333-4444-555555555555"}))

    async def boom(*a, **kw):
        raise RuntimeError("webhook queue down")

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", boom
    )

    ok = await dw._persist_deposit(pool, w=_wallet(), ev=_event())
    assert ok is True  # deposit still recorded
