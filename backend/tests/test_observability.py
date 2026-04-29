"""Unit tests for the JSON log formatter."""

import json
import logging

from backend.observability import JsonFormatter, configure_observability


def _record(msg: str = "hello", level: int = logging.INFO, name: str = "orgon.test", **extra) -> logging.LogRecord:
    rec = logging.LogRecord(
        name=name, level=level, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )
    for k, v in extra.items():
        setattr(rec, k, v)
    return rec


def test_minimal_record_is_valid_json():
    out = JsonFormatter().format(_record())
    parsed = json.loads(out)
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "orgon.test"
    assert parsed["msg"] == "hello"
    assert "ts" in parsed and parsed["ts"].endswith("Z")


def test_record_with_args_renders_full_message():
    rec = logging.LogRecord(
        name="orgon", level=logging.WARNING, pathname=__file__, lineno=1,
        msg="user %s failed %d times", args=("alice", 3), exc_info=None,
    )
    parsed = json.loads(JsonFormatter().format(rec))
    assert parsed["msg"] == "user alice failed 3 times"
    assert parsed["level"] == "WARNING"


def test_extra_fields_propagated():
    rec = _record(partner_id="abc", count=42, payload={"k": "v"})
    parsed = json.loads(JsonFormatter().format(rec))
    assert parsed["partner_id"] == "abc"
    assert parsed["count"] == 42
    assert parsed["payload"] == {"k": "v"}


def test_unjsonable_extra_falls_back_to_repr():
    class NotJsonable:
        def __repr__(self): return "<NotJsonable>"
    rec = _record(thing=NotJsonable())
    parsed = json.loads(JsonFormatter().format(rec))
    assert parsed["thing"] == "<NotJsonable>"


def test_exception_info_is_serialized():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = logging.LogRecord(
            name="orgon", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="caught", args=(), exc_info=sys.exc_info(),
        )
    parsed = json.loads(JsonFormatter().format(rec))
    assert "exc" in parsed
    assert "ValueError: boom" in parsed["exc"]


def test_configure_is_noop_without_env(monkeypatch):
    monkeypatch.delenv("ORGON_JSON_LOGS", raising=False)
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    # Should not raise; should not replace handlers
    root_handlers_before = list(logging.getLogger().handlers)
    configure_observability()
    assert logging.getLogger().handlers == root_handlers_before
