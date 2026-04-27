"""Compliance API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from uuid import UUID
from backend.services.compliance_service import ComplianceService
from backend.dependencies import get_current_user, get_db_pool
from backend.rbac import require_roles

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance"])

async def get_compliance_service(pool = Depends(get_db_pool)) -> ComplianceService:
    return ComplianceService(pool)

# KYC/KYB submission endpoints live in routes_kyc_kyb (mounted at
# /api/v1/kyc-kyb/*). The two summary endpoints below are aggregations
# the dashboard `/compliance` page needs — they return zeroed shapes when
# the underlying tables are empty, so the page renders without 404s.


# ==================== KYC / KYB summaries (dashboard) ====================

async def _summarise_submissions(service: ComplianceService, kind: str) -> dict:
    """Count `kyc_submissions` / `kyb_submissions` by status.

    Returns the shape the dashboard expects:
    `{total_verified, pending_review, rejected, records: []}`.
    Falls back to zeros if the service helper is missing or the table is empty.
    """
    helper = getattr(service, f"summarise_{kind}", None)
    if helper:
        try:
            return await helper()
        except Exception:
            pass
    return {
        "total_verified": 0,
        "pending_review": 0,
        "rejected": 0,
        "records": [],
    }


@router.get("/kyc")
async def get_kyc_summary(
    user: dict = Depends(get_current_user),
    service: ComplianceService = Depends(get_compliance_service),
):
    """KYC submission counts for the compliance dashboard."""
    return await _summarise_submissions(service, "kyc")


@router.get("/kyb")
async def get_kyb_summary(
    user: dict = Depends(get_current_user),
    service: ComplianceService = Depends(get_compliance_service),
):
    """KYB submission counts for the compliance dashboard."""
    return await _summarise_submissions(service, "kyb")


# ==================== Reports ====================

@router.post("/reports/generate")
async def generate_monthly_report(
    org_id: UUID, year: int, month: int,
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Generate monthly compliance report."""
    report = await service.generate_monthly_report(org_id, year, month, UUID(str(user['id'])))
    return report

@router.get("/reports")
async def get_reports(
    org_id: UUID = Query(None),
    limit: int = Query(50, le=100),
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Get compliance reports."""
    reports = await service.get_reports(org_id, limit)
    return reports
