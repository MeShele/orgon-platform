"""
B2B API Schemas (Pydantic Models)
Request/response validation for Partner API
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class TransactionStatus(str, Enum):
    """Transaction status enum."""
    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"
    cancelled = "cancelled"


class SignatureStatus(str, Enum):
    """Signature status enum."""
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class PartnerTier(str, Enum):
    """Partner subscription tier."""
    free = "free"
    starter = "starter"
    business = "business"
    enterprise = "enterprise"


# ============================================================================
# BASE MODELS
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination query parameters."""
    limit: int = Field(50, ge=1, le=100, description="Max results per page (1-100)")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class PaginationMeta(BaseModel):
    """Pagination metadata in response."""
    total: int = Field(..., description="Total number of results")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether more results exist")


# ============================================================================
# WALLET SCHEMAS
# ============================================================================

class WalletCreateRequest(BaseModel):
    """Request to create a new wallet."""
    name: str = Field(..., min_length=1, max_length=255, description="Wallet name (unique)")
    network_id: int = Field(..., description="Network ID (5000=Tron mainnet, 5010=Tron Nile testnet)")
    wallet_type: int = Field(1, description="Wallet type (1=multisig)")
    label: Optional[str] = Field(None, max_length=255, description="Optional label")
    
    @validator('name')
    def validate_name(cls, v):
        """Ensure name doesn't contain special characters."""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Wallet name can only contain letters, numbers, hyphens, and underscores")
        return v


class TokenBalance(BaseModel):
    """Token balance information."""
    token: str = Field(..., description="Token symbol (TRX, USDT, etc.)")
    balance: str = Field(..., description="Balance (decimal string)")
    balance_decimal: float = Field(..., description="Balance as float")
    usd_value: Optional[float] = Field(None, description="USD value (if available)")


class WalletResponse(BaseModel):
    """Wallet details response."""
    name: str = Field(..., description="Wallet name")
    network_id: int = Field(..., description="Network ID")
    wallet_type: int = Field(..., description="Wallet type")
    address: Optional[str] = Field(None, description="Wallet address (if activated)")
    label: Optional[str] = Field(None, description="Custom label")
    is_favorite: bool = Field(False, description="Favorite status")
    tokens: List[TokenBalance] = Field([], description="Token balances")
    created_at: datetime = Field(..., description="Creation timestamp")
    synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")


class WalletListResponse(BaseModel):
    """Paginated list of wallets."""
    wallets: List[WalletResponse] = Field(..., description="Wallet list")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


# ============================================================================
# TRANSACTION SCHEMAS
# ============================================================================

class TransactionCreateRequest(BaseModel):
    """Request to create (send) a transaction."""
    wallet_name: str = Field(..., description="Source wallet name")
    token: str = Field(..., description="Token symbol (TRX, USDT, etc.)")
    to_address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount to send (decimal string)")
    memo: Optional[str] = Field(None, max_length=500, description="Optional memo/note")
    
    @validator('amount')
    def validate_amount(cls, v):
        """Ensure amount is positive decimal."""
        try:
            amount_float = float(v)
            if amount_float <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            raise ValueError("Amount must be a valid decimal number")
        return v


class TransactionResponse(BaseModel):
    """Transaction details response."""
    unid: str = Field(..., description="Unique transaction ID")
    wallet_name: str = Field(..., description="Source wallet")
    token: str = Field(..., description="Token symbol")
    to_address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount (decimal string)")
    status: TransactionStatus = Field(..., description="Transaction status")
    tx_hash: Optional[str] = Field(None, description="Blockchain transaction hash (if confirmed)")
    min_signatures: int = Field(..., description="Minimum signatures required")
    current_signatures: int = Field(0, description="Current signature count")
    memo: Optional[str] = Field(None, description="Transaction memo")
    created_at: datetime = Field(..., description="Creation timestamp")
    confirmed_at: Optional[datetime] = Field(None, description="Confirmation timestamp")


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""
    transactions: List[TransactionResponse] = Field(..., description="Transaction list")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


# ============================================================================
# SIGNATURE SCHEMAS
# ============================================================================

class SignatureApproveRequest(BaseModel):
    """Request to approve a pending signature."""
    # No body needed - partner context from auth middleware


class SignatureRejectRequest(BaseModel):
    """Request to reject a pending signature."""
    reason: Optional[str] = Field(None, max_length=500, description="Rejection reason")


class PendingSignature(BaseModel):
    """Pending signature information."""
    unid: str = Field(..., description="Transaction UNID")
    wallet_name: str = Field(..., description="Wallet name")
    token: str = Field(..., description="Token symbol")
    to_address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount")
    min_signatures: int = Field(..., description="Required signatures")
    current_signatures: int = Field(..., description="Current signatures")
    pending_since: datetime = Field(..., description="Timestamp when signature needed")


class PendingSignaturesResponse(BaseModel):
    """List of pending signatures."""
    pending: List[PendingSignature] = Field(..., description="Pending signatures")
    count: int = Field(..., description="Total pending count")


class SignatureHistoryEntry(BaseModel):
    """Signature history entry."""
    unid: str = Field(..., description="Transaction UNID")
    action: str = Field(..., description="Action (approve/reject)")
    user_id: str = Field(..., description="User EC address")
    timestamp: datetime = Field(..., description="Action timestamp")


class SignatureHistoryResponse(BaseModel):
    """Paginated signature history."""
    history: List[SignatureHistoryEntry] = Field(..., description="Signature history")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


