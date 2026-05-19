"""Treasury & per-wallet balance read-path contract.

Pins:
- merchant scoping (cross-merchant lookup → None, not error)
- response shape (wallet_id, network, address, status, purpose,
  end_user_id, as_of, balances)
- empty-balances paths (no token rows, no Safina wallet_id yet)
- treasury filter excludes user_deposit
- `as_of` is iso8601 string when present, null when not
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import pytest

from backend.services import merchant_balance_service as bal


MERCHANT_A = "11111111-2222-3333-4444-555555555555"
MERCHANT_B = "99999999-8888-7777-6666-555555555555"
WALLET_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SAFINA_WID = 42  # integer Safina assigns


def _wallet_row(*, organization_id=MERCHANT_A, purpose="user_deposit", safina_wid=SAFINA_WID, addr="T_addr_xyz"):
    return {
        "id": WALLET_ID,
        "name": "test-wallet",
        "network": 5010,
        "addr": addr,
        "purpose": purpose,
        "end_user_id": "99999999-1111-2222-3333-444444444444" if purpose == "user_deposit" else None,
        "safina_wallet_id": safina_wid,
        "created_at": datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    }


def _balance_row(*, token="USDT", value="100.50", decimals="6", network="5010", ts: datetime | None = None):
    return {
        "token": token,
        "value": value,
        "decimals": decimals,
        "network": network,
        "updated_at": ts or datetime(2026, 5, 19, 10, 23, 14, tzinfo=timezone.utc),
    }


class _FakeConn:
    """Programmable conn — each fetchrow/fetch call pops a queued result.

    Calls beyond the queue return None / []. Captures every query+params
    for assertions.
    """

    def __init__(
        self,
        fetchrow_results: list[Any] | None = None,
        fetch_results: list[Any] | None = None,
    ):
        self._fr = list(fetchrow_results or [])
        self._fa = list(fetch_results or [])
        self.queries: list[tuple[str, str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", query, params))
        if not self._fr:
            return None
        return self._fr.pop(0)

    async def fetch(self, query, *params):
        self.queries.append(("fetch", query, params))
        if not self._fa:
            return []
        return self._fa.pop(0)


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


# ───────────────────────── get_wallet_balance ─────────────────────────


@pytest.mark.asyncio
async def test_get_wallet_balance_full_shape():
    conn = _FakeConn(
        fetchrow_results=[_wallet_row()],
        fetch_results=[[
            _balance_row(token="USDT", value="100.50", decimals="6"),
            _balance_row(token="TRX", value="10.0", decimals="6", ts=datetime(2026, 5, 19, 9, 0, tzinfo=timezone.utc)),
        ]],
    )
    pool = _FakePool(conn)

    out = await bal.get_wallet_balance(pool, merchant_id=MERCHANT_A, wallet_id=WALLET_ID)

    assert out is not None
    assert out["wallet_id"] == WALLET_ID
    assert out["network"] == 5010
    assert out["address"] == "T_addr_xyz"
    assert out["status"] == "active"
    assert out["purpose"] == "user_deposit"
    # as_of = MAX of balance updated_at — picks the later one
    assert out["as_of"] == "2026-05-19T10:23:14+00:00"
    assert out["balances"] == [
        {"token": "USDT", "value": "100.50", "decimals": "6"},
        {"token": "TRX", "value": "10.0", "decimals": "6"},
    ]


@pytest.mark.asyncio
async def test_get_wallet_balance_other_merchant_returns_none():
    """Scope-check: wallet of merchant B must look exactly like 404 to
    merchant A. The SELECT WHERE organization_id = $1 simply returns no
    row — that's how the service signals 'not found'.
    """
    conn = _FakeConn(fetchrow_results=[None])
    pool = _FakePool(conn)

    out = await bal.get_wallet_balance(pool, merchant_id=MERCHANT_B, wallet_id=WALLET_ID)
    assert out is None


@pytest.mark.asyncio
async def test_get_wallet_balance_empty_balances():
    """Wallet exists, but `token_balances` has no rows yet — common
    right after wallet creation, before the next sync tick."""
    conn = _FakeConn(
        fetchrow_results=[_wallet_row()],
        fetch_results=[[]],  # no token rows
    )
    pool = _FakePool(conn)

    out = await bal.get_wallet_balance(pool, merchant_id=MERCHANT_A, wallet_id=WALLET_ID)
    assert out["balances"] == []
    assert out["as_of"] is None


@pytest.mark.asyncio
async def test_get_wallet_balance_pending_no_safina_wid():
    """Wallet exists locally but Safina hasn't returned a `wallet_id`
    integer yet (the activation race window). We must not blow up —
    return empty balances with `as_of=null` and `status=pending`.
    """
    conn = _FakeConn(
        fetchrow_results=[_wallet_row(safina_wid=None, addr="")],
    )
    pool = _FakePool(conn)

    out = await bal.get_wallet_balance(pool, merchant_id=MERCHANT_A, wallet_id=WALLET_ID)
    assert out["balances"] == []
    assert out["as_of"] is None
    assert out["status"] == "pending"
    assert out["address"] is None


@pytest.mark.asyncio
async def test_get_wallet_balance_scope_is_in_query():
    """The SELECT MUST filter on `organization_id = $1` — caller-side
    code never trusts a raw wallet_id, this is the only enforcement."""
    conn = _FakeConn(fetchrow_results=[None])
    pool = _FakePool(conn)

    await bal.get_wallet_balance(pool, merchant_id=MERCHANT_A, wallet_id=WALLET_ID)

    op, query, params = conn.queries[0]
    assert op == "fetchrow"
    assert "organization_id = $1" in query
    assert "id = $2" in query
    assert "is_hidden" in query
    assert str(params[0]) == MERCHANT_A
    assert str(params[1]) == WALLET_ID


# ───────────────────────── get_merchant_treasury ─────────────────────────


@pytest.mark.asyncio
async def test_get_treasury_only_merchant_owned_purposes_in_query():
    conn = _FakeConn(fetch_results=[[]])
    pool = _FakePool(conn)

    await bal.get_merchant_treasury(pool, merchant_id=MERCHANT_A)

    op, query, params = conn.queries[0]
    assert op == "fetch"
    # explicit purpose whitelist — user_deposit MUST NOT leak into treasury
    assert "purpose IN ('treasury', 'fee', 'hot', 'cold')" in query
    assert "user_deposit" not in query  # not even in a comment near this clause
    assert "organization_id = $1" in query
    assert str(params[0]) == MERCHANT_A


@pytest.mark.asyncio
async def test_get_treasury_assembles_per_wallet_balances():
    treasury_w = _wallet_row(purpose="treasury", safina_wid=42)
    fee_w = _wallet_row(purpose="fee", safina_wid=43)
    conn = _FakeConn(
        fetch_results=[
            # First call: SELECT wallets
            [treasury_w, fee_w],
            # Second call: balances for safina_wid=42
            [_balance_row(token="USDT", value="500.0")],
            # Third call: balances for safina_wid=43
            [_balance_row(token="TRX", value="200.0")],
        ],
    )
    pool = _FakePool(conn)

    out = await bal.get_merchant_treasury(pool, merchant_id=MERCHANT_A)

    assert len(out["wallets"]) == 2
    assert out["wallets"][0]["purpose"] == "treasury"
    assert out["wallets"][0]["balances"][0]["token"] == "USDT"
    assert out["wallets"][1]["purpose"] == "fee"
    assert out["wallets"][1]["balances"][0]["token"] == "TRX"


@pytest.mark.asyncio
async def test_get_treasury_empty_for_merchant_with_no_treasury_wallets():
    conn = _FakeConn(fetch_results=[[]])
    pool = _FakePool(conn)

    out = await bal.get_merchant_treasury(pool, merchant_id=MERCHANT_A)
    assert out == {"wallets": []}


@pytest.mark.asyncio
async def test_get_treasury_wallet_without_safina_wid_returns_empty_balances():
    """A treasury wallet local row that doesn't yet have a Safina wallet_id
    appears in the list with empty balances — not omitted, not erroring."""
    pending_w = _wallet_row(purpose="treasury", safina_wid=None, addr="")
    conn = _FakeConn(fetch_results=[[pending_w]])
    pool = _FakePool(conn)

    out = await bal.get_merchant_treasury(pool, merchant_id=MERCHANT_A)
    assert len(out["wallets"]) == 1
    assert out["wallets"][0]["balances"] == []
    assert out["wallets"][0]["as_of"] is None
    assert out["wallets"][0]["status"] == "pending"
