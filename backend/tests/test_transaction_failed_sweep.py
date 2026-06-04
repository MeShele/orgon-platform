"""`transaction.failed` timeout-based source-of-truth tests.

The sweep finds txs stuck in `status='signed'` without a `tx_hash`
beyond the timeout, atomically flips them to `'failed'` via
`UPDATE...RETURNING`, and emits `transaction.failed` per row.

These tests pin:
- SQL eligibility predicate (status / tx_hash / updated_at / org_id)
- Atomic UPDATE+SELECT shape so a single tick is at-most-once-per-row
- Payload contract for the emitted event
- env override for the timeout window
- No-op behavior when no rows match
- Per-row publish failure does NOT skip subsequent rows
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.services import transaction_failure_sweep as tfs


class _FakeConn:
    def __init__(self, fetch_rows: list | None = None):
        self._fetch_rows = fetch_rows or []
        self.queries: list[tuple[str, tuple]] = []

    async def fetch(self, query, *params):
        self.queries.append(("fetch", (query, params)))
        return list(self._fetch_rows)


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


def _row(*, id_="tx-1", unid="UNID-1", merchant_id="11111111-2222-3333-4444-555555555555"):
    return {
        "id": id_,
        "unid": unid,
        "merchant_id": merchant_id,
        "wallet_name": "treasury-1",
        "to_addr": "T_dest_xyz",
        "value": "100.5",
        "token": "USDT",
    }


@pytest.mark.asyncio
async def test_sweep_emits_failed_with_documented_payload(monkeypatch):
    pool = _FakePool(_FakeConn([_row()]))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({"merchant_id": merchant_id, "event_type": event_type, "payload": payload})
        return "deliv-1"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    stats = await tfs.run_tick(pool, timeout_hours=24)
    assert stats == {"candidates_swept": 1, "events_emitted": 1}

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event_type"] == "transaction.failed"
    assert ev["merchant_id"] == "11111111-2222-3333-4444-555555555555"

    p = ev["payload"]
    # Mirrors broadcasted/confirmed shape so SDK clients can reuse types
    assert p["tx_id"] == "UNID-1"  # public id (= unid), not internal row id
    assert p["tx_unid"] == "UNID-1"
    assert p["tx_hash"] is None
    assert p["wallet_name"] == "treasury-1"
    assert p["to_address"] == "T_dest_xyz"
    assert p["amount"] == "100.5"
    assert p["token"] == "USDT"
    assert p["reason"] == "timeout_no_broadcast"


@pytest.mark.asyncio
async def test_sweep_query_eligibility_predicate(monkeypatch):
    """SQL must filter on status / tx_hash / updated_at / org_id and lock rows."""
    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tfs.run_tick(pool, timeout_hours=24)

    assert len(conn.queries) == 1
    op, (query, params) = conn.queries[0]
    assert op == "fetch"
    # All four eligibility clauses present
    assert "status = 'signed'" in query
    assert "tx_hash IS NULL OR tx_hash = ''" in query
    assert "updated_at < now() -" in query
    assert "organization_id IS NOT NULL" in query
    # Atomic UPDATE+SELECT with row-level lock so two parallel ticks
    # never emit twice
    assert "UPDATE transactions" in query
    assert "FOR UPDATE SKIP LOCKED" in query
    assert "RETURNING" in query
    # Param: timeout passed as string-hours
    assert params[0] == "24"


@pytest.mark.asyncio
async def test_sweep_no_candidates_no_publish(monkeypatch):
    """Empty result must not even import webhook_publisher uselessly."""
    pool = _FakePool(_FakeConn([]))
    captured: list = []

    async def fake_publish(*a, **kw):
        captured.append(1)

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    stats = await tfs.run_tick(pool, timeout_hours=24)
    assert stats == {"candidates_swept": 0, "events_emitted": 0}
    assert captured == []


@pytest.mark.asyncio
async def test_sweep_publish_failure_does_not_stop_remaining_rows(monkeypatch):
    """If row 2's publish raises, rows 1 and 3 still emit. Stats reflect partial success."""
    rows = [
        _row(id_="tx-1", unid="U-1"),
        _row(id_="tx-2", unid="U-2"),
        _row(id_="tx-3", unid="U-3"),
    ]
    pool = _FakePool(_FakeConn(rows))
    emitted: list[str] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        if payload["tx_id"] == "U-2":
            raise RuntimeError("queue down")
        emitted.append(payload["tx_id"])

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    stats = await tfs.run_tick(pool, timeout_hours=24)
    assert stats == {"candidates_swept": 3, "events_emitted": 2}
    assert emitted == ["U-1", "U-3"]


@pytest.mark.asyncio
async def test_env_override_timeout_hours(monkeypatch):
    """`TX_FAILED_TIMEOUT_HOURS` env overrides the default 24h."""
    monkeypatch.setenv("TX_FAILED_TIMEOUT_HOURS", "72")

    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tfs.run_tick(pool)  # no explicit timeout_hours → reads env

    _, (_, params) = conn.queries[0]
    assert params[0] == "72"


@pytest.mark.asyncio
async def test_env_override_ignores_garbage(monkeypatch):
    """A malformed env value falls back to the default — don't crash."""
    monkeypatch.setenv("TX_FAILED_TIMEOUT_HOURS", "nope")

    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tfs.run_tick(pool)

    _, (_, params) = conn.queries[0]
    assert params[0] == "24"


@pytest.mark.asyncio
async def test_explicit_timeout_overrides_env(monkeypatch):
    """Programmatic call with explicit timeout_hours wins over env."""
    monkeypatch.setenv("TX_FAILED_TIMEOUT_HOURS", "72")

    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tfs.run_tick(pool, timeout_hours=6)

    _, (_, params) = conn.queries[0]
    assert params[0] == "6"
