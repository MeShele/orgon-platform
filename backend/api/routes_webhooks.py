"""
Webhook Management API Routes
Partner webhook configuration and event log endpoints
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, HttpUrl
from datetime import datetime

from backend.services.webhook_service import WebhookService
from backend.api.middleware_b2b import get_partner_from_request


# Create router
router = APIRouter(prefix="/api/v1/partner/webhooks", tags=["Partner API - Webhooks"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_webhook_service(request: Request) -> WebhookService:
    """Get WebhookService instance from app state."""
    if not hasattr(request.app.state, "webhook_service"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Webhook service not available"}
        )
    return request.app.state.webhook_service


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class WebhookRegisterRequest(BaseModel):
    """Request to register a webhook URL."""
    url: HttpUrl
    event_types: List[str]  # e.g., ["wallet.*", "transaction.confirmed"]
    description: Optional[str] = None
    secret: Optional[str] = None  # Optional custom HMAC secret


class WebhookResponse(BaseModel):
    """Webhook configuration response."""
    id: int
    url: str
    event_types: List[str]
    description: Optional[str]
    is_active: bool
    success_count: int
    failure_count: int
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    """List of webhook configurations."""
    webhooks: List[WebhookResponse]
    count: int


class WebhookEventResponse(BaseModel):
    """Webhook event log entry."""
    event_id: str
    event_type: str
    status: str  # pending, delivered, failed
    attempts: int
    created_at: datetime
    delivered_at: Optional[datetime]
    error_message: Optional[str]
    response_code: Optional[int]


class WebhookEventLogResponse(BaseModel):
    """Webhook event log."""
    events: List[WebhookEventResponse]
    count: int


# ============================================================================
# WEBHOOK CONFIGURATION ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Webhook",
    description="Register a webhook URL for event notifications."
)
async def register_webhook(
    request: Request,
    webhook_data: WebhookRegisterRequest,
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Register a webhook endpoint for receiving event notifications.
    
    **Authentication:** Requires valid API key + secret.
    
    **Request Body:**
    - `url`: Webhook endpoint URL (must be HTTPS in production)
    - `event_types`: List of event type patterns (supports wildcards)
      - Examples: `["wallet.*"]`, `["transaction.confirmed", "transaction.failed"]`
      - Available events:
        - `wallet.created`, `wallet.updated`
        - `transaction.created`, `transaction.confirmed`, `transaction.failed`
        - `signature.pending`, `signature.approved`, `signature.rejected`
    - `description`: Optional description for this webhook
    - `secret`: Optional custom HMAC secret (overrides API secret)
    
    **Returns:** Webhook configuration details.
    """
    partner = get_partner_from_request(request)
    
    # Register webhook
    webhook_id = await webhook_service.register_webhook(
        partner_id=partner["partner_id"],
        url=str(webhook_data.url),
        event_types=webhook_data.event_types,
        description=webhook_data.description,
        secret=webhook_data.secret
    )
    
    # Fetch created webhook
    webhooks = await webhook_service.list_webhooks(partner["partner_id"])
    created_webhook = next((w for w in webhooks if w["id"] == webhook_id), None)
    
    if not created_webhook:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "webhook_not_found", "message": "Webhook created but not found"}
        )
    
    return WebhookResponse(**created_webhook)


@router.get(
    "",
    response_model=WebhookListResponse,
    summary="List Webhooks",
    description="Get all webhook configurations for partner."
)
async def list_webhooks(
    request: Request,
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    List all webhook configurations for authenticated partner.
    
    **Authentication:** Requires valid API key + secret.
    
    **Returns:** List of webhook configurations with delivery statistics.
    """
    partner = get_partner_from_request(request)
    
    webhooks = await webhook_service.list_webhooks(partner["partner_id"])
    
    return WebhookListResponse(
        webhooks=[WebhookResponse(**w) for w in webhooks],
        count=len(webhooks)
    )


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Webhook",
    description="Remove a webhook configuration."
)
async def delete_webhook(
    request: Request,
    webhook_id: int,
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Delete a webhook configuration.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `webhook_id`: Webhook configuration ID
    
    **Returns:** 204 No Content on success.
    """
    partner = get_partner_from_request(request)
    
    success = await webhook_service.delete_webhook(webhook_id, partner["partner_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "webhook_not_found", "message": f"Webhook {webhook_id} not found"}
        )


# ============================================================================
# WEBHOOK EVENT LOG ENDPOINTS
# ============================================================================

@router.get(
    "/events",
    response_model=WebhookEventLogResponse,
    summary="Get Event Log",
    description="Get webhook delivery history."
)
async def get_event_log(
    request: Request,
    limit: int = Query(100, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, delivered, failed)"),
    webhook_service: WebhookService = Depends(get_webhook_service)
):
    """
    Get webhook event delivery log.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `limit`: Max results per page (1-500, default 100)
    - `offset`: Pagination offset (default 0)
    - `status`: Optional filter by status (pending, delivered, failed)
    
    **Returns:** List of webhook event deliveries with status and errors.
    """
    partner = get_partner_from_request(request)
    
    events = await webhook_service.get_event_log(
        partner_id=partner["partner_id"],
        limit=limit,
        offset=offset,
        status=status_filter
    )
    
    return WebhookEventLogResponse(
        events=[
            WebhookEventResponse(
                event_id=str(e["event_id"]),
                event_type=e["event_type"],
                status=e["status"],
                attempts=e["attempts"],
                created_at=e["created_at"],
                delivered_at=e.get("delivered_at"),
                error_message=e.get("error_message"),
                response_code=e.get("response_code")
            )
            for e in events
        ],
        count=len(events)
    )
