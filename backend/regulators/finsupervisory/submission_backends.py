"""Pluggable submission backends for Финнадзор SAR (Wave 24, Story 2.9).

Each backend takes a prepared payload+rendered text and tries to deliver
it. They return a result-dict the caller persists into `sar_submissions`:

  {
    "status":             "prepared" | "sent" | "acknowledged" | "failed",
    "external_reference": "<regulator-side ID>" | None,
    "response_body":      "<error/receipt text>" | None,
  }

Default backend is `manual_export` — the operator downloads the JSON +
Markdown and submits via the regulator's web-portal/email manually.
This is the only backend that works without external service config,
and it's appropriate for early pilot tenants where the regulator hasn't
published an API.
"""

from __future__ import annotations

import csv
import io
import json as _json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("orgon.regulators.finsupervisory")


def build_external_reference(payload: Dict[str, Any]) -> str:
    """Stable, human-readable reference per submission.

    Format: `ORGON-SAR-<short_alert_id>-<unix_ts>` — short enough to
    paste into Финнадзор's reply email subject, recognisable enough
    that compliance officers can grep their inbox for "ORGON-SAR-".

    `alert_id` is the natural anchor: there's a UNIQUE constraint on
    `sar_submissions.alert_id`, so two refs colliding would only
    happen if the same alert was re-submitted (which the DB blocks
    upstream). The `unix_ts` suffix makes accidental copy-paste
    duplicates visually distinguishable.
    """
    alert_id = str(payload.get("alert", {}).get("id", "unknown"))
    # First 8 chars of the alert UUID — enough entropy to avoid
    # collisions in a single org's lifetime; short enough for an
    # email subject.
    short = alert_id.replace("-", "")[:8] or "unknown"
    return f"ORGON-SAR-{short}-{int(time.time())}"


def _payload_to_csv_bytes(payload: Dict[str, Any]) -> bytes:
    """Flatten the SAR payload to a one-row CSV.

    Compliance officers paste this into Excel rather than reading the
    JSON pretty-print. Headers are stable so a downstream Финнадзор
    template can map columns positionally.

    We don't try to render every nested field — only the load-bearing
    columns that go into the regulator's standard SAR form. Operators
    extending this can add columns; the rendered Markdown attachment
    + JSON keep the full payload for audit.
    """
    alert = payload.get("alert", {})
    tx = payload.get("transaction", {}) or {}
    org = payload.get("filing_org", {}) or payload.get("organization", {}) or {}
    officer = payload.get("officer", {}) or {}

    columns = [
        ("external_reference", payload.get("external_reference", "")),
        ("alert_id", alert.get("id", "")),
        ("alert_severity", alert.get("severity", "")),
        ("alert_status", alert.get("status", "")),
        ("alert_created_at", alert.get("created_at", "")),
        ("rule_name", alert.get("rule_name", "")),
        ("rule_type", alert.get("rule_type", "")),
        ("rule_action", alert.get("action", "")),
        ("transaction_id", tx.get("id", "")),
        ("transaction_hash", tx.get("tx_hash", "")),
        ("transaction_network", tx.get("network", "")),
        ("transaction_value", tx.get("value", "")),
        ("transaction_token", tx.get("token", "")),
        ("transaction_from", tx.get("from_address", "")),
        ("transaction_to", tx.get("to_address", "")),
        ("filing_org_name", org.get("name", "")),
        ("filing_org_inn", org.get("inn", "")),
        ("filing_org_address", org.get("address", "")),
        ("officer_name", officer.get("full_name", "")),
        ("officer_email", officer.get("email", "")),
        ("officer_phone", officer.get("phone", "")),
    ]

    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([c[0] for c in columns])
    writer.writerow([str(c[1]) if c[1] is not None else "" for c in columns])
    return buf.getvalue().encode("utf-8")


# ────────────────────────────────────────────────────────────────────
# Backend protocol + registry
# ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SubmissionBackend:
    name: str
    description: str
    submit: Callable[[Dict[str, Any], str], Dict[str, Any]]
    """Args: (payload_json, rendered_markdown) → result dict."""


def _backend_manual_export(payload: Dict[str, Any], rendered: str) -> Dict[str, Any]:
    """Persist-only — operator handles delivery offline.

    The endpoint that calls this backend stores `payload` + `rendered`
    in `sar_submissions` and exposes `/sar.json` and `/sar.md` for
    download. Status stays `prepared` until the operator manually
    confirms via the alert's `resolution` flow with the SAR-номер
    they got from Финнадзор.
    """
    return {
        "status": "prepared",
        "external_reference": None,
        "response_body": "manual_export — payload prepared for offline delivery",
    }


