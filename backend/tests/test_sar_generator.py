"""Tests for the SAR generator + submission backend registry
(Wave 24, Story 2.9). Pure-function only — endpoint integration is
covered in `test_sar_endpoints.py`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import pytest

from backend.regulators.finsupervisory import (
    PII_SCRUB_KEYS,
    build_sar_payload,
    list_backends,
    render_sar_markdown,
    resolve_backend,
)


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


@pytest.fixture
def alert():
    return {
        "id": "alert-uuid-1",
        "alert_type": "sumsub:applicantOnHold",
        "severity": "critical",
        "description": "Sumsub flagged sanctions hit",
        "details": {
            "applicantId": "sumsub-abc",
            "rejectLabels": ["SANCTIONS"],
            "passport_number": "AB1234567",       # PII — must redact
            "national_id": "9112345678",           # PII — must redact
            "nested": {"inn": "1234567890", "ok": "still-here"},
        },
        "resolution": "OFAC list match confirmed",
        "investigation_notes": "[2026-05-02 10:00] auditor: cross-checked",
        "created_at": datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def transaction():
    return {
        "id": "tx-uuid-1",
        "unid": "0xdeadbeef",
        "tx_hash": "0xabc123",
        "from_address": "0xfrom",
        "to_address": "0xto",
        "value": "1000000",
        "token": "ETH",
        "network": 1,
        "status": "rejected_signer_mismatch",
        "created_at": datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def organization():
    return {
        "id": "org-uuid-1",
        "name": "Acme Custody KG",
        "registration_number": "BL-1234",
        "country": "KG",
        "legal_address": "Bishkek, Manas 1",
        "contact_email": "compliance@acme.kg",
    }


@pytest.fixture
def officer():
    return {
        "id": 42,
        "full_name": "Auditor Smith",
        "email": "auditor@orgon.test",
        "phone": "+996700000000",
    }


@pytest.fixture
def env_isolated(monkeypatch):
    for k in (
        "FINSUPERVISORY_SAR_BACKEND",
        "FINSUPERVISORY_SAR_EMAIL",
        "SMTP_HOST",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "SMTP_PORT",
    ):
        monkeypatch.delenv(k, raising=False)
    yield monkeypatch


# ────────────────────────────────────────────────────────────────────
# Generator
# ────────────────────────────────────────────────────────────────────


def test_payload_top_level_shape(alert, transaction, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=transaction,
        organization=organization, officer=officer,
        filed_at=datetime(2026, 5, 2, tzinfo=timezone.utc),
    )
    assert payload["schema_version"] == "orgon.sar.v1"
    assert payload["filed_at"] == "2026-05-02T00:00:00+00:00"
    assert payload["filing_org"]["name"] == "Acme Custody KG"
    assert payload["officer"]["email"] == "auditor@orgon.test"
    assert payload["alert"]["id"] == "alert-uuid-1"
    assert payload["transaction"]["unid"] == "0xdeadbeef"
    assert payload["supporting_documents"] == []


def test_payload_redacts_pii_in_details(alert, transaction, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=transaction,
        organization=organization, officer=officer,
    )
    redacted = payload["alert"]["details_redacted"]
    assert redacted["passport_number"] == "***hidden***"
    assert redacted["national_id"] == "***hidden***"
    assert redacted["nested"]["inn"] == "***hidden***"
    assert redacted["nested"]["ok"] == "still-here"
    # Non-PII keys survive verbatim.
    assert redacted["applicantId"] == "sumsub-abc"
    assert redacted["rejectLabels"] == ["SANCTIONS"]


def test_payload_no_transaction_when_kyc_only(alert, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    assert payload["transaction"] is None


def test_payload_handles_missing_org_fields(alert, officer):
    """Tenant onboarding may not have filled every org field — ensure
    we don't crash on Nones, just fall through."""
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization={"id": "x", "name": ""},
        officer=officer,
    )
    fo = payload["filing_org"]
    assert fo["registration_no"] is None
    assert fo["legal_address"] is None


