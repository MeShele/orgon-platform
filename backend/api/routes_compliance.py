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

# ==================== KYC ====================

@router.post("/kyc", status_code=status.HTTP_201_CREATED)
async def create_kyc(
    org_id: UUID, customer_name: str, customer_email: str,
    id_type: str, id_number: str,
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Create KYC record."""
    record = await service.create_kyc_record(
        org_id, customer_name, customer_email, id_type, id_number, UUID(str(user['id']))
    )
    return record

@router.get("/kyc")
async def get_kyc_records(
    org_id: UUID = Query(...),
    status: Optional[str] = None,
    limit: int = Query(50, le=100),
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Get KYC records."""
    records = await service.get_kyc_records(org_id, status, limit)
    return records

@router.put("/kyc/{kyc_id}/status")
async def update_kyc_status(
    kyc_id: UUID, status: str, risk_level: Optional[str] = None,
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Approve/reject KYC."""
    record = await service.update_kyc_status(kyc_id, status, UUID(str(user['id'])), risk_level)
    if not record:
        raise HTTPException(status_code=404, detail="KYC record not found")
    return record

# ==================== AML ====================

@router.get("/aml/alerts")
async def get_aml_alerts(
    org_id: UUID = Query(...),
    status: Optional[str] = None,
    limit: int = Query(50, le=100),
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Get AML alerts."""
    alerts = await service.get_aml_alerts(org_id, status, limit)
    return alerts

@router.put("/aml/alerts/{alert_id}/resolve")
async def resolve_aml_alert(
    alert_id: UUID, resolution: str,
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Resolve AML alert."""
    alert = await service.update_aml_alert_status(
        alert_id, "resolved", resolution, UUID(str(user['id']))
    )
    if not alert:
        raise HTTPException(status_code=404, detail="AML alert not found")
    return alert

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
    org_id: UUID = Query(...),
    limit: int = Query(50, le=100),
    user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor")),
    service: ComplianceService = Depends(get_compliance_service)
):
    """Get compliance reports."""
    reports = await service.get_reports(org_id, limit)
    return reports
