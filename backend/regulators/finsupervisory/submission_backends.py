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

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("orgon.regulators.finsupervisory")


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
    """Send via SMTP to FINSUPERVISORY_SAR_EMAIL.

    SMTP credentials come from the existing `SMTP_*` env vars
    (host/port/user/password/from). When any of them is unset we treat
    the attempt as failed and let the operator fall back to manual_export.
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

    # Build the email; deliberately small dependency surface — stdlib
    # only, so this works on every Python target without extra installs.
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg["Subject"] = (
        f"SAR — {payload.get('filing_org', {}).get('name', 'unknown')} "
        f"— alert {payload.get('alert', {}).get('id')}"
    )
    msg["From"] = os.getenv("SMTP_FROM", os.getenv("SMTP_USER", "noreply@orgon.local"))
    msg["To"] = target
    msg.set_content(rendered)
    msg.add_attachment(
        __import__("json").dumps(payload, indent=2, default=str).encode("utf-8"),
        maintype="application",
        subtype="json",
        filename=f"sar-{payload.get('alert', {}).get('id', 'unknown')}.json",
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
            "external_reference": None,
            "response_body": f"SMTP error: {exc}",
        }

    # Email accepted by SMTP server — that's all we know. Operator
    # later edits the row to status='acknowledged' once the regulator
    # confirms receipt and assigns a reference.
    return {
        "status": "sent",
        "external_reference": None,
        "response_body": f"sent to {target}",
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
