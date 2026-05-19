"""Idempotency cache tests.

Covers the pure-function helpers and the lookup/save contract against
a fake asyncpg pool. The integration path (middleware → handler →
cache → replay) is exercised by the route-level test suite once the
canonical schema is up; here we keep the unit boundary tight.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from backend.services import idempotency_service as idem


# ────────────────────────────────────────────────────────────────────
# Fake pool — same shape as test_aml_alerts._FakePool.
# ────────────────────────────────────────────────────────────────────


class _FakeConn:
    def __init__(self, fixtures: list[Any] | None = None):
        self._fixtures = list(fixtures or [])
        self.queries: list[tuple[str, tuple]] = []

    async def fetchrow(self, query, *params):
        self.queries.append(("fetchrow", (query, params)))
        if not self._fixtures:
            return None
        head = self._fixtures.pop(0)
        return head

    async def execute(self, query, *params):
        self.queries.append(("execute", (query, params)))
        # Match the asyncpg result string shape so prune_expired's parser works.
        if query.strip().upper().startswith("DELETE"):
            # tag the count onto the conn so the test can read it
            return "DELETE 0"
        return "OK"


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


# ────────────────────────────────────────────────────────────────────
# compute_request_hash — pure, deterministic
# ────────────────────────────────────────────────────────────────────


def test_request_hash_is_deterministic():
    h1 = idem.compute_request_hash("POST", "/v1/transactions", b'{"a":1}')
    h2 = idem.compute_request_hash("POST", "/v1/transactions", b'{"a":1}')
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_request_hash_differs_on_method_path_body():
    base = idem.compute_request_hash("POST", "/v1/users", b'{"a":1}')
    assert base != idem.compute_request_hash("PATCH", "/v1/users", b'{"a":1}')
    assert base != idem.compute_request_hash("POST", "/v1/wallets", b'{"a":1}')
    assert base != idem.compute_request_hash("POST", "/v1/users", b'{"a":2}')


def test_request_hash_case_normalizes_method():
    assert idem.compute_request_hash("post", "/v1/x", b"") == \
           idem.compute_request_hash("POST", "/v1/x", b"")


# ────────────────────────────────────────────────────────────────────
# lookup — hit / miss / hash-drift
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_lookup_miss_returns_none():
    conn = _FakeConn(fixtures=[None])
    pool = _FakePool(conn)
    result = await idem.lookup(
        pool,
        merchant_id="00000000-0000-0000-0000-000000000001",
        idem_key="key-abc",
        request_hash="h",
    )
    assert result is None


@pytest.mark.asyncio
async def test_lookup_hit_returns_cached_response():
    conn = _FakeConn(fixtures=[{
        "request_hash": "h-original",
        "response_status": 201,
        "response_body": b'{"id":"u1"}',
        "response_headers": json.dumps({"content-type": "application/json"}),
    }])
    pool = _FakePool(conn)
    result = await idem.lookup(
        pool,
        merchant_id="00000000-0000-0000-0000-000000000001",
        idem_key="key-abc",
        request_hash="h-original",
    )
    assert result is not None
    assert result.status == 201
    assert result.body == b'{"id":"u1"}'
    assert result.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_lookup_hash_drift_still_replays(caplog):
    """If the client retries with subtly-different body bytes, we
    must NOT 409. We log a warning and replay the original — dfns-style."""
    conn = _FakeConn(fixtures=[{
        "request_hash": "h-original",
        "response_status": 200,
        "response_body": b"ok",
        "response_headers": {},  # passthrough dict, not json string
    }])
    pool = _FakePool(conn)
    with caplog.at_level("WARNING", logger="orgon.idempotency"):
        result = await idem.lookup(
            pool,
            merchant_id="00000000-0000-0000-0000-000000000001",
            idem_key="key-abc",
            request_hash="h-DIFFERENT",
        )
    assert result is not None
    assert result.status == 200
    assert any("drift" in rec.message for rec in caplog.records), \
        "drift should produce a warning log"


# ────────────────────────────────────────────────────────────────────
# save — cacheable-only, non-2xx is a no-op
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_4xx_is_noop():
    conn = _FakeConn()
    pool = _FakePool(conn)
    await idem.save(
        pool,
        merchant_id="00000000-0000-0000-0000-000000000001",
        idem_key="k",
        request_hash="h",
        status=400,
        body=b'{"error":"bad"}',
        headers={"content-type": "application/json"},
    )
    # No INSERT happened.
    assert conn.queries == []


@pytest.mark.asyncio
async def test_save_5xx_is_noop():
    conn = _FakeConn()
    pool = _FakePool(conn)
    await idem.save(
        pool,
        merchant_id="00000000-0000-0000-0000-000000000001",
        idem_key="k",
        request_hash="h",
        status=503,
        body=b"server gone",
        headers={},
    )
    assert conn.queries == []


@pytest.mark.asyncio
async def test_save_2xx_inserts():
    conn = _FakeConn()
    pool = _FakePool(conn)
    await idem.save(
        pool,
        merchant_id="00000000-0000-0000-0000-000000000001",
        idem_key="k",
        request_hash="h",
        status=201,
        body=b'{"id":"u1"}',
        headers={"content-type": "application/json"},
    )
    assert len(conn.queries) == 1
    op, (query, params) = conn.queries[0]
    assert op == "execute"
    assert "INSERT INTO merchant_idempotency_keys" in query
    assert "ON CONFLICT (merchant_id, idem_key) DO NOTHING" in query
    # params order matches the SQL
    assert params[0] == "00000000-0000-0000-0000-000000000001"
    assert params[1] == "k"
    assert params[2] == "h"
    assert params[3] == 201
    assert params[4] == b'{"id":"u1"}'
    # response_headers serialized to json string
    assert json.loads(params[5]) == {"content-type": "application/json"}


# ────────────────────────────────────────────────────────────────────
# prune_expired — parses asyncpg result string
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_prune_expired_parses_count():
    class _PruneConn(_FakeConn):
        async def execute(self, query, *params):
            self.queries.append(("execute", (query, params)))
            return "DELETE 42"

    pool = _FakePool(_PruneConn())
    n = await idem.prune_expired(pool)
    assert n == 42


@pytest.mark.asyncio
async def test_prune_expired_handles_malformed_result():
    class _BadConn(_FakeConn):
        async def execute(self, query, *params):
            self.queries.append(("execute", (query, params)))
            return ""  # asyncpg should never do this, but be defensive
    pool = _FakePool(_BadConn())
    n = await idem.prune_expired(pool)
    assert n == 0
