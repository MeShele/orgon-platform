"""KYC/KYB API endpoints — user-facing submission & admin review."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import date
from backend.services.kyc_kyb_service import KycKybService
from backend.dependencies import get_current_user, get_db_pool
from backend.rbac import require_roles

router = APIRouter(prefix="/api/v1/kyc-kyb", tags=["KYC/KYB"])


async def get_service(pool=Depends(get_db_pool)) -> KycKybService:
    return KycKybService(pool)


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
