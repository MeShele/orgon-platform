"""`/v1/deposits/lookup` — support tool for "where is my crypto" tickets.

Pins:
- service correctly scopes to caller's merchant (SQL has `merchant_id = $1`)
- multi-row case (one tx → multiple log_index'es) sorted by log_index ASC
- empty result = found:false + structured wrong-network hint
- include_offchain=true populates the placeholder block (today: not_supported)
- amount serialised as string (decimal-safe across SDK boundaries)
- block_timestamp serialised as ISO8601 when present, null when not
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from backend.services import merchant_deposit_lookup_service as dlookup


MERCHANT_A = "11111111-2222-3333-4444-555555555555"
MERCHANT_B = "99999999-8888-7777-6666-555555555555"


class _FakeConn:
    def __init__(self, fetch_results: list[list[Any]] | None = None):
        self._fa = list(fetch_results or [])
        self.queries: list[tuple[str, tuple]] = []

    async def fetch(self, query, *params):
        self.queries.append((query, params))
        return self._fa.pop(0) if self._fa else []


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


def _deposit_row(*, log_index: int = 0, tx_hash: str = "0xabc", asset: str = "USDT", amount: str = "100.5"):
    return {
        "id": str(uuid4()),
        "merchant_id": MERCHANT_A,
        "wallet_id": str(uuid4()),
        "end_user_id": str(uuid4()),
        "network": 5010,
        "tx_hash": tx_hash,
        "log_index": log_index,
        "from_address": "T_sender_123",
        "to_address": "T_dest_xyz",
        "asset": asset,
        "amount": Decimal(amount),
        "confirmations": 12,
        "block_number": 98765,
        "block_timestamp": datetime(2026, 5, 19, 10, 23, tzinfo=timezone.utc),
        "discovered_at": datetime(2026, 5, 19, 10, 24, tzinfo=timezone.utc),
        "status": "confirmed",
    }


# ──────────────── service-layer scoping ────────────────


@pytest.mark.asyncio
async def test_lookup_scopes_query_to_merchant_and_tx_hash():
    """SQL MUST filter on both (merchant_id, tx_hash) — never trust
    caller-supplied tenancy. Index relies on the same shape."""
    conn = _FakeConn([[]])
    await dlookup.lookup_by_tx_hash(
        _FakePool(conn), merchant_id=MERCHANT_A, tx_hash="0xdeadbeef",
    )
    query, params = conn.queries[0]
    assert "merchant_id = $1" in query
    assert "tx_hash" in query and "$2" in query
    assert str(params[0]) == MERCHANT_A
    assert params[1] == "0xdeadbeef"
    # Result ordering — log_index ASC so multi-transfer tx renders in tx order
    assert "ORDER BY log_index ASC" in query


@pytest.mark.asyncio
async def test_lookup_returns_empty_when_no_match():
    """No 404 here — the lookup succeeded, just returned zero rows."""
    pool = _FakePool(_FakeConn([[]]))
    rows = await dlookup.lookup_by_tx_hash(pool, merchant_id=MERCHANT_A, tx_hash="0xfeed")
    assert rows == []


@pytest.mark.asyncio
async def test_lookup_returns_all_rows_for_multi_transfer_tx():
    """ETH/ERC-20 batch txs produce multiple deposits with same
    tx_hash but different log_index. Return them all."""
    rows_in = [
        _deposit_row(log_index=0, amount="100.0", asset="USDT"),
        _deposit_row(log_index=2, amount="50.0", asset="USDT"),
    ]
    pool = _FakePool(_FakeConn([rows_in]))
    rows_out = await dlookup.lookup_by_tx_hash(pool, merchant_id=MERCHANT_A, tx_hash="0xbatch")
    assert len(rows_out) == 2
    assert rows_out[0]["log_index"] == 0
    assert rows_out[1]["log_index"] == 2


@pytest.mark.asyncio
async def test_lookup_serialises_amount_as_string():
    """Decimal MUST cross the API boundary as string — float would
    silently truncate at 17 digits."""
    pool = _FakePool(_FakeConn([[_deposit_row(amount="100.123456789012345678")]]))
    rows = await dlookup.lookup_by_tx_hash(pool, merchant_id=MERCHANT_A, tx_hash="0x")
    assert isinstance(rows[0]["amount"], str)
    assert rows[0]["amount"] == "100.123456789012345678"


@pytest.mark.asyncio
async def test_lookup_serialises_timestamps_as_iso():
    pool = _FakePool(_FakeConn([[_deposit_row()]]))
    rows = await dlookup.lookup_by_tx_hash(pool, merchant_id=MERCHANT_A, tx_hash="0x")
    assert rows[0]["block_timestamp"] == "2026-05-19T10:23:00+00:00"
    assert rows[0]["discovered_at"] == "2026-05-19T10:24:00+00:00"


@pytest.mark.asyncio
async def test_lookup_handles_missing_block_timestamp():
    row = _deposit_row()
    row["block_timestamp"] = None
    pool = _FakePool(_FakeConn([[row]]))
    rows = await dlookup.lookup_by_tx_hash(pool, merchant_id=MERCHANT_A, tx_hash="0x")
    assert rows[0]["block_timestamp"] is None


# ──────────────── build_lookup_response shape ────────────────


def test_response_shape_when_found():
    out = dlookup.build_lookup_response(
        tx_hash="0xabc",
        deposits=[{"id": "d1"}, {"id": "d2"}],
        include_offchain=False,
    )
    assert out["tx_hash"] == "0xabc"
    assert out["found"] is True
    assert len(out["deposits"]) == 2
    assert out["hint"] is None
    assert "offchain_lookup" not in out


def test_response_shape_when_not_found_has_hint():
    """The hint is the load-bearing part — without it support has no
    UI text to render explaining the wrong-network failure mode."""
    out = dlookup.build_lookup_response(
        tx_hash="0xabc",
        deposits=[],
        include_offchain=False,
    )
    assert out["found"] is False
    assert out["deposits"] == []
    assert out["hint"] is not None
    # Mention of wrong-network failure mode is essential
    assert "wrong-network" in out["hint"].lower() or "wrong network" in out["hint"].lower()


def test_response_includes_offchain_block_when_requested():
    out = dlookup.build_lookup_response(
        tx_hash="0xabc",
        deposits=[],
        include_offchain=True,
    )
    assert "offchain_lookup" in out
    assert out["offchain_lookup"]["supported"] is False
    # Hint reserved for future implementation, must not be empty
    assert out["offchain_lookup"]["hint"]
    assert "support@orgon" in out["offchain_lookup"]["hint"]


def test_response_omits_offchain_block_when_not_requested():
    out = dlookup.build_lookup_response(
        tx_hash="0xabc",
        deposits=[],
        include_offchain=False,
    )
    assert "offchain_lookup" not in out


def test_response_offchain_block_present_even_when_found():
    """Even when DB lookup found rows, if caller asked for offchain we
    still surface the reserved block — keeps the contract uniform."""
    out = dlookup.build_lookup_response(
        tx_hash="0xabc",
        deposits=[{"id": "d1"}],
        include_offchain=True,
    )
    assert out["found"] is True
    assert "offchain_lookup" in out
