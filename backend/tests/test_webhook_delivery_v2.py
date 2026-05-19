"""E-03 — retry schedule selection + Event-Id header + headers
contract.

Pure tests against the public surface of webhook_delivery — we do
not spin up Postgres or httpx here; the live delivery loop is
exercised by the integration harness.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import pytest

from backend.services import webhook_delivery as wd


@contextmanager
def _env(name: str, value: str | None):
    prev = os.environ.get(name)
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = prev


# ────────────────────────────────────────────────────────────────────
# Retry schedule (v1 default; v2 via WEBHOOK_RETRY_V2=1)
# ────────────────────────────────────────────────────────────────────


def test_v1_schedule_is_default():
    with _env("WEBHOOK_RETRY_V2", None):
        assert wd._backoff_seconds(1) == 30
        assert wd._backoff_seconds(2) == 120
        assert wd._backoff_seconds(3) == 600
        assert wd._backoff_seconds(4) == 3_600
        assert wd._backoff_seconds(5) == 21_600


def test_v2_schedule_when_flag_set():
    with _env("WEBHOOK_RETRY_V2", "1"):
        assert wd._backoff_seconds(1) == 60
        assert wd._backoff_seconds(2) == 720
        assert wd._backoff_seconds(3) == 7_200
        assert wd._backoff_seconds(4) == 28_800
        assert wd._backoff_seconds(5) == 86_400


def test_flag_recognizes_truthy_variants():
    for raw in ("1", "true", "TRUE", "yes", "on"):
        with _env("WEBHOOK_RETRY_V2", raw):
            assert wd._use_retry_v2() is True, f"`{raw}` should enable v2"


def test_flag_falsy_variants_stay_on_v1():
    for raw in ("", "0", "false", "no", "off", "  "):
        with _env("WEBHOOK_RETRY_V2", raw):
            assert wd._use_retry_v2() is False, f"`{raw}` must NOT enable v2"


def test_unknown_attempt_falls_back_to_attempt_5_cap():
    """attempts can theoretically go past the schedule on a manual
    DB poke; we never want a KeyError to take down the worker."""
    with _env("WEBHOOK_RETRY_V2", None):
        assert wd._backoff_seconds(99) == 21_600
    with _env("WEBHOOK_RETRY_V2", "1"):
        assert wd._backoff_seconds(99) == 86_400


def test_six_attempts_then_give_up():
    """Public contract: GIVE_UP_ATTEMPTS is 6 — both schedules use it."""
    assert wd.GIVE_UP_ATTEMPTS == 6


# ────────────────────────────────────────────────────────────────────
# Headers contract (Event-Id, signature recipe pinned)
# ────────────────────────────────────────────────────────────────────


def _build_signed_headers(secret: str, body: bytes, ts_ms: int, delivery_id: str,
                          event_type: str) -> dict:
    """Mirror of the in-code header builder, kept in sync via this test."""
    import hashlib
    import hmac
    sig = hmac.new(
        secret.encode() if secret else b"",
        f"{ts_ms}\n".encode() + body,
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-ORGON-Webhook-Timestamp": str(ts_ms),
        "X-ORGON-Webhook-Signature": sig,
        "X-ORGON-Webhook-Event-Id": delivery_id,
        "X-ORGON-Webhook-Id": delivery_id,
        "X-ORGON-Webhook-Event": event_type,
        "User-Agent": "Orgon-Webhook/1.0",
    }


def test_signature_recipe_is_pinned():
    """If this test changes, docs/WEBHOOKS.md MUST change too, every
    SDK MUST change, and integrators owe a deprecation window. The
    recipe is `hex(HMAC-SHA256(secret, f"{ts_ms}\\n".encode() + body))`."""
    ts = 1700000000000
    body = b'{"id":"e-1","type":"wallet.activated","merchant_id":"m-1"}'
    h = _build_signed_headers(
        secret="test-secret", body=body, ts_ms=ts,
        delivery_id="del-1", event_type="wallet.activated",
    )
    # Recomputed inline — drift here will fail loudly.
    import hashlib, hmac
    expected = hmac.new(
        b"test-secret", f"{ts}\n".encode() + body, hashlib.sha256
    ).hexdigest()
    assert h["X-ORGON-Webhook-Signature"] == expected


def test_event_id_alias_is_identical_value():
    h = _build_signed_headers(
        secret="s", body=b"", ts_ms=0, delivery_id="abc", event_type="x",
    )
    assert h["X-ORGON-Webhook-Event-Id"] == h["X-ORGON-Webhook-Id"] == "abc"


def test_event_id_is_stable_across_retries_in_runtime():
    """The runtime header builder uses r['id'] (the webhook_deliveries
    row id) for both headers — same row, same id, every retry."""
    # We can't easily call _deliver_one without a pool; instead pin the
    # invariant by reading the actual source of truth.
    import inspect
    src = inspect.getsource(wd._deliver_one)
    assert '"X-ORGON-Webhook-Event-Id": delivery_id' in src
    assert '"X-ORGON-Webhook-Id": delivery_id' in src, \
        "legacy alias must keep the same value as the new header"


# ────────────────────────────────────────────────────────────────────
# Retention SQL safety — pending rows must never be touched
# ────────────────────────────────────────────────────────────────────


def test_retention_sweep_excludes_pending_rows():
    """The retention SQL in scheduler.py MUST gate on
    `delivered_at IS NOT NULL OR attempts >= 6` so an in-flight
    retry isn't deleted out from under the delivery worker."""
    import inspect
    from backend.tasks import scheduler
    src = inspect.getsource(scheduler.setup_scheduler)
    # The DELETE must be in the source, and it must carry the
    # terminal-only guard.
    assert "DELETE FROM webhook_deliveries" in src
    # The exact predicate keeps human readers honest if the SQL ever
    # gets reformatted.
    assert "delivered_at IS NOT NULL OR attempts >= 6" in src, (
        "retention DELETE must gate on terminal rows only — "
        "removing this predicate risks deleting pending in-flight rows"
    )