def _backend_email(payload: Dict[str, Any], rendered: str) -> Dict[str, Any]:
    """Send via SMTP to FINSUPERVISORY_SAR_EMAIL with full attachment set.

    Attaches three artefacts on every send:
      * `<ref>.csv` — flat row Эльдар's compliance officer pastes into
        the Финнадзор form template (one column per SAR field).
      * `<ref>.json` — full payload for machine-readable archive on
        the regulator's side.
      * `<ref>.md` — rendered narrative for human review (same text
        we put in the body, attached separately for archiving).

    Env config:
      * `FINSUPERVISORY_SAR_EMAIL` — to: address (required)
      * `FINSUPERVISORY_SAR_CC`    — cc: address (optional; the
        operator's compliance officer keeps a copy on their side)
      * `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` /
        `SMTP_FROM` — standard SMTP creds

    The `external_reference` returned here is a stable, human-readable
    ID (`ORGON-SAR-<short>-<unix_ts>`) so the operator and the
    regulator can correspond about a specific submission without
    digging through UUIDs.

    Any missing env var fails closed with `status=failed` and a clear
    message — the calling endpoint falls back to manual_export.
    """
    target = os.getenv("FINSUPERVISORY_SAR_EMAIL", "").strip()
    if not target:
        return {
            "status": "failed",
            "external_reference": None,
            "response_body": "email backend selected but FINSUPERVISORY_SAR_EMAIL is unset",
        }
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    if not smtp_host:
        return {
            "status": "failed",
            "external_reference": None,
            "response_body": "email backend selected but SMTP_HOST is unset",
        }

    # Generate the stable reference before serialising so it shows up
    # in every artifact and on every Cc copy of the email.
    external_ref = build_external_reference(payload)
    # Inject into the payload — both the CSV and the JSON pick it up.
    enriched_payload = dict(payload)
    enriched_payload["external_reference"] = external_ref

    cc = os.getenv("FINSUPERVISORY_SAR_CC", "").strip()

    # Build the email; deliberately small dependency surface — stdlib
    # only, so this works on every Python target without extra installs.
    import smtplib
    from email.message import EmailMessage

    org_name = payload.get("filing_org", {}).get("name", "unknown")
    alert = payload.get("alert", {}) or {}
    severity = (alert.get("severity") or "?").upper()
    short_alert = str(alert.get("id", "?"))[:8]

    msg = EmailMessage()
    msg["Subject"] = (
        f"[{external_ref}] SAR {severity} — {org_name} — alert {short_alert}"
    )
    msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@orgon.local"))
    msg["To"] = target
    if cc:
        msg["Cc"] = cc
    msg.set_content(
        rendered
        + "\n\n"
        + "—\n"
        + f"Submission reference: {external_ref}\n"
        + "Attachments: CSV (form-paste-friendly), JSON (full payload), "
        + "MD (this narrative).\n"
        + "Reply with the regulator-side acknowledgement reference and "
        + "we'll mark the submission as acknowledged on our side.\n"
    )

    # 1. CSV — flat row for the form template.
    msg.add_attachment(
        _payload_to_csv_bytes(enriched_payload),
        maintype="text",
        subtype="csv",
        filename=f"{external_ref}.csv",
    )
    # 2. JSON — full payload.
    msg.add_attachment(
        _json.dumps(enriched_payload, indent=2, default=str).encode("utf-8"),
        maintype="application",
        subtype="json",
        filename=f"{external_ref}.json",
    )
    # 3. Markdown narrative.
    msg.add_attachment(
        rendered.encode("utf-8"),
        maintype="text",
        subtype="markdown",
        filename=f"{external_ref}.md",
    )

    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        with smtplib.SMTP(smtp_host, port, timeout=15) as smtp:
            if os.getenv("SMTP_USER") and os.getenv("SMTP_PASSWORD"):
                smtp.starttls()
                smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            smtp.send_message(msg)
    except Exception as exc:                # pragma: no cover (network)
        logger.exception("SAR email submit failed: %s", exc)
        return {
            "status": "failed",
            "external_reference": external_ref,
            "response_body": f"SMTP error: {exc}",
        }

    recipients = target if not cc else f"{target} (cc: {cc})"
    return {
        "status": "sent",
        "external_reference": external_ref,
        "response_body": f"sent to {recipients}; ref={external_ref}",
    }


