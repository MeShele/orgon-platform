"""API routes for analytics and charts."""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import Optional
from datetime import datetime

from backend.services.analytics_service import AnalyticsService
from backend.rbac import require_roles

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# Dependency injection helper
def get_analytics_service(request: Request) -> AnalyticsService:
    """Get AnalyticsService from app state."""
    return request.app.state.analytics_service


@router.get("/balance-history")
async def get_balance_history(
    days: int = Query(30, ge=1, le=365),
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get balance history over time.
    
    Query parameters:
    - days: Number of days to look back (1-365, default: 30)
    """
    try:
        data = await service.get_balance_history(days)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transaction-volume")
async def get_transaction_volume(
    network: Optional[str] = None,
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get transaction volume grouped by network.
    
    Query parameters:
    - network: Optional network filter
    """
    try:
        data = await service.get_transaction_volume(network)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/token-distribution")
async def get_token_distribution(user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)):
    """Get token distribution (pie chart data)."""
    try:
        data = await service.get_token_distribution()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signature-stats")
async def get_signature_stats(user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)):
    """Get signature completion statistics."""
    try:
        data = await service.get_signature_stats()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-trends")
async def get_daily_trends(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get daily transaction trends.
    
    Query parameters:
    - from_date: Start date (ISO format, default: 30 days ago)
    - to_date: End date (ISO format, default: today)
    """
    try:
        
        # Parse dates if provided
        from_dt = datetime.fromisoformat(from_date) if from_date else None
        to_dt = datetime.fromisoformat(to_date) if to_date else None
        
        data = await service.get_daily_trends(from_dt, to_dt)
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/network-activity")
async def get_network_activity(user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)):
    """Get network activity summary."""
    try:
        data = await service.get_network_activity()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallet-summary")
async def get_wallet_summary(user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)):
    """Get wallet summary statistics."""
    try:
        data = await service.get_wallet_summary()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_analytics_overview(user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AnalyticsService = Depends(get_analytics_service)):
    """
    Get analytics overview (all stats in one call).
    
    Returns:
    - balance_history (7 days)
    - transaction_volume
    - token_distribution (top 10)
    - signature_stats
    - wallet_summary
    """
    try:
        
        # Fetch all data in parallel would be better, but for simplicity:
        balance_history = await service.get_balance_history(7)
        tx_volume = await service.get_transaction_volume()
        token_dist = await service.get_token_distribution()
        sig_stats = await service.get_signature_stats()
        wallet_summary = await service.get_wallet_summary()
        
        return {
            "balance_history": balance_history,
            "transaction_volume": tx_volume[:5],  # Top 5 networks
            "token_distribution": token_dist[:10],  # Top 10 tokens
            "signature_stats": sig_stats,
            "wallet_summary": wallet_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
