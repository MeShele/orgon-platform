"""KYC/KYB API endpoints — user-facing submission & admin review."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date
from backend.services.kyc_kyb_service import KycKybService
from backend.services.sumsub_service import SumsubError, SumsubService
from backend.dependencies import get_current_user, get_db_pool
from backend.rbac import require_roles

logger = logging.getLogger("orgon.api.kyc_kyb")

router = APIRouter(prefix="/api/v1/kyc-kyb", tags=["KYC/KYB"])


async def get_service(pool=Depends(get_db_pool)) -> KycKybService:
    return KycKybService(pool)


def get_sumsub_service(request: Request) -> SumsubService:
    """Dependency that yields the Sumsub service or raises 503 cleanly.

    The factory in main.py (`build_sumsub_service`) returns None when
    any of SUMSUB_APP_TOKEN / SUMSUB_SECRET_KEY / SUMSUB_WEBHOOK_SECRET
    is unset. We honour that contract here so admins know Sumsub
    integration is wired but waiting for credentials — paste env vars
    in Coolify, redeploy, KYC works.
    """
    svc = getattr(request.app.state, "sumsub", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sumsub is not configured. Set SUMSUB_APP_TOKEN, "
                   "SUMSUB_SECRET_KEY and SUMSUB_WEBHOOK_SECRET in env "
                   "and redeploy.",
        )
    return svc


# ==================== Schemas ====================

class KycSubmitRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    date_of_birth: Optional[date] = None
    nationality: Optional[str] = Field(None, max_length=2)
    address: Optional[str] = None
    phone: Optional[str] = None
    organization_id: Optional[UUID] = None
    documents: List[dict] = Field(default_factory=list)
    # documents: [{"type": "passport"|"selfie"|"proof_of_address", "file_url": "...", "file_name": "..."}]


class KybSubmitRequest(BaseModel):
    organization_id: UUID
    company_name: str = Field(..., min_length=2, max_length=255)
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    legal_address: Optional[str] = None
    country: Optional[str] = Field(None, max_length=2)
    documents: List[dict] = Field(default_factory=list)
    beneficiaries: List[dict] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    comment: Optional[str] = None
    risk_level: Optional[str] = Field(None, pattern="^(low|medium|high)$")


# ==================== KYC Endpoints ====================

@router.post("/kyc/submit", status_code=status.HTTP_201_CREATED)
async def submit_kyc(
    req: KycSubmitRequest,
    user: dict = Depends(require_roles("end_user", "company_operator", "company_admin")),
    service: KycKybService = Depends(get_service)
):
    """User submits KYC documents for verification."""
    result = await service.submit_kyc(int(user['id']), req.dict())
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/kyc/status")
async def get_kyc_status(
    user: dict = Depends(get_current_user),
    service: KycKybService = Depends(get_service)
):
    """Get current user's KYC verification status."""
    result = await service.get_kyc_status(int(user['id']))
    if not result:
        return {"status": "not_submitted"}
    return result


@router.get("/kyc/submissions")
async def list_kyc_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(require_roles("platform_admin")),
    service: KycKybService = Depends(get_service)
):
    """Admin: list all KYC submissions."""
    return await service.get_kyc_submissions(status_filter, limit, offset)


@router.put("/kyc/{submission_id}/review")
async def review_kyc(
    submission_id: UUID,
    req: ReviewRequest,
    user: dict = Depends(require_roles("platform_admin")),
    service: KycKybService = Depends(get_service)
):
    """Admin: approve or reject KYC submission."""
    result = await service.review_kyc(
        submission_id, int(user['id']),
        req.decision, req.comment, req.risk_level
    )
    if not result:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return result


# ==================== KYB Endpoints ====================

@router.post("/kyb/submit", status_code=status.HTTP_201_CREATED)
async def submit_kyb(
    req: KybSubmitRequest,
    user: dict = Depends(require_roles("company_admin")),
    service: KycKybService = Depends(get_service)
):
    """Company admin submits KYB documents for organization verification."""
    result = await service.submit_kyb(
        req.organization_id, int(user['id']), req.dict()
    )
    if "error" in result:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@router.get("/kyb/status/{org_id}")
async def get_kyb_status(
    org_id: UUID,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: KycKybService = Depends(get_service)
):
    """Get organization's KYB verification status."""
    result = await service.get_kyb_status(org_id)
    if not result:
        return {"status": "not_submitted"}
    return result


@router.get("/kyb/submissions")
async def list_kyb_submissions(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(require_roles("platform_admin")),
    service: KycKybService = Depends(get_service)
):
    """Admin: list all KYB submissions."""
    return await service.get_kyb_submissions(status_filter, limit, offset)


@router.put("/kyb/{submission_id}/review")
async def review_kyb(
    submission_id: UUID,
    req: ReviewRequest,
    user: dict = Depends(require_roles("platform_admin")),
    service: KycKybService = Depends(get_service)
):
    """Admin: approve or reject KYB submission."""
    result = await service.review_kyb(
        submission_id, int(user['id']),
        req.decision, req.comment, req.risk_level
    )
    if not result:
        raise HTTPException(status_code=404, detail="KYB submission not found")
    return result


