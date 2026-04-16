"""
Billing System Pydantic Schemas
Phase 2.1.2: Backend API
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# ============================================
# SUBSCRIPTION PLANS
# ============================================

class SubscriptionPlanBase(BaseModel):
    """Base schema for subscription plan"""
    name: str = Field(..., max_length=100, description="Plan name")
    slug: str = Field(..., max_length=50, description="URL-friendly identifier")
    description: Optional[str] = Field(None, description="Plan description")
    price_monthly: Decimal = Field(..., ge=0, description="Monthly price in USD")
    price_yearly: Optional[Decimal] = Field(None, ge=0, description="Yearly price (optional)")
    currency: str = Field(default="USD", max_length=3)
    features: Dict[str, Any] = Field(default_factory=dict, description="Plan features (JSON)")
    max_users: Optional[int] = Field(None, ge=1, description="Max users per org")
    max_wallets: Optional[int] = Field(None, ge=1, description="Max wallets")
    max_transactions_per_month: Optional[int] = Field(None, ge=0)
    trial_days: int = Field(default=14, ge=0, description="Free trial days")
    is_active: bool = Field(default=True)
    is_public: bool = Field(default=True, description="Visible in plan selector")


class SubscriptionPlanCreate(SubscriptionPlanBase):
    """Create subscription plan"""
    pass


class SubscriptionPlanUpdate(BaseModel):
    """Update subscription plan (all fields optional)"""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price_monthly: Optional[Decimal] = Field(None, ge=0)
    price_yearly: Optional[Decimal] = Field(None, ge=0)
    features: Optional[Dict[str, Any]] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_wallets: Optional[int] = Field(None, ge=1)
    max_transactions_per_month: Optional[int] = Field(None, ge=0)
    trial_days: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    is_public: Optional[bool] = None


class SubscriptionPlan(SubscriptionPlanBase):
    """Subscription plan response"""
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# SUBSCRIPTIONS
# ============================================

class SubscriptionBase(BaseModel):
    """Base schema for subscription"""
    organization_id: UUID
    plan_id: UUID
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")
    

class SubscriptionCreate(SubscriptionBase):
    """Create subscription"""
    start_trial: bool = Field(default=True, description="Start with trial period")


class SubscriptionUpdate(BaseModel):
    """Update subscription"""
    plan_id: Optional[UUID] = Field(None, description="Upgrade/downgrade plan")
    billing_cycle: Optional[str] = Field(None, pattern="^(monthly|yearly)$")


class SubscriptionCancel(BaseModel):
    """Cancel subscription"""
    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")
    cancel_at_period_end: bool = Field(default=True, description="Cancel at end of billing period")


class Subscription(SubscriptionBase):
    """Subscription response"""
    id: UUID
    status: str  # trial, active, past_due, cancelled, expired
    trial_start_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    start_date: datetime
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    current_usage: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    # Include plan details
    plan: Optional[SubscriptionPlan] = None

    class Config:
        from_attributes = True


# ============================================
# INVOICES
# ============================================

class InvoiceLineItemBase(BaseModel):
    """Base schema for invoice line item"""
    description: str = Field(..., max_length=255)
    item_type: str = Field(..., description="subscription, transaction_fee, one_time_charge, adjustment")
    quantity: Decimal = Field(default=Decimal("1"), ge=0)
    unit_price: Decimal = Field(..., description="Price per unit")
    amount: Decimal = Field(..., ge=0, description="quantity * unit_price")
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100, description="Tax percentage")
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvoiceLineItemCreate(InvoiceLineItemBase):
    """Create invoice line item"""
    pass


class InvoiceLineItem(InvoiceLineItemBase):
    """Invoice line item response"""
    id: UUID
    invoice_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    """Base schema for invoice"""
    organization_id: UUID
    subscription_id: Optional[UUID] = None
    description: Optional[str] = Field(None, description="Invoice description")
    due_date: date = Field(..., description="Payment due date")
    period_start: Optional[date] = Field(None, description="Billing period start")
    period_end: Optional[date] = Field(None, description="Billing period end")


class InvoiceCreate(InvoiceBase):
    """Create invoice"""
    line_items: list[InvoiceLineItemCreate] = Field(..., min_length=1)


class InvoiceUpdate(BaseModel):
    """Update invoice (limited fields)"""
    description: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None


class Invoice(InvoiceBase):
    """Invoice response"""
    id: UUID
    invoice_number: str
    status: str  # draft, open, paid, void, uncollectible
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    issue_date: date
    paid_at: Optional[datetime] = None
    voided_at: Optional[datetime] = None
    notes: Optional[str] = None
    pdf_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Include line items
    line_items: list[InvoiceLineItem] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ============================================
# PAYMENTS
# ============================================

class PaymentBase(BaseModel):
    """Base schema for payment"""
    invoice_id: UUID
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., description="card, bank_transfer, crypto, manual")
    payment_gateway: str = Field(default="manual", description="stripe, paypal, manual, etc")


class PaymentCreate(PaymentBase):
    """Create payment"""
    gateway_transaction_id: Optional[str] = Field(None, max_length=100)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentUpdate(BaseModel):
    """Update payment status"""
    status: str = Field(..., pattern="^(succeeded|failed|refunded)$")
    failure_reason: Optional[str] = None
    paid_at: Optional[datetime] = None


class PaymentRefund(BaseModel):
    """Refund payment"""
    amount: Decimal = Field(..., gt=0, description="Refund amount")
    reason: str = Field(..., max_length=500)


class Payment(PaymentBase):
    """Payment response"""
    id: UUID
    payment_number: str
    organization_id: UUID
    status: str  # pending, succeeded, failed, refunded
    currency: str
    gateway_transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    refund_amount: Decimal
    refund_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================
# TRANSACTION FEES
# ============================================

class TransactionFeeBase(BaseModel):
    """Base schema for transaction fee"""
    organization_id: UUID
    transaction_type: str = Field(..., description="withdrawal, deposit, exchange, transfer")
    transaction_id: Optional[UUID] = None
    fee_type: str = Field(..., description="percentage, fixed, tiered")
    fee_amount: Decimal = Field(..., ge=0)
    currency: str = Field(..., max_length=10)
    base_amount: Optional[Decimal] = Field(None, ge=0, description="Original transaction amount")
    fee_rate: Optional[Decimal] = Field(None, ge=0, le=1, description="Fee rate (0.025 = 2.5%)")


class TransactionFeeCreate(TransactionFeeBase):
    """Create transaction fee"""
    transaction_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransactionFee(TransactionFeeBase):
    """Transaction fee response"""
    id: UUID
    status: str  # pending, invoiced, paid
    invoice_id: Optional[UUID] = None
    transaction_date: datetime
    invoiced_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# DASHBOARD / SUMMARY SCHEMAS
# ============================================

class BillingDashboard(BaseModel):
    """Billing dashboard summary"""
    organization_id: UUID
    current_subscription: Optional[Subscription] = None
    account_balance: Decimal = Field(default=Decimal("0"))
    next_billing_date: Optional[datetime] = None
    pending_invoices_count: int = Field(default=0)
    pending_invoices_total: Decimal = Field(default=Decimal("0"))
    last_payment: Optional[Payment] = None
    usage_this_month: Dict[str, Any] = Field(default_factory=dict)


class FeesSummary(BaseModel):
    """Transaction fees summary"""
    organization_id: UUID
    period_start: date
    period_end: date
    total_fees: Decimal
    fees_by_type: Dict[str, Decimal]  # {"withdrawal": 10.50, "exchange": 5.25}
    pending_fees: Decimal
    invoiced_fees: Decimal
    paid_fees: Decimal
