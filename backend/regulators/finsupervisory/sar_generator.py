"""SAR (Suspicious Activity Report) payload generator for Финнадзор
(Wave 24, Story 2.9).

Pure functions only — given an alert + its linked transaction (if any)
+ the filing org info + the officer who is submitting, return:

  - `payload_json`: structured dict suitable for POST/email body
  - `rendered_markdown`: human-readable preview that mirrors the JSON

PII redaction matches Wave 21 frontend: document IDs are scrubbed,
identity fields (name/email/phone) stay because the regulator needs
the actual subject of the report. Sensitive document copies are
attached separately as supporting documents (out of scope for Wave 24).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Mirror of frontend `PII_SCRUB_KEYS` (frontend/src/lib/amlAlerts.ts).
# The two lists must stay in sync — backend tests assert keys match.
PII_SCRUB_KEYS = frozenset({
    "passport_number",
    "national_id",
    "inn",
    "dob",
    "taxId",
    "tax_id",
})


def _scrub_pii(value: Any) -> Any:
    """Recursively replace PII-coded keys with `***hidden***`."""
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            if k in PII_SCRUB_KEYS:
                out[k] = "***hidden***"
            else:
                out[k] = _scrub_pii(v)
        return out
    if isinstance(value, list):
        return [_scrub_pii(v) for v in value]
    return value


def build_sar_payload(
    *,
    alert: Dict[str, Any],
    transaction: Optional[Dict[str, Any]],
    organization: Dict[str, Any],
    officer: Dict[str, Any],
    filed_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Assemble the SAR payload from the four context dicts.

    Args:
        alert: row from `aml_alerts` (id/alert_type/severity/description/
            details/resolution/investigation_notes).
        transaction: row from `transactions` if alert.transaction_id was
            set; None otherwise (Sumsub-only KYC alerts).
        organization: row from `organizations` (name, registration_no,
            legal_address, contact_email, jurisdiction).
        officer: dict with at minimum {id, email, full_name} of the
            submitting compliance officer.
        filed_at: override timestamp for tests; defaults to now(UTC).

    Returns:
        JSON-serialisable dict.
    """
    filed_at = filed_at or datetime.now(timezone.utc)
    details_redacted = _scrub_pii(alert.get("details") or {})

    return {
        "schema_version": "orgon.sar.v1",
        "filed_at": filed_at.isoformat(),
        "filing_org": {
            "id": str(organization.get("id", "")),
            "name": organization.get("name") or "",
            "registration_no": organization.get("registration_number"),
            "legal_address": organization.get("legal_address"),
            "contact_email": organization.get("contact_email"),
            "jurisdiction": organization.get("country") or organization.get("jurisdiction"),
        },
        "officer": {
            "id": officer.get("id"),
            "name": officer.get("full_name") or officer.get("name") or "",
            "email": officer.get("email") or "",
            "phone": officer.get("phone"),
        },
        "alert": {
            "id": str(alert.get("id", "")),
            "alert_type": alert.get("alert_type"),
            "severity": alert.get("severity"),
            "description": alert.get("description"),
            "created_at": _format_dt(alert.get("created_at")),
            "details_redacted": details_redacted,
            "resolution": alert.get("resolution"),
            "investigation_notes": alert.get("investigation_notes"),
        },
        "transaction": _format_transaction(transaction),
        "supporting_documents": [],
    }


def _format_transaction(tx: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if tx is None:
        return None
    return {
        "id": str(tx.get("id", "")) or None,
        "unid": tx.get("unid"),
        "tx_hash": tx.get("tx_hash"),
        "from_address": tx.get("from_address"),
        "to_address": tx.get("to_address") or tx.get("to_addr"),
        "value": str(tx.get("value", "")) if tx.get("value") is not None else None,
        "amount": str(tx.get("amount", "")) if tx.get("amount") is not None else None,
        "token": tx.get("token"),
        "network": tx.get("network"),
        "status": tx.get("status"),
        "created_at": _format_dt(tx.get("created_at")),
    }


def _format_dt(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


# ────────────────────────────────────────────────────────────────────
# Markdown rendering
# ────────────────────────────────────────────────────────────────────


def render_sar_markdown(payload: Dict[str, Any]) -> str:
    """Render `build_sar_payload()` output as a human-readable Markdown
    document. Used both for the SAR-preview drawer and the email body.

    Output is stable enough that operators can paste it into a Финнадзор
    portal-form 1:1 if no API integration exists.
    """
    fo = payload["filing_org"]
    of = payload["officer"]
    al = payload["alert"]
    tx = payload.get("transaction")

    lines = [
        f"# SAR — Suspicious Activity Report",
        "",
        f"**Filed at:** {payload['filed_at']}  ",
        f"**Schema:** {payload['schema_version']}",
        "",
        "## Filing organization",
        "",
        f"- **Name:** {fo.get('name') or '—'}",
        f"- **Registration №:** {fo.get('registration_no') or '—'}",
        f"- **Jurisdiction:** {fo.get('jurisdiction') or '—'}",
        f"- **Legal address:** {fo.get('legal_address') or '—'}",
        f"- **Contact:** {fo.get('contact_email') or '—'}",
        "",
        "## Compliance officer",
        "",
        f"- **Name:** {of.get('name') or '—'}",
        f"- **Email:** {of.get('email') or '—'}",
        f"- **Phone:** {of.get('phone') or '—'}",
        "",
        "## Alert summary",
        "",
        f"- **Alert ID:** `{al.get('id')}`",
        f"- **Type:** {al.get('alert_type') or '—'}",
        f"- **Severity:** {al.get('severity') or '—'}",
        f"- **Detected at:** {al.get('created_at') or '—'}",
        "",
        "### Description",
        "",
        al.get("description") or "_(none)_",
        "",
        "### Officer reasoning / resolution",
        "",
        al.get("resolution") or "_(none provided)_",
        "",
    ]

    if al.get("investigation_notes"):
        lines += [
            "### Investigation notes",
            "",
            "```",
            al["investigation_notes"],
            "```",
            "",
        ]

    if tx:
        lines += [
            "## Linked transaction",
            "",
            f"- **UNID:** `{tx.get('unid') or '—'}`",
            f"- **Tx hash:** `{tx.get('tx_hash') or '—'}`",
            f"- **From → To:** `{tx.get('from_address') or '—'}` → `{tx.get('to_address') or '—'}`",
            f"- **Value:** {tx.get('value') or tx.get('amount') or '—'} {tx.get('token') or ''}",
            f"- **Network:** {tx.get('network') or '—'}",
            f"- **Status:** {tx.get('status') or '—'}",
            f"- **Created at:** {tx.get('created_at') or '—'}",
            "",
        ]
    else:
        lines += [
            "## Linked transaction",
            "",
            "_No on-chain transaction is linked to this alert (KYC/applicant-level event)._",
            "",
        ]

    lines += [
        "## Supporting documents",
        "",
        "_Submitted separately via secure channel._",
        "",
        "---",
        "",
        "_Generated by ORGON compliance pipeline._",
    ]
    return "\n".join(lines)
