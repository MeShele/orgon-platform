"""Wave 36 — SAR email backend enrichments.

Pins:
- `build_external_reference` produces stable, human-readable refs
- CSV serialisation flattens load-bearing fields with stable column order
- `describe_active_config` reports honest readiness state per env shape
- Email backend builds Excel/CSV/JSON/MD attachments when SMTP env set
  (uses a stubbed SMTP transport to avoid actual network IO)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from backend.regulators.finsupervisory import submission_backends as sb


def _alert() -> dict:
    return {
        "id": "alert-uuid-1234-5678-aaaabbbb",
        "severity": "high",
        "status": "reported",
        "created_at": "2026-05-19T10:00:00+00:00",
        "rule_name": "high-value-send",
        "rule_type": "threshold",
        "action": "hold",
    }


def _tx() -> dict:
    return {
        "id": "tx-uuid-1",
        "tx_hash": "0xfeedbeef",
        "network": 5010,
        "value": "50000.000000",
        "token": "USDT",
        "from_address": "T_sender_xyz",
        "to_address": "T_dest_abc",
    }


def _org() -> dict:
    return {"name": "ACME Exchange Ltd", "inn": "12345678901234", "address": "Bishkek, somewhere"}


def _officer() -> dict:
    return {"full_name": "Ivan Compliance", "email": "ivan@acme.kg", "phone": "+996 700 000 000"}


def _payload() -> dict:
    return {
        "alert": _alert(),
        "transaction": _tx(),
        "filing_org": _org(),
        "officer": _officer(),
    }


# ───────────── external reference ─────────────


def test_external_reference_includes_short_alert_id_and_timestamp():
    payload = _payload()
    ref = sb.build_external_reference(payload)
    assert ref.startswith("ORGON-SAR-")
    parts = ref.split("-")
    # ORGON-SAR-<short>-<ts>
    assert len(parts) == 4
    assert parts[0] == "ORGON"
    assert parts[1] == "SAR"
    # short = first 8 hex chars of alert id with dashes stripped
    assert parts[2] == "alertuui"
    # timestamp is current unix seconds — at least 10 digits
    assert parts[3].isdigit() and len(parts[3]) >= 10


def test_external_reference_handles_missing_alert_id():
    """If `alert.id` is missing (defensive), the ref still renders."""
    ref = sb.build_external_reference({"alert": {}})
    assert ref.startswith("ORGON-SAR-unknown-")


# ───────────── CSV serialisation ─────────────


def test_csv_has_stable_header_row():
    csv_bytes = sb._payload_to_csv_bytes(_payload())
    csv = csv_bytes.decode("utf-8")
    lines = csv.strip().split("\n")
    assert len(lines) == 2, "header + one data row"
    headers = lines[0].split(",")
    # Critical columns the regulator's form depends on — these MUST be present
    for required in (
        "external_reference",
        "alert_id",
        "rule_name",
        "transaction_hash",
        "transaction_value",
        "transaction_token",
        "filing_org_name",
        "filing_org_inn",
        "officer_name",
    ):
        assert required in headers, f"missing required column: {required}"


def test_csv_values_match_payload():
    payload = _payload()
    payload["external_reference"] = "ORGON-SAR-test-123"
    csv = sb._payload_to_csv_bytes(payload).decode("utf-8")
    assert "ORGON-SAR-test-123" in csv
    assert "ACME Exchange Ltd" in csv
    assert "0xfeedbeef" in csv
    assert "50000.000000" in csv
    assert "USDT" in csv


def test_csv_handles_missing_optional_fields():
    """Officer phone, transaction.to_address etc. may be missing —
    CSV must render empty string instead of 'None' / 'null' / crash."""
    csv_bytes = sb._payload_to_csv_bytes({"alert": _alert()})
    csv = csv_bytes.decode("utf-8")
    # No literal 'None' values bleeding through
    assert ",None" not in csv
    assert "None," not in csv


# ───────────── describe_active_config ─────────────


def test_describe_config_default_is_manual_export(monkeypatch):
    """Unset env → 'manual_export', ready=True (always works)."""
    for k in ("FINSUPERVISORY_SAR_BACKEND", "FINSUPERVISORY_SAR_EMAIL",
              "FINSUPERVISORY_SAR_CC", "SMTP_HOST"):
        monkeypatch.delenv(k, raising=False)
    cfg = sb.describe_active_config()
    assert cfg["backend"] == "manual_export"
    assert cfg["ready"] is True
    assert cfg["missing_env"] == []
    assert cfg["target_email"] is None
    assert cfg["cc_email"] is None
    assert cfg["smtp_configured"] is False


def test_describe_config_email_mode_lists_missing_env(monkeypatch):
    """Email backend selected but neither env set — report both gaps."""
    monkeypatch.setenv("FINSUPERVISORY_SAR_BACKEND", "email")
    monkeypatch.delenv("FINSUPERVISORY_SAR_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    cfg = sb.describe_active_config()
    assert cfg["backend"] == "email"
    assert cfg["ready"] is False
    assert "FINSUPERVISORY_SAR_EMAIL" in cfg["missing_env"]
    assert "SMTP_HOST" in cfg["missing_env"]


def test_describe_config_email_mode_ready_when_env_complete(monkeypatch):
    monkeypatch.setenv("FINSUPERVISORY_SAR_BACKEND", "email")
    monkeypatch.setenv("FINSUPERVISORY_SAR_EMAIL", "compliance@fiu.gov.kg")
    monkeypatch.setenv("FINSUPERVISORY_SAR_CC", "officer@acme.kg")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    cfg = sb.describe_active_config()
    assert cfg["backend"] == "email"
    assert cfg["ready"] is True
    assert cfg["target_email"] == "compliance@fiu.gov.kg"
    assert cfg["cc_email"] == "officer@acme.kg"
    assert cfg["smtp_configured"] is True


def test_describe_config_api_v1_always_reports_not_ready(monkeypatch):
    """api_v1 is a stub until Финнадзор publishes a spec — surface that."""
    monkeypatch.setenv("FINSUPERVISORY_SAR_BACKEND", "api_v1")
    cfg = sb.describe_active_config()
    assert cfg["backend"] == "api_v1"
    assert cfg["ready"] is False
    assert any("api_v1 is reserved" in m for m in cfg["missing_env"])


def test_describe_config_unknown_backend_falls_back(monkeypatch):
    """Garbage env value falls back to manual_export — never crashes the dashboard."""
    monkeypatch.setenv("FINSUPERVISORY_SAR_BACKEND", "totally-not-real")
    cfg = sb.describe_active_config()
    assert cfg["backend"] == "manual_export"


# ───────────── email backend SMTP integration ─────────────


def test_email_backend_calls_smtp_when_configured(monkeypatch):
    """With env complete, SMTP send_message is called with a message
    carrying 3 attachments + a body containing the reference. We stub
    the SMTP class so the test doesn't hit the network."""
    monkeypatch.setenv("FINSUPERVISORY_SAR_EMAIL", "compliance@fiu.gov.kg")
    monkeypatch.setenv("FINSUPERVISORY_SAR_CC", "officer@acme.kg")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    monkeypatch.setenv("SMTP_FROM", "noreply@orgon.kg")

    sent_messages: list[Any] = []

    class _FakeSMTP:
        def __init__(self, host, port, timeout):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return None

        def starttls(self):
            pass

        def login(self, u, p):
            pass

        def send_message(self, msg):
            sent_messages.append(msg)

    with patch("smtplib.SMTP", _FakeSMTP):
        result = sb._backend_email(_payload(), "rendered markdown body")

    assert result["status"] == "sent"
    assert result["external_reference"] is not None
    assert result["external_reference"].startswith("ORGON-SAR-")
    assert "compliance@fiu.gov.kg" in result["response_body"]
    assert "cc: officer@acme.kg" in result["response_body"]

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert msg["To"] == "compliance@fiu.gov.kg"
    assert msg["Cc"] == "officer@acme.kg"
    # Subject carries reference + severity for inbox triage
    assert "ORGON-SAR-" in msg["Subject"]
    assert "HIGH" in msg["Subject"]

    # 3 attachments: CSV + JSON + MD
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 3
    filenames = {a.get_filename() for a in attachments}
    assert any(f.endswith(".csv") for f in filenames)
    assert any(f.endswith(".json") for f in filenames)
    assert any(f.endswith(".md") for f in filenames)