def test_pii_scrub_keys_synced_with_frontend():
    """Frontend `PII_SCRUB_KEYS` must match — operators see consistent
    redaction in the AML drawer and in SAR previews."""
    expected = {"passport_number", "national_id", "inn", "dob", "taxId", "tax_id"}
    assert PII_SCRUB_KEYS == expected


# ────────────────────────────────────────────────────────────────────
# Markdown render
# ────────────────────────────────────────────────────────────────────


def test_render_includes_required_sections(alert, transaction, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=transaction,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    assert "# SAR" in md
    assert "## Filing organization" in md
    assert "## Compliance officer" in md
    assert "## Alert summary" in md
    assert "## Linked transaction" in md
    assert "Acme Custody KG" in md
    assert "auditor@orgon.test" in md
    assert "0xdeadbeef" in md


def test_render_handles_no_transaction(alert, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    assert "No on-chain transaction" in md


def test_render_handles_missing_resolution(alert, organization, officer):
    alert_no_resolution = {**alert, "resolution": None, "investigation_notes": None}
    payload = build_sar_payload(
        alert=alert_no_resolution, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    assert "_(none provided)_" in md


# ────────────────────────────────────────────────────────────────────
# Backend registry
# ────────────────────────────────────────────────────────────────────


def test_list_backends_includes_required_names():
    names = set(list_backends().keys())
    assert {"manual_export", "email", "api_v1", "dryrun"}.issubset(names)


def test_resolve_backend_explicit():
    spec = resolve_backend("dryrun")
    assert spec.name == "dryrun"


def test_resolve_backend_unknown_raises():
    with pytest.raises(ValueError, match="unknown SAR submission backend"):
        resolve_backend("nonexistent_backend")


def test_resolve_backend_falls_back_to_manual_export(env_isolated):
    spec = resolve_backend(None)
    assert spec.name == "manual_export"


def test_resolve_backend_uses_env_var(env_isolated):
    env_isolated.setenv("FINSUPERVISORY_SAR_BACKEND", "dryrun")
    spec = resolve_backend(None)
    assert spec.name == "dryrun"


# ────────────────────────────────────────────────────────────────────
# Backend behaviour
# ────────────────────────────────────────────────────────────────────


def test_manual_export_returns_prepared(alert, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    spec = resolve_backend("manual_export")
    result = spec.submit(payload, md)
    assert result["status"] == "prepared"
    assert result["external_reference"] is None


def test_dryrun_returns_prepared_no_io(alert, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    spec = resolve_backend("dryrun")
    result = spec.submit(payload, md)
    assert result["status"] == "prepared"
    assert "dryrun" in result["response_body"]


def test_email_fails_when_target_unset(env_isolated, alert, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    spec = resolve_backend("email")
    result = spec.submit(payload, md)
    assert result["status"] == "failed"
    assert "FINSUPERVISORY_SAR_EMAIL" in result["response_body"]


def test_email_fails_when_smtp_host_unset(env_isolated, alert, organization, officer):
    env_isolated.setenv("FINSUPERVISORY_SAR_EMAIL", "compliance@regulator.gov")
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    spec = resolve_backend("email")
    result = spec.submit(payload, md)
    assert result["status"] == "failed"
    assert "SMTP_HOST" in result["response_body"]


def test_api_v1_raises_not_implemented(alert, organization, officer):
    payload = build_sar_payload(
        alert=alert, transaction=None,
        organization=organization, officer=officer,
    )
    md = render_sar_markdown(payload)
    spec = resolve_backend("api_v1")
    with pytest.raises(NotImplementedError):
        spec.submit(payload, md)


# ────────────────────────────────────────────────────────────────────
# JSON serialisation contract
# ────────────────────────────────────────────────────────────────────


def test_payload_is_json_serialisable(alert, transaction, organization, officer):
    """The payload goes into a `jsonb` column — must round-trip through json.dumps."""
    payload = build_sar_payload(
        alert=alert, transaction=transaction,
        organization=organization, officer=officer,
    )
    raw = json.dumps(payload, default=str)
    again = json.loads(raw)
    assert again["schema_version"] == "orgon.sar.v1"
