"""Sumsub webhook receiver — Stories 2.4 + 2.5 (Waves 19 + 20).

Sumsub posts events to this endpoint when an applicant's review state
changes or when AML screening fires. The endpoint:

  1. Reads the raw bytes of the request body BEFORE parsing JSON
     (the HMAC must run over exact transport bytes).
  2. Verifies the X-Payload-Digest header against the configured
     `SUMSUB_WEBHOOK_SECRET`. Any mismatch → 403 immediately, payload
     never reaches DB.
  3. Routes the event to the correct table based on `externalUserId`
     prefix (set by us when we created the applicant):
        "orgon-user-<int>"  → KYC, sumsub_applicants + kyc_submissions
        "orgon-org-<uuid>"  → KYB, sumsub_kyb_applicants + kyb_submissions
     If `externalUserId` is absent we fall back to looking the
     `applicantId` up in both tables — first match wins.
  4. Maps Sumsub status → ORGON status enum per Wave 19 ADR-5.
  5. On AML events writes an `aml_alerts` row scoped to the right
     organization (user.organization_id for KYC, applicant org for KYB).
  6. Always returns 200 on successful HMAC, even if event type is
     unrecognised — Sumsub will keep retrying otherwise. We log the
     unknown type and move on.

Idempotency: events arrive with a `correlationId`. We store the
last-seen value in `last_event_id` of the matching cache row.
Duplicates yield a no-op 200.
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


KYC_PREFIX = "orgon-user-"
KYB_PREFIX = "orgon-org-"


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
    routes file."""
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


def _classify_applicant(external_user_id: str | None) -> str | None:
    """Return 'kyc' / 'kyb' / None depending on externalUserId prefix."""
    if not external_user_id:
        return None
    if external_user_id.startswith(KYC_PREFIX):
        return "kyc"
    if external_user_id.startswith(KYB_PREFIX):
        return "kyb"
    return None


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

    # 2. Verify signature.
    sig = request.headers.get("x-payload-digest", "") or request.headers.get(
        "X-Payload-Digest", ""
    )
    if not sumsub.verify_webhook_signature(raw_body, sig):
        logger.warning(
            "Sumsub webhook rejected: signature mismatch (request_id=%s)",
            request.headers.get("x-correlation-id", "?"),
        )
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 3. Parse payload — past this line we trust the bytes.
    try:
        payload: dict[str, Any] = json.loads(raw_body or b"{}")
    except json.JSONDecodeError as exc:
        logger.warning("Sumsub webhook: malformed JSON: %s", exc)
        raise HTTPException(status_code=400, detail="Malformed JSON")

    event_type = payload.get("type") or "unknown"
    applicant_id = payload.get("applicantId")
    external_user_id = payload.get("externalUserId")
    correlation_id = payload.get("correlationId")
    review_status = payload.get("reviewStatus") or payload.get("applicantStatus")
    review_result = payload.get("reviewResult") or {}

    if not applicant_id:
        logger.info("Sumsub webhook: no applicantId in payload (type=%s)", event_type)
        return {"ok": True, "ignored": "no applicantId"}

    # 4. Classify the event: KYC vs KYB.
    flow = _classify_applicant(external_user_id)

    async with pool.acquire() as conn:
        if flow is None:
            # External user id missing or with unknown prefix — fall back
            # to a dual lookup: which cache table holds this applicant?
            kyc_row = await conn.fetchrow(
                "SELECT user_id, last_event_id FROM sumsub_applicants "
                "WHERE applicant_id = $1",
                applicant_id,
            )
            if kyc_row:
                flow = "kyc"
                row = kyc_row
            else:
                kyb_row = await conn.fetchrow(
                    "SELECT organization_id, last_event_id FROM sumsub_kyb_applicants "
                    "WHERE applicant_id = $1",
                    applicant_id,
                )
                if kyb_row:
                    flow = "kyb"
                    row = kyb_row
                else:
                    logger.warning(
                        "Sumsub webhook for unknown applicant_id=%s (type=%s) — ignored",
                        applicant_id, event_type,
                    )
                    return {"ok": True, "ignored": "unknown applicant"}
        else:
            if flow == "kyc":
                row = await conn.fetchrow(
                    "SELECT user_id, last_event_id FROM sumsub_applicants "
                    "WHERE applicant_id = $1",
                    applicant_id,
                )
            else:  # kyb
                row = await conn.fetchrow(
                    "SELECT organization_id, last_event_id FROM sumsub_kyb_applicants "
                    "WHERE applicant_id = $1",
                    applicant_id,
                )

            if not row:
                logger.warning(
                    "Sumsub webhook for unknown %s applicant_id=%s — ignored",
                    flow, applicant_id,
                )
                return {"ok": True, "ignored": "unknown applicant"}

        # 5. Idempotency check.
        if correlation_id and row["last_event_id"] == correlation_id:
            logger.info(
                "Sumsub webhook duplicate event %s for applicant %s — no-op",
                correlation_id, applicant_id,
            )
            return {"ok": True, "duplicate": True}

        mapped = _map_sumsub_to_orgon_status(review_status or "", review_result)
        review_result_json = json.dumps(review_result) if review_result else None

        if flow == "kyc":
            await _apply_kyc_update(
                conn, applicant_id, row["user_id"],
                review_status, review_result_json, correlation_id, mapped,
                event_type, review_result,
            )
        else:  # kyb
            await _apply_kyb_update(
                conn, applicant_id, row["organization_id"],
                review_status, review_result_json, correlation_id, mapped,
                event_type, review_result,
            )

    logger.info(
        "Sumsub webhook processed: flow=%s type=%s applicant=%s status=%s mapped=%s",
        flow, event_type, applicant_id, review_status, mapped,
    )
    return {"ok": True, "flow": flow, "mapped_status": mapped}