def test_email_backend_omits_cc_when_unset(monkeypatch):
    """No CC env → no Cc header. Single-recipient response_body."""
    monkeypatch.setenv("FINSUPERVISORY_SAR_EMAIL", "compliance@fiu.gov.kg")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.delenv("FINSUPERVISORY_SAR_CC", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)

    sent: list[Any] = []

    class _FakeSMTP:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *exc): return None
        def send_message(self, msg): sent.append(msg)

    with patch("smtplib.SMTP", _FakeSMTP):
        result = sb._backend_email(_payload(), "body")

    assert result["status"] == "sent"
    assert "cc:" not in result["response_body"]
    assert sent[0].get("Cc") is None


def test_email_backend_returns_ref_even_on_smtp_failure(monkeypatch):
    """SMTP errors must surface the reference so the operator can
    correlate the failed attempt with the persisted sar_submissions row."""
    monkeypatch.setenv("FINSUPERVISORY_SAR_EMAIL", "compliance@fiu.gov.kg")
    monkeypatch.setenv("SMTP_HOST", "broken.example.com")

    class _BoomSMTP:
        def __init__(self, *a, **kw): pass
        def __enter__(self): raise ConnectionError("no route to host")
        def __exit__(self, *exc): return None

    with patch("smtplib.SMTP", _BoomSMTP):
        result = sb._backend_email(_payload(), "body")

    assert result["status"] == "failed"
    assert result["external_reference"] is not None
    assert result["external_reference"].startswith("ORGON-SAR-")
    assert "SMTP error" in result["response_body"]