# ============================================================================
# NETWORK & TOKEN INFO SCHEMAS
# ============================================================================

class NetworkInfo(BaseModel):
    """Network information."""
    network_id: int = Field(..., description="Network ID")
    name: str = Field(..., description="Network name")
    chain: str = Field(..., description="Blockchain (tron, ethereum, bitcoin)")
    is_testnet: bool = Field(..., description="Is testnet")


class NetworkListResponse(BaseModel):
    """List of supported networks."""
    networks: List[NetworkInfo] = Field(..., description="Network list")


class TokenInfo(BaseModel):
    """Token information with commission."""
    token: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token full name")
    network_id: int = Field(..., description="Network ID")
    commission_percent: float = Field(..., description="Platform commission (%)")
    min_amount: Optional[str] = Field(None, description="Minimum transaction amount")


class TokenListResponse(BaseModel):
    """List of supported tokens."""
    tokens: List[TokenInfo] = Field(..., description="Token list")


# ============================================================================
# ADDRESS BOOK SCHEMAS
# ============================================================================

class AddressCreateRequest(BaseModel):
    """Request to add address to book."""
    name: str = Field(..., min_length=1, max_length=255, description="Address name")
    address: str = Field(..., description="Blockchain address")
    network_id: int = Field(..., description="Network ID")
    label: Optional[str] = Field(None, max_length=100, description="Optional label")
    notes: Optional[str] = Field(None, max_length=1000, description="Optional notes")


class AddressResponse(BaseModel):
    """Saved address details."""
    id: str = Field(..., description="Address ID (UUID)")
    name: str = Field(..., description="Address name")
    address: str = Field(..., description="Blockchain address")
    network_id: int = Field(..., description="Network ID")
    label: Optional[str] = Field(None, description="Label")
    notes: Optional[str] = Field(None, description="Notes")
    is_favorite: bool = Field(False, description="Favorite status")
    created_at: datetime = Field(..., description="Creation timestamp")


class AddressListResponse(BaseModel):
    """List of saved addresses."""
    addresses: List[AddressResponse] = Field(..., description="Address list")
    count: int = Field(..., description="Total count")


# ============================================================================
# SCHEDULED TRANSACTION SCHEMAS
# ============================================================================

class ScheduledTransactionCreateRequest(BaseModel):
    """Request to schedule a transaction."""
    wallet_name: str = Field(..., description="Source wallet name")
    token: str = Field(..., description="Token symbol")
    to_address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount (decimal string)")
    schedule_time: datetime = Field(..., description="Execution time (UTC)")
    schedule_type: str = Field("once", description="Schedule type (once, daily, weekly, monthly, cron)")
    cron_expression: Optional[str] = Field(None, description="Cron expression (for recurring)")
    max_executions: Optional[int] = Field(None, description="Max executions (for recurring)")
    memo: Optional[str] = Field(None, max_length=500, description="Optional memo")


class ScheduledTransactionResponse(BaseModel):
    """Scheduled transaction details."""
    id: str = Field(..., description="Schedule ID (UUID)")
    wallet_name: str = Field(..., description="Wallet name")
    token: str = Field(..., description="Token symbol")
    to_address: str = Field(..., description="Destination address")
    amount: str = Field(..., description="Amount")
    schedule_time: datetime = Field(..., description="Next execution time")
    schedule_type: str = Field(..., description="Schedule type")
    status: str = Field(..., description="Status (pending, executing, completed, failed, cancelled)")
    execution_count: int = Field(..., description="Times executed")
    last_executed_at: Optional[datetime] = Field(None, description="Last execution timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class ScheduledTransactionListResponse(BaseModel):
    """List of scheduled transactions."""
    scheduled: List[ScheduledTransactionResponse] = Field(..., description="Scheduled transactions")
    count: int = Field(..., description="Total count")


# ============================================================================
# ANALYTICS SCHEMAS
# ============================================================================

class VolumeReportRequest(BaseModel):
    """Request for volume report."""
    start_date: datetime = Field(..., description="Report start date (UTC)")
    end_date: datetime = Field(..., description="Report end date (UTC)")
    grouping: str = Field("day", description="Grouping (hour, day, week, month)")


class VolumeDataPoint(BaseModel):
    """Volume data point."""
    timestamp: datetime = Field(..., description="Data point timestamp")
    volume_usd: float = Field(..., description="Volume in USD")
    transaction_count: int = Field(..., description="Number of transactions")


class VolumeReportResponse(BaseModel):
    """Volume report response."""
    data: List[VolumeDataPoint] = Field(..., description="Volume data points")
    total_volume_usd: float = Field(..., description="Total volume in USD")
    total_transactions: int = Field(..., description="Total transaction count")


class TokenDistributionEntry(BaseModel):
    """Token distribution entry."""
    token: str = Field(..., description="Token symbol")
    volume_usd: float = Field(..., description="Volume in USD")
    transaction_count: int = Field(..., description="Transaction count")
    percentage: float = Field(..., description="Percentage of total volume")


class TokenDistributionResponse(BaseModel):
    """Token distribution response."""
    distribution: List[TokenDistributionEntry] = Field(..., description="Token distribution")


# ============================================================================
# ERROR SCHEMAS
# ============================================================================

class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# ============================================================================
# HEALTH & STATUS SCHEMAS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field("ok", description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field("1.0.0", description="API version")
