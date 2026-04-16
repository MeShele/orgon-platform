"""Compliance API compatibility routes (non-v1 prefix).

Frontend may call /api/compliance/kyc and /api/compliance/kyb.
The real compliance routes live at /api/v1/compliance/* and /api/v1/kyc-kyb/*.
These endpoints return mock data so the compliance page works.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/compliance", tags=["Compliance (compat)"])


@router.get("/kyc")
async def get_kyc_compat():
    """Return mock KYC status overview."""
    return {
        "total_verified": 0,
        "pending_review": 0,
        "rejected": 0,
        "records": [],
    }


@router.get("/kyb")
async def get_kyb_compat():
    """Return mock KYB status overview."""
    return {
        "total_verified": 0,
        "pending_review": 0,
        "rejected": 0,
        "records": [],
    }
