"""
Partner Scheduled Transactions API
Scheduled and recurring transactions for B2B partners
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends, Query
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from croniter import croniter

from backend.services.scheduled_transaction_service import ScheduledTransactionService
from backend.api.middleware_b2b import get_partner_from_request


# Create router
router = APIRouter(prefix="/api/v1/partner/scheduled-transactions", tags=["Partner API - Scheduled Transactions"])


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

async def get_scheduled_transaction_service(request: Request) -> ScheduledTransactionService:
    """Get ScheduledTransactionService instance from app state."""
    if not hasattr(request.app.state, "scheduled_transaction_service"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "service_unavailable", "message": "Scheduled transaction service not available"}
        )
    return request.app.state.scheduled_transaction_service


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class ScheduledTransactionCreateRequest(BaseModel):
    """Create scheduled transaction request."""
    wallet_name: str = Field(..., description="Source wallet name")
    token: str = Field(..., description="Token symbol (TRX, USDT, etc.)")
    to_address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount to send (decimal string)")
    scheduled_at: str = Field(..., description="ISO 8601 timestamp when to execute")
    recurrence_rule: Optional[str] = Field(None, description="Optional cron expression for recurring transactions")
    description: Optional[str] = Field(None, description="Optional description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "wallet_name": "my-wallet",
                "token": "TRX",
                "to_address": "TYourAddress...",
                "amount": "100.50",
                "scheduled_at": "2026-02-09T10:00:00Z",
                "recurrence_rule": "0 10 1 * *",  # First day of month at 10:00
                "description": "Monthly salary payment"
            }
        }


class ScheduledTransactionResponse(BaseModel):
    """Scheduled transaction response."""
    id: str
    wallet_name: str
    token: str
    to_address: str
    amount: str
    scheduled_at: datetime
    recurrence_rule: Optional[str]
    description: Optional[str]
    status: str  # pending, executed, cancelled, failed
    created_at: datetime
    executed_at: Optional[datetime]
    next_run_at: Optional[datetime]


class ScheduledTransactionListResponse(BaseModel):
    """List of scheduled transactions."""
    transactions: List[ScheduledTransactionResponse]
    count: int


# ============================================================================
# SCHEDULED TRANSACTION ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=ScheduledTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Scheduled Transaction",
    description="Schedule a transaction for future execution (one-time or recurring)."
)
async def create_scheduled_transaction(
    request: Request,
    tx_data: ScheduledTransactionCreateRequest,
    scheduled_tx_service: ScheduledTransactionService = Depends(get_scheduled_transaction_service)
):
    """
    Create a scheduled transaction.
    
    **Authentication:** Requires valid API key + secret.
    
    **Request Body:**
    - `wallet_name`: Source wallet name
    - `token`: Token symbol (TRX, USDT, etc.)
    - `to_address`: Destination address
    - `amount`: Amount to send (decimal string)
    - `scheduled_at`: ISO 8601 timestamp when to execute
    - `recurrence_rule`: Optional cron expression for recurring transactions
      - Examples: `0 10 * * *` (daily 10:00), `0 10 1 * *` (monthly 1st at 10:00)
    - `description`: Optional description
    
    **Returns:** Created scheduled transaction details.
    """
    partner = get_partner_from_request(request)
    
    # Parse and validate scheduled_at
    try:
        scheduled_at = datetime.fromisoformat(tx_data.scheduled_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_datetime", "message": f"Invalid scheduled_at format: {str(e)}"}
        )
    
    # Validate scheduled_at is in the future
    now = datetime.now(timezone.utc)
    if scheduled_at <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_datetime", "message": "scheduled_at must be in the future"}
        )
    
    # Validate cron expression if provided
    if tx_data.recurrence_rule:
        try:
            croniter(tx_data.recurrence_rule)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_cron", "message": f"Invalid cron expression: {str(e)}"}
            )
    
    # Create scheduled transaction
    # Format token: "network:::TOKEN###wallet_name"
    # TODO: Get network_id from wallet
    network_id = 5010  # Default to Tron Nile testnet for now
    token_formatted = f"{network_id}:::{tx_data.token}###{tx_data.wallet_name}"
    
    try:
        tx_id = await scheduled_tx_service.create_scheduled_transaction(
            token=token_formatted,
            to_address=tx_data.to_address,
            value=tx_data.amount,
            scheduled_at=scheduled_at,
            info=tx_data.description,
            json_info={"partner_id": str(partner["partner_id"])},
            recurrence_rule=tx_data.recurrence_rule
        )
        
        # Fetch created transaction
        created_tx = await scheduled_tx_service.get_scheduled_transaction(tx_id)
        
        if not created_tx:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "creation_failed", "message": "Transaction created but not found"}
            )
        
        return ScheduledTransactionResponse(
            id=str(created_tx["id"]),
            wallet_name=tx_data.wallet_name,
            token=tx_data.token,
            to_address=tx_data.to_address,
            amount=tx_data.amount,
            scheduled_at=created_tx["scheduled_at"],
            recurrence_rule=created_tx.get("recurrence_rule"),
            description=created_tx.get("info"),
            status=created_tx["status"],
            created_at=created_tx["created_at"],
            executed_at=created_tx.get("executed_at"),
            next_run_at=created_tx.get("next_run_at")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request", "message": str(e)}
        )


@router.get(
    "",
    response_model=ScheduledTransactionListResponse,
    summary="List Scheduled Transactions",
    description="Get all scheduled transactions for partner."
)
async def list_scheduled_transactions(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, executed, cancelled)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    scheduled_tx_service: ScheduledTransactionService = Depends(get_scheduled_transaction_service)
):
    """
    List scheduled transactions.
    
    **Authentication:** Requires valid API key + secret.
    
    **Query Parameters:**
    - `status`: Optional filter by status (pending, executed, cancelled, failed)
    - `limit`: Max results per page (1-100, default 50)
    - `offset`: Pagination offset (default 0)
    
    **Returns:** List of scheduled transactions.
    """
    partner = get_partner_from_request(request)
    
    # Get scheduled transactions
    # TODO: Filter by partner_id
    scheduled_txs = await scheduled_tx_service.list_scheduled_transactions(
        status=status_filter,
        limit=limit,
        offset=offset
    )
    
    transactions = [
        ScheduledTransactionResponse(
            id=str(tx["id"]),
            wallet_name=tx.get("token", "").split("###")[-1] if "###" in tx.get("token", "") else "unknown",
            token=tx.get("token", "").split(":::")[1].split("###")[0] if ":::" in tx.get("token", "") else "TRX",
            to_address=tx["to_address"],
            amount=tx["value"],
            scheduled_at=tx["scheduled_at"],
            recurrence_rule=tx.get("recurrence_rule"),
            description=tx.get("info"),
            status=tx["status"],
            created_at=tx["created_at"],
            executed_at=tx.get("executed_at"),
            next_run_at=tx.get("next_run_at")
        )
        for tx in scheduled_txs
    ]
    
    return ScheduledTransactionListResponse(
        transactions=transactions,
        count=len(transactions)
    )


@router.get(
    "/{tx_id}",
    response_model=ScheduledTransactionResponse,
    summary="Get Scheduled Transaction",
    description="Get details of a specific scheduled transaction."
)
async def get_scheduled_transaction(
    request: Request,
    tx_id: str,
    scheduled_tx_service: ScheduledTransactionService = Depends(get_scheduled_transaction_service)
):
    """
    Get scheduled transaction details.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `tx_id`: Scheduled transaction ID
    
    **Returns:** Scheduled transaction details.
    """
    partner = get_partner_from_request(request)
    
    tx = await scheduled_tx_service.get_scheduled_transaction(tx_id)
    
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Scheduled transaction {tx_id} not found"}
        )
    
    # TODO: Verify partner owns this transaction
    
    return ScheduledTransactionResponse(
        id=str(tx["id"]),
        wallet_name=tx.get("token", "").split("###")[-1] if "###" in tx.get("token", "") else "unknown",
        token=tx.get("token", "").split(":::")[1].split("###")[0] if ":::" in tx.get("token", "") else "TRX",
        to_address=tx["to_address"],
        amount=tx["value"],
        scheduled_at=tx["scheduled_at"],
        recurrence_rule=tx.get("recurrence_rule"),
        description=tx.get("info"),
        status=tx["status"],
        created_at=tx["created_at"],
        executed_at=tx.get("executed_at"),
        next_run_at=tx.get("next_run_at")
    )


@router.delete(
    "/{tx_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel Scheduled Transaction",
    description="Cancel a pending scheduled transaction."
)
async def cancel_scheduled_transaction(
    request: Request,
    tx_id: str,
    scheduled_tx_service: ScheduledTransactionService = Depends(get_scheduled_transaction_service)
):
    """
    Cancel a scheduled transaction.
    
    **Authentication:** Requires valid API key + secret.
    
    **Path Parameters:**
    - `tx_id`: Scheduled transaction ID
    
    **Returns:** 204 No Content on success.
    """
    partner = get_partner_from_request(request)
    
    # Get transaction first to verify ownership
    tx = await scheduled_tx_service.get_scheduled_transaction(tx_id)
    
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"Scheduled transaction {tx_id} not found"}
        )
    
    # TODO: Verify partner owns this transaction
    
    # Cancel transaction
    success = await scheduled_tx_service.cancel_scheduled_transaction(tx_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "cancellation_failed", "message": "Failed to cancel transaction"}
        )
