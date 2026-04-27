"""API routes for scheduled transactions."""

import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from pydantic import BaseModel, Field

from backend.services.scheduled_transaction_service import ScheduledTransactionService
from backend.rbac import require_roles

logger = logging.getLogger("orgon.api.scheduled")

# Roles
_AUTH_ANY = require_roles(
    "platform_admin", "company_admin", "company_operator", "company_auditor", "end_user",
)
_AUTH_OPERATOR = require_roles("platform_admin", "company_admin", "company_operator")
_AUTH_ADMIN = require_roles("platform_admin", "company_admin")

router = APIRouter(prefix="/api/scheduled", tags=["scheduled"])


# Dependency injection helper
def get_scheduled_transaction_service(request: Request) -> ScheduledTransactionService:
    """Get ScheduledTransactionService from app state."""
    return request.app.state.scheduled_transaction_service


class CreateScheduledTransactionRequest(BaseModel):
    """Request to create a scheduled transaction."""
    
    token: str = Field(..., description="Token identifier (e.g., 'TRX:::1###wallet-name')")
    to_address: str = Field(..., description="Recipient address")
    value: str = Field(..., description="Amount to send (string with decimal)")
    scheduled_at: str = Field(..., description="ISO 8601 datetime when to send")
    info: Optional[str] = Field(None, description="Optional description")
    json_info: Optional[dict] = Field(None, description="Optional JSON metadata")
    recurrence_rule: Optional[str] = Field(
        None,
        description="Optional cron expression (e.g., '0 10 * * MON' = every Monday 10:00)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "TRX:::1###my-wallet",
                "to_address": "TYourAddress...",
                "value": "100.50",
                "scheduled_at": "2026-02-07T10:00:00Z",
                "info": "Monthly payment",
                "recurrence_rule": "0 10 1 * *"  # First day of each month at 10:00
            }
        }


@router.post("")
async def create_scheduled_transaction(
    request: CreateScheduledTransactionRequest,
    user: dict = Depends(_AUTH_OPERATOR),
    service: ScheduledTransactionService = Depends(get_scheduled_transaction_service),
):
    """
    Create a new scheduled transaction.
    
    For one-time payments, provide only `scheduled_at`.
    For recurring payments, also provide `recurrence_rule` (cron syntax).
    
    **Cron examples:**
    - `0 10 * * *` = Every day at 10:00
    - `0 10 * * MON` = Every Monday at 10:00
    - `0 10 1 * *` = First day of each month at 10:00
    - `0 */6 * * *` = Every 6 hours
    """
    
    try:
        # Parse scheduled_at
        scheduled_at = datetime.fromisoformat(request.scheduled_at.replace("Z", "+00:00"))
        
        # Validate it's in the future
        now = datetime.now(timezone.utc)
        if scheduled_at <= now:
            raise HTTPException(
                status_code=400,
                detail="scheduled_at must be in the future"
            )
        
        tx_id = await service.create_scheduled_transaction(
            token=request.token,
            to_address=request.to_address,
            value=request.value,
            scheduled_at=scheduled_at,
            info=request.info,
            json_info=request.json_info,
            recurrence_rule=request.recurrence_rule
        )
        
        return {
            "id": tx_id,
            "status": "pending",
            "scheduled_at": request.scheduled_at,
            "recurring": bool(request.recurrence_rule)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_scheduled_transactions(
    user: dict = Depends(_AUTH_ANY),
    service: ScheduledTransactionService = Depends(get_scheduled_transaction_service),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    """
    List scheduled transactions.
    
    Query params:
    - `status`: pending, sent, failed, cancelled
    - `limit`: Max number of results (1-200)
    """
    transactions = await service.list_scheduled_transactions(status=status, limit=limit)
    
    return {
        "total": len(transactions),
        "transactions": transactions
    }


@router.get("/upcoming")
async def get_upcoming_transactions(
    user: dict = Depends(_AUTH_ANY),
    service: ScheduledTransactionService = Depends(get_scheduled_transaction_service),
    hours: int = Query(24, ge=1, le=168, description="Look ahead N hours"),
):
    """Get transactions scheduled in the next N hours (default 24)."""
    upcoming = await service.get_upcoming_transactions(hours=hours)
    
    return {
        "total": len(upcoming),
        "hours": hours,
        "transactions": upcoming
    }


@router.get("/{tx_id}")
async def get_scheduled_transaction(
    tx_id: int,
    user: dict = Depends(_AUTH_ANY),
    service: ScheduledTransactionService = Depends(get_scheduled_transaction_service),
):
    """Get scheduled transaction by ID."""
    tx = await service.get_scheduled_transaction(tx_id)
    
    if not tx:
        raise HTTPException(status_code=404, detail="Scheduled transaction not found")
    
    return tx


@router.delete("/{tx_id}")
async def cancel_scheduled_transaction(
    tx_id: int,
    user: dict = Depends(_AUTH_OPERATOR),
    service: ScheduledTransactionService = Depends(get_scheduled_transaction_service),
):
    """Cancel a pending scheduled transaction."""
    
    # Check if exists and is pending
    tx = await service.get_scheduled_transaction(tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Scheduled transaction not found")
    
    if tx["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel transaction with status: {tx['status']}"
        )
    
    await service.cancel_scheduled_transaction(tx_id)
    
    return {
        "id": tx_id,
        "status": "cancelled",
        "message": "Scheduled transaction cancelled"
    }


@router.post("/process")
async def process_due_transactions(
    user: dict = Depends(_AUTH_ADMIN),
    service: ScheduledTransactionService = Depends(get_scheduled_transaction_service),
):
    """
    Background endpoint: Process transactions that are due to be sent.
    
    This is called by the scheduler every minute.
    Should not be called manually unless for testing.
    """
    results = await service.process_due_transactions()
    
    return {
        "processed": len(results),
        "results": results
    }