def _backend_api_v1(payload: Dict[str, Any], rendered: str) -> Dict[str, Any]:
    """Stub for future Финнадзор HTTP API.

    When the regulator publishes their API spec, swap the body with
    a `httpx.AsyncClient.post(...)` call. Until then, raising here
    is the right behaviour — the operator must not select api_v1
    until it works.
    """
    raise NotImplementedError(
        "api_v1 backend not implemented — Финнадзор has not published "
        "an SAR API spec. Use 'manual_export' or 'email' until then."
    )


def _backend_dryrun(payload: Dict[str, Any], rendered: str) -> Dict[str, Any]:
    """Logs only — never persists. Useful for tests and shadow-mode."""
    logger.info(
        "dryrun SAR: org=%s alert=%s",
        payload.get("filing_org", {}).get("name"),
        payload.get("alert", {}).get("id"),
    )
    return {
        "status": "prepared",
        "external_reference": None,
        "response_body": "dryrun — nothing was sent",
    }


_BACKENDS: Dict[str, SubmissionBackend] = {
    "manual_export": SubmissionBackend(
        name="manual_export",
        description="Persist payload + render; operator delivers offline.",
        submit=_backend_manual_export,
    ),
    "email": SubmissionBackend(
        name="email",
        description="SMTP-deliver SAR + JSON attachment to FINSUPERVISORY_SAR_EMAIL.",
        submit=_backend_email,
    ),
    "api_v1": SubmissionBackend(
        name="api_v1",
        description="Reserved for future Финнадзор HTTP API.",
        submit=_backend_api_v1,
    ),
    "dryrun": SubmissionBackend(
        name="dryrun",
        description="Logs only — for tests / shadow validation.",
        submit=_backend_dryrun,
    ),
}


def list_backends() -> Dict[str, SubmissionBackend]:
    """Public copy of the registry — used by tests and the (future) admin UI."""
    return dict(_BACKENDS)


def describe_active_config() -> Dict[str, Any]:
    """Snapshot of the SAR submission environment.

    Surfaced via `GET /api/v1/compliance/sar/config` so the dashboard
    can render an honest "current SAR mode" indicator on
    `/compliance` — the compliance officer needs to know at a glance
    which channel SAR submissions are flowing through.

    Returns the *effective* backend (the one `resolve_backend(None)`
    would pick) plus the readiness of supporting env vars.

    Doesn't actually send anything. No secrets in the response —
    `*_email` are present (they're targets, not credentials), but
    SMTP creds are surfaced only as booleans.
    """
    backend = (os.getenv("FINSUPERVISORY_SAR_BACKEND") or "manual_export").strip().lower()
    smtp_host = bool(os.getenv("SMTP_HOST", "").strip())
    sar_email = os.getenv("FINSUPERVISORY_SAR_EMAIL", "").strip() or None
    sar_cc = os.getenv("FINSUPERVISORY_SAR_CC", "").strip() or None

    missing: list[str] = []
    if backend == "email":
        if not sar_email:
            missing.append("FINSUPERVISORY_SAR_EMAIL")
        if not smtp_host:
            missing.append("SMTP_HOST")
    elif backend == "api_v1":
        missing.append("api_v1 is reserved — Финнадзор has not published a SAR API spec yet")

    ready = (backend in _BACKENDS) and not missing
    return {
        "backend": backend if backend in _BACKENDS else "manual_export",
        "ready": ready,
        "missing_env": missing,
        "target_email": sar_email,
        "cc_email": sar_cc,
        "smtp_configured": smtp_host,
        "known_backends": sorted(_BACKENDS),
    }


def resolve_backend(name: Optional[str] = None) -> SubmissionBackend:
    """Resolve a backend by name or env-default.

    Order:
      1. explicit `name` argument
      2. `FINSUPERVISORY_SAR_BACKEND` env var
      3. `manual_export` fallback (always available)
    """
    chosen = (name or os.getenv("FINSUPERVISORY_SAR_BACKEND") or "").strip().lower()
    if not chosen:
        chosen = "manual_export"
    spec = _BACKENDS.get(chosen)
    if spec is None:
        raise ValueError(
            f"unknown SAR submission backend '{chosen}'. "
            f"Available: {sorted(_BACKENDS)}"
        )
    return spec
