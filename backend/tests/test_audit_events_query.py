"""E-04 — pure helpers for /api/audit/events keyset query.

Endpoint-level checks (RBAC, end-to-end pagination) live in the
integration suite that talks to a real Postgres. Here we pin the
pure functions: cursor codec, parameterized WHERE builder, row
serializer. If any of these drift, the SQL generated for the
endpoint silently goes wrong and the failure mode is "missing rows
in a compliance export" — exactly the kind of thing tests must
catch.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.api import routes_audit as ra


# ────────────────────────────────────────────────────────────────────
# _parse_iso
# ────────────────────────────────────────────────────────────────────


def test_parse_iso_none_and_empty_return_none():
    assert ra._parse_iso(None, field="x") is None
    assert ra._parse_iso("", field="x") is None


def test_parse_iso_accepts_naive_and_offset_and_z():
    a = ra._parse_iso("2026-05-19T10:00:00", field="since")
    b = ra._parse_iso("2026-05-19T10:00:00+00:00", field="since")
    c = ra._parse_iso("2026-05-19T10:00:00Z", field="since")
    assert a.year == b.year == c.year == 2026
    assert b.tzinfo is not None and c.tzinfo is not None


def test_parse_iso_bad_input_raises_400():
    with pytest.raises(HTTPException) as exc:
        ra._parse_iso("not-a-date", field="since")
    assert exc.value.status_code == 400
    assert "since" in str(exc.value.detail)


# ────────────────────────────────────────────────────────────────────
# cursor codec round-trip
# ────────────────────────────────────────────────────────────────────


def test_cursor_round_trip():
    ts = datetime(2026, 5, 19, 10, 0, 0, 123456, tzinfo=timezone.utc)
    enc = ra._encode_cursor(ts, 7777)
    decoded = ra._decode_cursor(enc)
    assert decoded == (ts, 7777)


def test_decode_cursor_none_and_empty_return_none():
    assert ra._decode_cursor(None) is None
    assert ra._decode_cursor("") is None


def test_decode_cursor_bad_input_raises_400():
    with pytest.raises(HTTPException) as exc:
        ra._decode_cursor("garbage-no-pipe")
    assert exc.value.status_code == 400


# ────────────────────────────────────────────────────────────────────
# WHERE builder — parameter discipline, never string-interpolates input
# ────────────────────────────────────────────────────────────────────


def test_build_where_empty_returns_empty_where_and_no_params():
    where, params = ra._build_where(
        action=None, resource_type=None, resource_id=None,
        actor_user_id=None, since=None, until=None, cursor=None,
    )
    assert where == ""
    assert params == []


def test_build_where_action_filter_only():
    where, params = ra._build_where(
        action="transaction.signed", resource_type=None, resource_id=None,
        actor_user_id=None, since=None, until=None, cursor=None,
    )
    assert where == " WHERE action = $1"
    assert params == ["transaction.signed"]


def test_build_where_all_filters_use_distinct_placeholders():
    since = datetime(2026, 5, 1, tzinfo=timezone.utc)
    until = datetime(2026, 5, 31, tzinfo=timezone.utc)
    where, params = ra._build_where(
        action="X",
        resource_type="wallet",
        resource_id="w-1",
        actor_user_id=42,
        since=since,
        until=until,
        cursor=None,
    )
    # Each filter contributes exactly one parameter, in declared order.
    assert params == ["X", "wallet", "w-1", 42, since, until]
    # All placeholders are unique 1..6 and the SQL is parameterized
    # (no `'X'` literal etc.).
    for raw in ("X", "wallet", "w-1", "42"):
        assert raw not in where, f"raw value {raw!r} must not appear in WHERE — only $N placeholders"
    for i in range(1, 7):
        assert f"${i}" in where


def test_build_where_keyset_cursor_adds_three_placeholders():
    cursor_ts = datetime(2026, 5, 19, 10, tzinfo=timezone.utc)
    where, params = ra._build_where(
        action=None, resource_type=None, resource_id=None,
        actor_user_id=None, since=None, until=None,
        cursor=(cursor_ts, 100),
    )
    # cursor adds (ts, ts, id) — composite keyset compare
    assert params == [cursor_ts, cursor_ts, 100]
    assert "$1" in where and "$2" in where and "$3" in where
    assert "created_at < $1" in where
    assert "created_at = $2 AND id < $3" in where


def test_build_where_combines_action_and_cursor_correctly():
    cursor_ts = datetime(2026, 5, 19, 10, tzinfo=timezone.utc)
    where, params = ra._build_where(
        action="x", resource_type=None, resource_id=None,
        actor_user_id=None, since=None, until=None,
        cursor=(cursor_ts, 5),
    )
    assert params == ["x", cursor_ts, cursor_ts, 5]
    assert "action = $1" in where
    # cursor terms must reference $2/$3/$4, not $1
    assert "created_at < $2" in where
    assert "AND id < $4" in where


# ────────────────────────────────────────────────────────────────────
# Row serializer — stable dictionary contract
# ────────────────────────────────────────────────────────────────────


class _Row(dict):
    """asyncpg.Record-shaped enough for our purposes."""
    pass


def test_serialize_row_normalizes_types():
    ts = datetime(2026, 5, 19, 10, 0, tzinfo=timezone.utc)
    row = _Row({
        "id": 42,
        "user_id": 7,
        "action": "wallet.created",
        "resource_type": "wallet",
        "resource_id": "w-1",
        "details": {"foo": "bar"},
        "ip_address": "1.2.3.4",
        "user_agent": "ua",
        "created_at": ts,
    })
    out = ra._serialize_row(row)
    assert out["id"] == 42
    assert out["user_id"] == 7
    assert out["details"] == {"foo": "bar"}
    assert out["created_at"] == ts.isoformat()


def test_serialize_row_parses_string_details():
    ts = datetime(2026, 5, 19, tzinfo=timezone.utc)
    row = _Row({
        "id": 1, "user_id": None, "action": "x",
        "resource_type": None, "resource_id": None,
        "details": '{"k":"v"}',
        "ip_address": None, "user_agent": None,
        "created_at": ts,
    })
    out = ra._serialize_row(row)
    assert out["details"] == {"k": "v"}
    assert out["user_id"] is None


def test_serialize_row_null_details_becomes_empty_dict():
    ts = datetime(2026, 5, 19, tzinfo=timezone.utc)
    row = _Row({
        "id": 1, "user_id": None, "action": "x",
        "resource_type": None, "resource_id": None,
        "details": None,
        "ip_address": None, "user_agent": None,
        "created_at": ts,
    })
    out = ra._serialize_row(row)
    assert out["details"] == {}
