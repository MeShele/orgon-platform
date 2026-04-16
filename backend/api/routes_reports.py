"""Reports API endpoints."""
from fastapi import APIRouter, Depends
from backend.rbac import require_roles

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def get_reports(user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor"))):
    """Get available reports."""
    return {
        "reports": [
            {"id": "pnl", "title": "P&L Report", "type": "financial", "status": "available"},
            {"id": "regulatory", "title": "Regulatory Report", "type": "compliance", "status": "available"},
            {"id": "tax", "title": "Tax Report", "type": "tax", "status": "available"},
        ]
    }


@router.post("/generate")
async def generate_report(user: dict = Depends(require_roles("company_admin", "platform_admin", "company_auditor"))):
    """Generate a report."""
    return {"status": "queued", "message": "Report generation started"}