# ════════════════════════════════════════════════════════════════════
# Sumsub WebSDK integration
# ════════════════════════════════════════════════════════════════════
#
# Story 2.4 — Sumsub KYC for individuals (Wave 19).
# See docs/stories/2-4-sumsub-kyc-architecture.md for full design.
#
# Pattern: backend creates an applicant in Sumsub keyed by our user_id,
# stores the mapping in `sumsub_applicants` table, mints a short-lived
# WebSDK token, frontend embeds the iframe. Webhook updates land in
# `routes_webhooks_sumsub.py` (Sprint 2.4.2).
#
# Disabled mode: if SUMSUB_* env vars are not set, get_sumsub_service
# raises 503 so the app boots cleanly and the frontend shows a
# "configure platform first" banner. No code rewires needed for prod —
# paste 3 env vars and redeploy.


class SumsubAccessTokenResponse(BaseModel):
    access_token: str = Field(..., description="Short-lived WebSDK token")
    expires_in: int = Field(..., description="TTL in seconds")
    applicant_id: str
    external_user_id: str
    level_name: str


class SumsubApplicantStatusResponse(BaseModel):
    applicant_id: str
    review_status: str
    review_result: Optional[dict] = None
    level_name: str
    mapped_status: str = Field(
        ..., description="ORGON-side status mapped per ADR-5 (kyc_submissions.status enum)"
    )


def _map_sumsub_to_orgon_status(review_status: str, review_result: dict | None) -> str:
    """Map Sumsub status → kyc_submissions.status. ADR-5 in 2-4 doc."""
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
            # If `clientComment` is present, retry is allowed; final RED means rejected.
            client_comment = (review_result or {}).get("clientComment")
            if client_comment:
                return "needs_resubmit"
            return "rejected"
    return "pending"


@router.post(
    "/sumsub/access-token",
    response_model=SumsubAccessTokenResponse,
    responses={503: {"description": "Sumsub not configured (env vars unset)"}},
)
async def sumsub_access_token(
    user: dict = Depends(get_current_user),
    sumsub: SumsubService = Depends(get_sumsub_service),
    pool=Depends(get_db_pool),
):
    """Mint a short-lived WebSDK token for the current user.

    Idempotent: if user already has an applicant in Sumsub, the
    existing one is reused. Cached `applicant_id` is stored in the
    `sumsub_applicants` table (Wave 19 migration 025).
    """
    external_user_id = f"orgon-user-{user['id']}"

    try:
        applicant = await sumsub.create_or_get_applicant(external_user_id)
    except SumsubError as exc:
        logger.warning("Sumsub create_or_get failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Sumsub API error",
        )

    applicant_id = applicant.get("id")
    if not applicant_id:
        raise HTTPException(
            status_code=502, detail="Sumsub returned no applicant id"
        )

    # Upsert into sumsub_applicants — fast lookup for webhook handler.
    review = applicant.get("review", {})
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO sumsub_applicants (
                user_id, applicant_id, external_user_id, level_name,
                review_status, review_result
            )
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (user_id) DO UPDATE
            SET applicant_id     = EXCLUDED.applicant_id,
                external_user_id = EXCLUDED.external_user_id,
                level_name       = EXCLUDED.level_name,
                review_status    = EXCLUDED.review_status,
                review_result    = EXCLUDED.review_result,
                updated_at       = now()
            """,
            int(user["id"]),
            applicant_id,
            external_user_id,
            sumsub.level_name,
            review.get("reviewStatus", "init"),
            None if not review else __import__("json").dumps(review),
        )

    try:
        token_resp = await sumsub.generate_access_token(external_user_id)
    except SumsubError as exc:
        logger.warning("Sumsub access-token mint failed: %s", exc)
        raise HTTPException(status_code=502, detail="Sumsub API error")

    return SumsubAccessTokenResponse(
        access_token=token_resp["token"],
        expires_in=SumsubService.DEFAULT_TOKEN_TTL,
        applicant_id=applicant_id,
        external_user_id=external_user_id,
        level_name=sumsub.level_name,
    )


@router.get(
    "/sumsub/applicant-status",
    response_model=SumsubApplicantStatusResponse,
    responses={
        404: {"description": "User has no Sumsub applicant yet"},
        503: {"description": "Sumsub not configured"},
    },
)
async def sumsub_applicant_status(
    user: dict = Depends(get_current_user),
    sumsub: SumsubService = Depends(get_sumsub_service),
    pool=Depends(get_db_pool),
):
    """Current Sumsub status for the logged-in user.

    Reads our cached row first, falls back to a live Sumsub fetch if
    we have an applicant_id but stale data. 404 if the user never
    started verification (frontend then triggers /access-token).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT applicant_id, level_name, review_status, review_result "
            "FROM sumsub_applicants WHERE user_id = $1",
            int(user["id"]),
        )

    if not row:
        raise HTTPException(
            status_code=404,
            detail="No Sumsub applicant yet — call /sumsub/access-token first",
        )

    review_result = row["review_result"]
    if isinstance(review_result, str):
        review_result = __import__("json").loads(review_result)
    mapped = _map_sumsub_to_orgon_status(row["review_status"], review_result)

    return SumsubApplicantStatusResponse(
        applicant_id=row["applicant_id"],
        review_status=row["review_status"],
        review_result=review_result,
        level_name=row["level_name"],
        mapped_status=mapped,
    )