# ────────────────────────────────────────────────────────────────────
# Per-flow update helpers
# ────────────────────────────────────────────────────────────────────


async def _apply_kyc_update(
    conn,
    applicant_id: str,
    user_id: int,
    review_status: str | None,
    review_result_json: str | None,
    correlation_id: str | None,
    mapped: str,
    event_type: str,
    review_result: dict,
) -> None:
    """Apply webhook update to KYC cache + kyc_submissions + AML alerts."""
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
            review_result_json,
            correlation_id,
            applicant_id,
        )

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
        review_result_json,
        applicant_id,
        user_id,
    )

    await _maybe_record_aml_alert_kyc(
        conn, applicant_id, user_id, event_type, review_result
    )


async def _apply_kyb_update(
    conn,
    applicant_id: str,
    organization_id,
    review_status: str | None,
    review_result_json: str | None,
    correlation_id: str | None,
    mapped: str,
    event_type: str,
    review_result: dict,
) -> None:
    """Apply webhook update to KYB cache + kyb_submissions + AML alerts."""
    if review_status is not None:
        await conn.execute(
            """
            UPDATE sumsub_kyb_applicants
               SET review_status = $1,
                   review_result = $2::jsonb,
                   last_event_id = $3,
                   updated_at    = now()
             WHERE applicant_id = $4
            """,
            review_status,
            review_result_json,
            correlation_id,
            applicant_id,
        )

    await conn.execute(
        """
        UPDATE kyb_submissions
           SET status = $1,
               sumsub_review_result = $2::jsonb,
               sumsub_applicant_id  = $3,
               reviewed_at = CASE
                   WHEN $1 IN ('approved', 'rejected', 'needs_resubmit')
                        THEN now()
                   ELSE reviewed_at
               END
         WHERE organization_id = $4
           AND (sumsub_applicant_id = $3 OR sumsub_applicant_id IS NULL)
        """,
        mapped,
        review_result_json,
        applicant_id,
        organization_id,
    )

    await _maybe_record_aml_alert_kyb(
        conn, applicant_id, organization_id, event_type, review_result
    )


# ────────────────────────────────────────────────────────────────────
# AML alert helpers
# ────────────────────────────────────────────────────────────────────


def _is_aml_signal(event_type: str, reject_labels: list) -> bool:
    """Sumsub emits AML signals as applicantOnHold or labels containing
    AML/SANCTIONS/PEP. ADR-3 / ADR-5 in 2-4 doc."""
    return (
        event_type.startswith("applicantOnHold")
        or any(
            "AML" in label or "SANCTIONS" in label or "PEP" in label
            for label in reject_labels
        )
    )


def _aml_severity(reject_labels: list) -> str:
    return "high" if any(
        lab in ("SANCTIONS", "AML_RISK") for lab in reject_labels
    ) else "medium"


async def _maybe_record_aml_alert_kyc(
    conn, applicant_id: str, user_id: int, event_type: str, review_result: dict
) -> None:
    reject_labels = review_result.get("rejectLabels") or []
    if not (reject_labels and _is_aml_signal(event_type, reject_labels)):
        return
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
        _aml_severity(reject_labels),
        json.dumps({
            "flow": "kyc",
            "applicant_id": applicant_id,
            "user_id": user_id,
            "labels": reject_labels,
            "review_result": review_result,
        }),
        user_id,
    )
    logger.info(
        "AML alert recorded (kyc) for user %s applicant %s labels=%s",
        user_id, applicant_id, reject_labels,
    )


async def _maybe_record_aml_alert_kyb(
    conn, applicant_id: str, organization_id, event_type: str, review_result: dict
) -> None:
    reject_labels = review_result.get("rejectLabels") or []
    if not (reject_labels and _is_aml_signal(event_type, reject_labels)):
        return
    await conn.execute(
        """
        INSERT INTO aml_alerts (organization_id, alert_type, severity, transaction_id, details)
        VALUES ($1, $2, $3, NULL, $4::jsonb)
        ON CONFLICT DO NOTHING
        """,
        organization_id,
        f"sumsub:{event_type}",
        _aml_severity(reject_labels),
        json.dumps({
            "flow": "kyb",
            "applicant_id": applicant_id,
            "organization_id": str(organization_id),
            "labels": reject_labels,
            "review_result": review_result,
        }),
    )
    logger.info(
        "AML alert recorded (kyb) for org %s applicant %s labels=%s",
        organization_id, applicant_id, reject_labels,
    )
