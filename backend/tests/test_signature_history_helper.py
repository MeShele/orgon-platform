"""Tests for `record_signature_history` (TD-2 helper).

The helper is the shared sink for every sign / reject code-path — it
needs to work against both the `AsyncDatabase` wrapper (used by
SignatureService + TransactionService) and a bare asyncpg connection
(used by merchant_tx_service, which only has a pool-acquired conn).

We don't spin up Postgres here — that's the integration-tests job.
What we cover:

* AsyncDatabase-style execute (kwargs form) is invoked when the
  wrapper is passed in.
* asyncpg.Connection-style execute (positional *args) is invoked when
  a connection is passed in.
* Caller's UniqueViolationError surfaces unchanged — caller chooses
  whether that's a 409 or an idempotent no-op.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import asyncpg
import pytest

from backend.services.signature_service import record_signature_history


class _FakeAsyncDatabaseWrapper:
    """Mimics `backend.database.db_postgres.AsyncDatabase` — `execute()`
    takes `params=` kwarg, has `fetchrow()`. Just enough surface for the
    helper's wrapper-detection branch."""

    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.fetchrow = AsyncMock()


class _FakeConnection:
    """Mimics `asyncpg.Connection` — `execute()` takes positional *args,
    no `params=` kwarg. The wrapper-detection branch must reject this
    and fall through to the connection branch."""

    def __init__(self) -> None:
        self._calls: list[tuple[Any, ...]] = []

    async def execute(self, sql: str, *args: Any) -> Any:
        self._calls.append((sql, args))


@pytest.mark.asyncio
async def test_writes_via_async_database_wrapper_kwargs() -> None:
    db = _FakeAsyncDatabaseWrapper()
    await record_signature_history(
        db,
        tx_unid="tx-1",
        signer_address="0xABCDEF",
        action="signed",
        request_id="req-42",
    )
    db.execute.assert_called_once()
    # Sanity: SQL targets signature_history, kwargs carry the values.
    sql_arg = db.execute.call_args.args[0]
    assert "signature_history" in sql_arg
    params = db.execute.call_args.kwargs["params"]
    assert params[0] == "tx-1"
    assert params[1] == "0xABCDEF"
    assert params[2] == "signed"
    assert params[5] == "req-42"


@pytest.mark.asyncio
async def test_writes_via_asyncpg_connection_positional_args() -> None:
    conn = _FakeConnection()
    await record_signature_history(
        conn,
        tx_unid="tx-2",
        signer_address="0xCAFEBABE",
        action="rejected",
        reason="aml hold",
    )
    assert len(conn._calls) == 1
    sql, args = conn._calls[0]
    assert "signature_history" in sql
    assert args[0] == "tx-2"
    assert args[1] == "0xCAFEBABE"
    assert args[2] == "rejected"
    assert args[3] == "aml hold"
    # request_id defaulted to None — must be last positional.
    assert args[5] is None


@pytest.mark.asyncio
async def test_async_database_with_typeerror_falls_back_to_positional() -> None:
    """A wrapper that doesn't accept `params=` kwarg (some test doubles)
    still works — helper retries with positional args."""

    class _StrictWrapper:
        """Has both fetchrow + execute (so wrapper-detection picks it)
        but execute() rejects kwargs."""

        def __init__(self) -> None:
            self._calls: list[tuple[Any, ...]] = []
            self.fetchrow = AsyncMock()

        async def execute(self, sql: str, *args: Any, **kwargs: Any) -> Any:
            if kwargs:
                raise TypeError("unexpected keyword argument")
            self._calls.append((sql, args))

    db = _StrictWrapper()
    await record_signature_history(
        db,
        tx_unid="tx-3",
        signer_address="0xDEAD",
        action="signed",
    )
    # First call (kwargs form) raised TypeError; helper retried with *args.
    assert len(db._calls) == 1
    sql, args = db._calls[0]
    assert "signature_history" in sql
    assert args[0] == "tx-3"


@pytest.mark.asyncio
async def test_unique_violation_propagates_to_caller() -> None:
    """Caller decides if duplicate is a 409 or idempotent — helper
    doesn't swallow."""

    class _RaisingConn:
        async def execute(self, *a: Any, **kw: Any) -> Any:
            raise asyncpg.UniqueViolationError("duplicate")

    conn = _RaisingConn()
    with pytest.raises(asyncpg.UniqueViolationError):
        await record_signature_history(
            conn,
            tx_unid="tx-4",
            signer_address="0xBEEF",
            action="signed",
        )
