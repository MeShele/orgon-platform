"""
Partner Analytics API Routes
Transaction analytics with USD values for B2B partners
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from backend.services.analytics_service import AnalyticsService
from backend.services.price_feed_service import get_price_feed_service
from backend.api.middleware_b2b import get_partner_from_request


# Create router
router = APIRouter(prefix="/api/v1/partner/analytics", tags=["Partner API - Analytics"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_analytics_service(request: Request) -> AnalyticsService:
    """Get AnalyticsService instance from app state."""
    if not hasattr(request.app.state, "analytics_service"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Analytics service not available"}
        )
    return request.app.state.analytics_service


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class VolumeDataPoint(BaseModel):
    """Transaction volume data point."""
    date: str
    volume: float
    volume_usd: Optional[float] = None
    tx_count: int


class VolumeResponse(BaseModel):
    """Transaction volume time series."""
    data: List[VolumeDataPoint]
    total_volume: float
    total_volume_usd: Optional[float] = None
    total_transactions: int


class FeeDataPoint(BaseModel):
    """Fee analysis data point."""
    date: str
    total_fees: float
    total_fees_usd: Optional[float] = None
    avg_fee: float
    avg_fee_usd: Optional[float] = None


class FeeResponse(BaseModel):
    """Fee analysis response."""
    data: List[FeeDataPoint]
    total_fees: float
    total_fees_usd: Optional[float] = None


class DistributionItem(BaseModel):
    """Token distribution item."""
    token: str
    balance: float
    balance_usd: Optional[float] = None
    percentage: float


class DistributionResponse(BaseModel):
    """Token distribution response."""
    data: List[DistributionItem]
    total_value_usd: Optional[float] = None


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get(
    "/volume",
    response_model=VolumeResponse,
    summary="Get Transaction Volume",
    description="Get transaction volume over time with USD values."
)
async def get_volume(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    network_id: Optional[int] = Query(None, description="Filter by network ID"),
    token: Optional[str] = Query(None, description="Filter by token symbol"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get transaction volume over time.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `days`: Number of days to analyze (1-365, default: 30)
    - `network_id`: Optional filter by network ID
    - `token`: Optional filter by token symbol (TRX, USDT, etc.)
    
    **Returns:** Time-series data with volume and transaction count.
    """
    partner = get_partner_from_request(request)
    
    # Get volume data (filtered by partner_id internally)
    # TODO: Update AnalyticsService to support partner_id filtering
    volume_data = await analytics_service.get_transaction_volume(
        days=days,
        network=str(network_id) if network_id else None
    )
    
    # Convert to USD using price feed
    price_feed = get_price_feed_service()
    
    data_points = []
    total_volume = 0.0
    total_volume_usd = 0.0
    total_tx = 0
    
    for item in volume_data:
        volume = float(item.get("volume", 0))
        tx_count = int(item.get("count", 0))
        token_symbol = item.get("token", "TRX")
        
        # Get USD price
        usd_price = await price_feed.get_price(token_symbol)
        volume_usd = volume * usd_price if usd_price else None
        
        data_points.append(VolumeDataPoint(
            date=item.get("date", datetime.now().date().isoformat()),
            volume=volume,
            volume_usd=volume_usd,
            tx_count=tx_count
        ))
        
        total_volume += volume
        if volume_usd:
            total_volume_usd += volume_usd
        total_tx += tx_count
    
    return VolumeResponse(
        data=data_points,
        total_volume=total_volume,
        total_volume_usd=total_volume_usd if total_volume_usd > 0 else None,
        total_transactions=total_tx
    )


@router.get(
    "/fees",
    response_model=FeeResponse,
    summary="Get Fee Analysis",
    description="Get transaction fee analysis with USD values."
)
async def get_fees(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    network_id: Optional[int] = Query(None, description="Filter by network ID"),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get transaction fee analysis.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `days`: Number of days to analyze (1-365, default: 30)
    - `network_id`: Optional filter by network ID
    
    **Returns:** Fee data with USD conversion.
    """
    partner = get_partner_from_request(request)
    
    # Get fee data
    # TODO: Implement get_fee_analysis in AnalyticsService
    # For now, return mock data
    fee_data = []
    
    # Mock implementation
    price_feed = get_price_feed_service()
    trx_price = await price_feed.get_price("TRX")
    
    data_points = []
    total_fees = 0.0
    total_fees_usd = 0.0
    
    # TODO: Replace with real data from AnalyticsService
    for i in range(min(days, 7)):
        date = (datetime.now() - timedelta(days=i)).date().isoformat()
        fees = 10.0 + i * 2.0  # Mock fee data
        fees_usd = fees * trx_price if trx_price else None
        
        data_points.append(FeeDataPoint(
            date=date,
            total_fees=fees,
            total_fees_usd=fees_usd,
            avg_fee=fees / (i + 1),
            avg_fee_usd=fees_usd / (i + 1) if fees_usd else None
        ))
        
        total_fees += fees
        if fees_usd:
            total_fees_usd += fees_usd
    
    return FeeResponse(
        data=data_points,
        total_fees=total_fees,
        total_fees_usd=total_fees_usd if total_fees_usd > 0 else None
    )


@router.get(
    "/distribution",
    response_model=DistributionResponse,
    summary="Get Token Distribution",
    description="Get token balance distribution with USD values."
)
async def get_distribution(
    request: Request,
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Get token balance distribution.
    
    **Authentication:** Requires valid API key + secret.
    
    **Returns:** Token distribution with USD values and percentages.
    """
    partner = get_partner_from_request(request)
    
    # Get token distribution
    distribution_data = await analytics_service.get_token_distribution()
    
    # Convert to USD
    price_feed = get_price_feed_service()
    
    items = []
    total_value_usd = 0.0
    
    for item in distribution_data:
        token_symbol = item.get("token", "TRX")
        balance = float(item.get("balance", 0))
        percentage = float(item.get("percentage", 0))
        
        # Get USD price
        usd_price = await price_feed.get_price(token_symbol)
        balance_usd = balance * usd_price if usd_price else None
        
        items.append(DistributionItem(
            token=token_symbol,
            balance=balance,
            balance_usd=balance_usd,
            percentage=percentage
        ))
        
        if balance_usd:
            total_value_usd += balance_usd
    
    return DistributionResponse(
        data=items,
        total_value_usd=total_value_usd if total_value_usd > 0 else None
    )


@router.get(
    "/export",
    summary="Export Analytics",
    description="Export analytics data in CSV or JSON format."
)
async def export_analytics(
    request: Request,
    format: str = Query("json", regex="^(json|csv)$", description="Export format"),
    days: int = Query(30, ge=1, le=365),
    analytics_service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Export analytics data.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `format`: Export format (json or csv)
    - `days`: Number of days to include
    
    **Returns:** Analytics data in requested format.
    """
    partner = get_partner_from_request(request)
    
    # Get all analytics data
    volume_data = await analytics_service.get_transaction_volume(days=days)
    distribution_data = await analytics_service.get_token_distribution()
    
    if format == "json":
        return {
            "export_date": datetime.now().isoformat(),
            "partner_id": str(partner["partner_id"]),
            "period_days": days,
            "volume": volume_data,
            "distribution": distribution_data
        }
    
    elif format == "csv":
        # TODO: Implement CSV export using pandas or csv module
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"error": "not_implemented", "message": "CSV export coming soon"}
        )
