"""
Pydantic schemas for Billing System.
Subscription plans, invoices, payments, transaction fees.
"""

from pydantic import BaseModel, Field, validator, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ==================== Enums ====================

class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    BALANCE = "balance"


class PaymentMethodType(str, Enum):
    CARD = "card"
    BANK_ACCOUNT = "bank_account"


# ==================== Subscription Plan ====================

class SubscriptionPlanBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=50)
    description: Optional[str] = None
    monthly_price: Decimal = Field(..., ge=0)
    yearly_price: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="KGS", max_length=10)
    features: Dict[str, Any] = Field(default_factory=dict)
    max_organizations: Optional[int] = Field(None, ge=1)
    max_wallets: Optional[int] = Field(None, ge=1)
    max_monthly_transactions: Optional[int] = Field(None, ge=1)
    max_monthly_volume_usd: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True
    sort_order: int = 0
    margin_min: Optional[Decimal] = Field(None, ge=0)


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    monthly_price: Optional[Decimal] = Field(None, ge=0)
    yearly_price: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field(default="KGS", max_length=10)
    features: Optional[Dict[str, Any]] = None
    max_wallets: Optional[int] = Field(None, ge=1)
    max_monthly_transactions: Optional[int] = Field(None, ge=1)
    max_monthly_volume_usd: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: Any
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Organization Subscription ====================

class OrganizationSubscriptionBase(BaseModel):
    organization_id: str
    plan_id: str
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    price: Decimal = Field(..., ge=0)
    currency: str = Field(default="KGS", max_length=10)
    is_trial: bool = False
    trial_end_date: Optional[datetime] = None
    auto_renew: bool = True


class OrganizationSubscriptionCreate(OrganizationSubscriptionBase):
    pass


class OrganizationSubscriptionUpdate(BaseModel):
    plan_id: Optional[str] = None
    billing_cycle: Optional[BillingCycle] = None
    auto_renew: Optional[bool] = None
    cancellation_reason: Optional[str] = None


class OrganizationSubscriptionResponse(OrganizationSubscriptionBase):
    id: Any
    status: SubscriptionStatus
    start_date: datetime
    end_date: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Invoice ====================

class InvoiceLineItem(BaseModel):
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    total: Decimal = Field(..., ge=0)


class InvoiceBase(BaseModel):
    organization_id: str
    subscription_id: Optional[str] = None
    due_date: datetime
    subtotal: Decimal = Field(..., ge=0)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    total: Decimal = Field(..., ge=0)
    currency: str = Field(default="KGS", max_length=10)
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    @validator('total')
    def validate_total(cls, v, values):
        """Ensure total = subtotal + tax_amount"""
        if 'subtotal' in values and 'tax_amount' in values:
            expected = values['subtotal'] + values['tax_amount']
            if abs(v - expected) > Decimal("0.01"):  # Allow 1 cent rounding
                raise ValueError(f"Total must equal subtotal + tax_amount (expected {expected})")
        return v


class InvoiceUpdate(BaseModel):
    due_date: Optional[datetime] = None
    status: Optional[InvoiceStatus] = None
    payment_method: Optional[str] = Field(None, max_length=50)
    payment_reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class InvoiceResponse(InvoiceBase):
    id: Any
    invoice_number: str
    issue_date: datetime
    status: InvoiceStatus
    paid_at: Optional[datetime] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Payment ====================

class PaymentBase(BaseModel):
    organization_id: str
    invoice_id: Optional[str] = None
    amount: Decimal = Field(..., ge=0)
    currency: str = Field(default="KGS", max_length=10)
    payment_method: PaymentMethod
    payment_gateway: Optional[str] = Field(None, max_length=50)


class PaymentCreate(PaymentBase):
    payment_reference: str = Field(..., max_length=100)
    card_last4: Optional[str] = Field(None, max_length=4)
    card_brand: Optional[str] = Field(None, max_length=20)


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    failed_reason: Optional[str] = None
    gateway_response: Optional[Dict[str, Any]] = None


