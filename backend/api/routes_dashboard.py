from fastapi import Depends
from backend.rbac import require_any_auth
"""Dashboard aggregation endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(user: dict = Depends(require_any_auth())):
    """
    Get aggregated dashboard statistics.

    Returns:
    - total_wallets: Number of wallets
    - total_balance_usd: Estimated total balance in USD
    - transactions_24h: Transaction count in last 24 hours
    - pending_signatures: Number of pending signatures
    - networks_active: Number of active networks
    - cache_stats: Cache performance statistics
    - last_sync: Last synchronization timestamp
    """
    from backend.main import get_dashboard_service
    service = get_dashboard_service()
    return await service.get_stats()


@router.get("/recent")
async def get_recent_activity(user: dict = Depends(require_any_auth()), limit: int = 20):
    """
    Get recent activity feed.

    Combines activities from:
    - Recent transactions
    - Signature events
    - Wallet changes

    Query parameters:
    - limit: Maximum number of activities (default: 20)

    Returns:
        List of activity dicts sorted by timestamp DESC
    """
    from backend.main import get_dashboard_service
    service = get_dashboard_service()
    return await service.get_recent_activity(limit=limit)


@router.get("/alerts")
async def get_alerts(user: dict = Depends(require_any_auth())):
    """
    Get system alerts and warnings.

    Returns:
    - pending_signatures: Count and list
    - failed_transactions: Count and list
    - low_balances: Wallets with low balance
    - sync_issues: Synchronization problems
    - cache_warnings: Cache issues
    """
    from backend.main import get_dashboard_service
    service = get_dashboard_service()
    return await service.get_alerts()


@router.get("/overview")
async def overview(user: dict = Depends(require_any_auth())):
    """
    Get aggregated dashboard data.

    ℹ️ LEGACY: Consider using /stats, /recent, and /alerts instead for more granular data.
    """
    from backend.main import get_balance_service
    service = get_balance_service()
    return await service.get_dashboard_overview()


@router.get("/balance-history")
async def balance_history(user: dict = Depends(require_any_auth()), days: int = 7):
    """
    Get balance history for charts.

    Query parameters:
    - days: Number of days to include (default: 7)
    """
    from backend.main import get_balance_service
    service = get_balance_service()
    return await service.get_balance_history(days=days)
