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

# KYC and AML endpoints are served by routes_kyc_kyb (mounted at /api/v1/kyc-kyb/*).
# This module keeps only the report-generation endpoints, which are unique to it.

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