class PaymentResponse(PaymentBase):
    id: Any
    payment_reference: str
    status: PaymentStatus
    completed_at: Optional[datetime] = None
    failed_reason: Optional[str] = None
    card_last4: Optional[str] = None
    card_brand: Optional[str] = None
    refunded_at: Optional[datetime] = None
    refund_amount: Optional[Decimal] = None
    refund_reason: Optional[str] = None
    gateway_response: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Transaction Fee ====================

class TransactionFeeBase(BaseModel):
    organization_id: str
    transaction_id: Optional[str] = None
    network: str = Field(..., max_length=20)
    transaction_hash: Optional[str] = Field(None, max_length=100)
    amount: Decimal = Field(..., ge=0)
    token: str = Field(default="TRX", max_length=20)
    amount_usd: Optional[Decimal] = Field(None, ge=0)
    exchange_rate: Optional[Decimal] = Field(None, ge=0)
    fee_type: str = Field(default="transaction", max_length=30)
    billable: bool = True


class TransactionFeeCreate(TransactionFeeBase):
    pass


class TransactionFeeUpdate(BaseModel):
    billable: Optional[bool] = None
    billed_in_invoice_id: Optional[str] = None


class TransactionFeeResponse(TransactionFeeBase):
    id: Any
    billed_in_invoice_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Organization Payment Method ====================

class OrganizationPaymentMethodBase(BaseModel):
    organization_id: str
    type: PaymentMethodType
    is_default: bool = False
    
    # Card fields (conditional)
    card_last4: Optional[str] = Field(None, max_length=4)
    card_brand: Optional[str] = Field(None, max_length=20)
    card_exp_month: Optional[int] = Field(None, ge=1, le=12)
    card_exp_year: Optional[int] = Field(None, ge=2024)
    card_holder_name: Optional[str] = Field(None, max_length=100)
    
    # Bank account fields (conditional)
    bank_name: Optional[str] = Field(None, max_length=100)
    account_last4: Optional[str] = Field(None, max_length=4)
    account_holder_name: Optional[str] = Field(None, max_length=100)
    
    # Gateway
    payment_gateway: Optional[str] = Field(None, max_length=50)
    gateway_payment_method_id: Optional[str] = Field(None, max_length=100)


class OrganizationPaymentMethodCreate(OrganizationPaymentMethodBase):
    # Disable validator temporarily - Phase 2 mock implementation
    # Will be re-enabled when payment integration is active
    pass


class OrganizationPaymentMethodUpdate(BaseModel):
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None
    verified: Optional[bool] = None


class OrganizationPaymentMethodResponse(OrganizationPaymentMethodBase):
    id: Any
    is_active: bool
    verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Billing Dashboard Stats ====================

class BillingStatsResponse(BaseModel):
    """Statistics for billing dashboard."""
    
    # Revenue
    total_revenue: Decimal
    monthly_revenue: Decimal
    outstanding_invoices: Decimal
    
    # Subscriptions
    active_subscriptions: int
    trial_subscriptions: int
    cancelled_this_month: int
    
    # Invoices
    pending_invoices: int
    overdue_invoices: int
    paid_this_month: int
    
    # Growth
    revenue_growth_percent: Decimal  # Month-over-month
    subscription_growth_percent: Decimal


class OrganizationBillingOverview(BaseModel):
    """Billing overview for a specific organization."""
    
    organization_id: str
    subscription: Optional[OrganizationSubscriptionResponse] = None
    next_invoice_date: Optional[datetime] = None
    next_invoice_amount: Optional[Decimal] = None
    outstanding_balance: Decimal
    payment_method: Optional[OrganizationPaymentMethodResponse] = None
    recent_invoices: List[InvoiceResponse] = Field(default_factory=list)
    recent_payments: List[PaymentResponse] = Field(default_factory=list)
