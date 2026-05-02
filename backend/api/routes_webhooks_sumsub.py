"""Sumsub webhook receiver — Story 2.4 (Wave 19).

Sumsub posts events to this endpoint when an applicant's review state
changes or when AML screening fires. The endpoint:

  1. Reads the raw bytes of the request body BEFORE parsing JSON
     (the HMAC must run over exact transport bytes).
  2. Verifies the X-Payload-Digest header against the configured
     `SUMSUB_WEBHOOK_SECRET`. Any mismatch → 403 immediately, payload
     never reaches DB.
  3. Maps Sumsub status → ORGON `kyc_submissions.status` per ADR-5
     in docs/stories/2-4-sumsub-kyc-architecture.md.
  4. Updates `sumsub_applicants` (cache) and `kyc_submissions`
     (canonical KYC record).
  5. On AML events (`applicantOnHold` with reason, or any
     `aml_alert*` event subtype), writes an `aml_alerts` row.
  6. Always returns 200 on successful HMAC, even if event type is
     unrecognised — Sumsub will keep retrying otherwise. We log the
     unknown type and move on.

Idempotency (ADR-10): events arrive with a `correlationId`. We store
last-seen value in `sumsub_applicants.last_event_id`. Duplicate
deliveries are detected and yield a no-op 200.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.dependencies import get_db_pool
from backend.services.sumsub_service import SumsubService

logger = logging.getLogger("orgon.api.webhooks.sumsub")

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


def _get_sumsub_service(request: Request) -> SumsubService:
    """Same contract as `routes_kyc_kyb.get_sumsub_service` — 503 if
    unconfigured. Inlined here to avoid a circular import.
    """
    svc = getattr(request.app.state, "sumsub", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sumsub is not configured",
        )
    return svc


def _map_sumsub_to_orgon_status(review_status: str, review_result: dict | None) -> str:
    """Mirrors routes_kyc_kyb._map_sumsub_to_orgon_status. Duplicated
    here to keep the webhook handler independent of the user-facing
    routes file (avoids a one-way circular import path)."""
    rs = (review_status or "").lower()
    if rs == "init":
        return "not_started"
    if rs in ("pending", "prechecked", "queued"):
        return "pending"
    if rs == "onhold":
        return "manual_review"
    if rs == "completed":
        answer = (review_result or {}).get("reviewAnswer")
        if answer == "GREEN":
            return "approved"
        if answer == "RED":
            client_comment = (review_result or {}).get("clientComment")
            if client_comment:
                return "needs_resubmit"
            return "rejected"
    return "pending"


@router.post(
    "/sumsub",
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Invalid HMAC signature"},
        503: {"description": "Sumsub not configured"},
    },
)
async def sumsub_webhook(
    request: Request,
    sumsub: SumsubService = Depends(_get_sumsub_service),
    pool=Depends(get_db_pool),
):
    """Receive a single Sumsub webhook event."""

    # 1. Read raw body BEFORE parsing — needed for HMAC over transport bytes.
    raw_body = await request.body()

    # 2. Verify signature. Sumsub uses lowercase header name in docs,
    #    httpx/Starlette normalises to lower already, but we stay flexible.
    sig = request.headers.get("x-payload-digest", "") or request.headers.get(
        "X-Payload-Digest", ""
    )
    if not sumsub.verify_webhook_signature(raw_body, sig):
        # Don't log payload — could contain PII.
        logger.warning(
            "Sumsub webhook rejected: signature mismatch (request_id=%s)",
            request.headers.get("x-correlation-id", "?"),
        )
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 3. Parse payload. Past this line we trust the body — HMAC verified.
    try:
        payload: dict[str, Any] = json.loads(raw_body or b"{}")
    except json.JSONDecodeError as exc:
        logger.warning("Sumsub webhook: malformed JSON: %s", exc)
        raise HTTPException(status_code=400, detail="Malformed JSON")

    event_type = payload.get("type") or "unknown"
    applicant_id = payload.get("applicantId")
    correlation_id = payload.get("correlationId")
    review_status = payload.get("reviewStatus") or payload.get("applicantStatus")
    review_result = payload.get("reviewResult") or {}

    if not applicant_id:
        logger.info("Sumsub webhook: no applicantId in payload (type=%s)", event_type)
        return {"ok": True, "ignored": "no applicantId"}

    # 4. Idempotency check — same correlationId → no-op success.
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT user_id, last_event_id, review_status FROM sumsub_applicants "
            "WHERE applicant_id = $1",
            applicant_id,
        )
        if existing and correlation_id and existing["last_event_id"] == correlation_id:
            logger.info(
                "Sumsub webhook duplicate event %s for applicant %s — no-op",
                correlation_id, applicant_id,
            )
            return {"ok": True, "duplicate": True}

        if not existing:
            # Webhook for an applicant we never created — could be a stray
            # cross-environment event. Log and accept (200) so Sumsub stops
            # retrying; do not write to our DB.
            logger.warning(
                "Sumsub webhook for unknown applicant_id=%s (type=%s) — ignored",
                applicant_id, event_type,
            )
            return {"ok": True, "ignored": "unknown applicant"}

        user_id = existing["user_id"]

        # 5. Update sumsub_applicants cache.
        if review_status is not None:
            await conn.execute(
                """
                UPDATE sumsub_applicants
                   SET review_status = $1,
                       review_result = $2::jsonb,
                       last_event_id = $3,
                       updated_at    = now()
                 WHERE applicant_id = $4
                """,
                review_status,
                json.dumps(review_result) if review_result else None,
                correlation_id,
                applicant_id,
            )

        # 6. Mirror status into kyc_submissions (last submission for that
        #    user). For users who only ever started Sumsub flow without
        #    going through the legacy `submit_kyc` path, this UPDATE
        #    affects 0 rows — and that's fine.
        mapped = _map_sumsub_to_orgon_status(review_status or "", review_result)
        await conn.execute(
            """
            UPDATE kyc_submissions
               SET status = $1,
                   sumsub_review_result = $2::jsonb,
                   sumsub_applicant_id  = $3,
                   reviewed_at = CASE
                       WHEN $1 IN ('approved', 'rejected', 'needs_resubmit')
                            THEN now()
                       ELSE reviewed_at
                   END
             WHERE user_id = $4
               AND (sumsub_applicant_id = $3 OR sumsub_applicant_id IS NULL)
            """,
            mapped,
            json.dumps(review_result) if review_result else None,
            applicant_id,
            user_id,
        )

        # 7. AML event handling — minimum viable. Story 2.6 will expand.
        # Sumsub emits AML signals as `applicantWorkflowCompleted`,
        # `applicantOnHold` (with reason), or screening hits in
        # reviewResult.rejectLabels. For now we record any RED/onHold
        # transition with rejectLabels as an aml_alerts entry.
        reject_labels = review_result.get("rejectLabels") or []
        is_aml_signal = (
            event_type.startswith("applicantOnHold")
            or any("AML" in label or "SANCTIONS" in label or "PEP" in label
                   for label in reject_labels)
        )
        if is_aml_signal and reject_labels:
            severity = "high" if any(
                lab in ("SANCTIONS", "AML_RISK") for lab in reject_labels
            ) else "medium"
            await conn.execute(
                """
                INSERT INTO aml_alerts (organization_id, alert_type, severity, transaction_id, details)
                SELECT u.organization_id, $1, $2, NULL, $3::jsonb
                  FROM users u
                 WHERE u.id = $4
                   AND u.organization_id IS NOT NULL
                ON CONFLICT DO NOTHING
                """,
                f"sumsub:{event_type}",
                severity,
                json.dumps({
                    "applicant_id": applicant_id,
                    "labels": reject_labels,
                    "review_result": review_result,
                }),
                user_id,
            )
            logger.info(
                "AML alert recorded for user %s (applicant %s, labels=%s)",
                user_id, applicant_id, reject_labels,
            )

    logger.info(
        "Sumsub webhook processed: type=%s applicant=%s status=%s mapped=%s",
        event_type, applicant_id, review_status, mapped,
    )
    return {"ok": True, "mapped_status": mapped}
