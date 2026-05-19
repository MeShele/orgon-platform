"""`transaction.uncertain` 10-min preview signal.

Pins:
- SQL eligibility predicate (status / tx_hash / updated_at / org_id /
  uncertain_emitted_at IS NULL)
- Atomic UPDATE+SELECT shape — single tick, at-most-once per row
- Payload contract (tx_id, tx_unid, tx_hash:null, wallet_name,
  to_address, amount, token, stuck_seconds, next_check_in)
- env override for timeout window
- No-op behavior when no rows match
- Per-row publish failure does NOT skip remaining rows
- Does NOT mutate status column (uncertain is informational; the
  24h failure sweep is the one that flips to 'failed')
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from backend.services import transaction_uncertain_sweep as tus


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


def _row(
    *,
    id_="tx-1",
    unid="UNID-1",
    merchant_id="11111111-2222-3333-4444-555555555555",
    stuck_for: timedelta = timedelta(minutes=12),
):
    """Build a returned-row dict. `stuck_for` controls how long ago
    `updated_at` was, used to verify stuck_seconds payload field."""
    return {
        "id": id_,
        "unid": unid,
        "merchant_id": merchant_id,
        "wallet_name": "treasury-1",
        "to_addr": "T_dest_xyz",
        "value": "100.5",
        "token": "USDT",
        "updated_at": datetime.now(timezone.utc) - stuck_for,
    }


# ──────────────── SQL eligibility ────────────────


@pytest.mark.asyncio
async def test_query_predicate_includes_all_required_clauses():
    """Eligibility MUST include all five clauses; missing any one of
    them is a regression. Verified by SQL inspection."""
    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tus.run_tick(pool, timeout_minutes=10)

    assert len(conn.queries) == 1
    op, (query, params) = conn.queries[0]
    assert op == "fetch"
    assert "status = 'signed'" in query
    assert "tx_hash IS NULL OR tx_hash = ''" in query
    assert "updated_at < now() -" in query
    assert "organization_id IS NOT NULL" in query
    assert "uncertain_emitted_at IS NULL" in query
    # Atomic gate: SKIP LOCKED prevents two parallel ticks both
    # picking the same row and double-emitting.
    assert "FOR UPDATE SKIP LOCKED" in query
    # Does NOT mutate status — that's the failure sweep's job, 24h later
    assert "SET uncertain_emitted_at = now()" in query
    assert "status = 'failed'" not in query
    # Timeout passed as string-minutes
    assert params[0] == "10"
    # batch limit param
    assert params[1] == tus.SWEEP_BATCH_LIMIT


@pytest.mark.asyncio
async def test_no_op_when_nothing_stuck(monkeypatch):
    pool = _FakePool(_FakeConn([]))
    captured: list = []

    async def fake_publish(*a, **kw):
        captured.append(1)

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    stats = await tus.run_tick(pool, timeout_minutes=10)
    assert stats == {"candidates_swept": 0, "events_emitted": 0}
    assert captured == []


# ──────────────── payload contract ────────────────


@pytest.mark.asyncio
async def test_emits_uncertain_with_documented_payload(monkeypatch):
    row = _row(stuck_for=timedelta(minutes=12))
    pool = _FakePool(_FakeConn([row]))
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({"merchant_id": merchant_id, "event_type": event_type, "payload": payload})
        return "deliv-1"

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    stats = await tus.run_tick(pool, timeout_minutes=10)
    assert stats == {"candidates_swept": 1, "events_emitted": 1}

    ev = captured[0]
    assert ev["event_type"] == "transaction.uncertain"
    assert ev["merchant_id"] == "11111111-2222-3333-4444-555555555555"

    p = ev["payload"]
    # Mirrors broadcasted/failed shape — same fields, different timing
    assert p["tx_id"] == "tx-1"
    assert p["tx_unid"] == "UNID-1"
    assert p["tx_hash"] is None
    assert p["wallet_name"] == "treasury-1"
    assert p["to_address"] == "T_dest_xyz"
    assert p["amount"] == "100.5"
    assert p["token"] == "USDT"
    # New fields specific to uncertain — load-bearing for UI hints
    assert p["stuck_seconds"] is not None and p["stuck_seconds"] >= 720
    assert "24h" in p["next_check_in"]


@pytest.mark.asyncio
async def test_emits_for_each_row_even_when_one_fails(monkeypatch):
    """Per-row publish failures must NOT skip subsequent rows.
    stats reflects partial success."""
    rows = [_row(id_="tx-1"), _row(id_="tx-2"), _row(id_="tx-3")]
    pool = _FakePool(_FakeConn(rows))
    emitted: list[str] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        if payload["tx_id"] == "tx-2":
            raise RuntimeError("queue down")
        emitted.append(payload["tx_id"])

    monkeypatch.setattr(
        "backend.services.webhook_publisher.publish_event", fake_publish
    )

    stats = await tus.run_tick(pool, timeout_minutes=10)
    assert stats == {"candidates_swept": 3, "events_emitted": 2}
    assert emitted == ["tx-1", "tx-3"]


# ──────────────── timeout config ────────────────


@pytest.mark.asyncio
async def test_env_override_timeout_minutes(monkeypatch):
    """`TX_UNCERTAIN_TIMEOUT_MINUTES` env overrides the 10-min default."""
    monkeypatch.setenv("TX_UNCERTAIN_TIMEOUT_MINUTES", "20")
    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tus.run_tick(pool)

    _, (_, params) = conn.queries[0]
    assert params[0] == "20"


@pytest.mark.asyncio
async def test_env_override_ignores_garbage(monkeypatch):
    """A malformed env value falls back to the default — never crashes."""
    monkeypatch.setenv("TX_UNCERTAIN_TIMEOUT_MINUTES", "not-a-number")
    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tus.run_tick(pool)

    _, (_, params) = conn.queries[0]
    assert params[0] == "10"


@pytest.mark.asyncio
async def test_env_override_ignores_zero_and_negative(monkeypatch):
    """Non-positive values fall back to default — protects against
    accidental TX_UNCERTAIN_TIMEOUT_MINUTES=0 which would warn instantly
    on every signed tx."""
    monkeypatch.setenv("TX_UNCERTAIN_TIMEOUT_MINUTES", "0")
    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tus.run_tick(pool)

    _, (_, params) = conn.queries[0]
    assert params[0] == "10"


@pytest.mark.asyncio
async def test_explicit_timeout_overrides_env(monkeypatch):
    """Programmatic call with explicit timeout_minutes wins over env."""
    monkeypatch.setenv("TX_UNCERTAIN_TIMEOUT_MINUTES", "30")
    conn = _FakeConn([])
    pool = _FakePool(conn)
    await tus.run_tick(pool, timeout_minutes=3)

    _, (_, params) = conn.queries[0]
    assert params[0] == "3"
