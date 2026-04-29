"""
Billing API endpoints (TASK-005).
Subscription management, invoicing, payments, Stripe Checkout.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from backend.services.billing_service import BillingService
from backend.services.stripe_service import (
    StripeNotConfigured,
    get_stripe_service,
)
from backend.dependencies import get_current_user, get_db_pool
from backend.rbac import require_roles
from backend.api.schemas_billing import (
    SubscriptionPlanResponse,
    OrganizationSubscriptionResponse,
    InvoiceResponse,
    PaymentResponse,
)

logger = logging.getLogger("orgon.api.billing")

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


# ==================== Dependencies ====================

async def get_billing_service(pool = Depends(get_db_pool)) -> BillingService:
    """Get BillingService instance."""
    return BillingService(pool)


# ==================== Subscription Plans ====================

@router.get("/plans", response_model=List[SubscriptionPlanResponse])
async def get_subscription_plans(
    active_only: bool = True,
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Get all subscription plans (Starter, Professional, Enterprise).
    
    - **active_only**: Filter only active plans (default: true)
    """
    plans = await billing_service.get_subscription_plans(active_only)
    return plans


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanResponse)
async def get_subscription_plan(
    plan_id: UUID,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get subscription plan by ID."""
    plan = await billing_service.get_subscription_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    return plan


@router.get("/usage")
async def get_billing_usage(
    user: dict = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Aggregated billing usage for the dashboard `/billing` page.

    Returns the shape the frontend expects:
    `{current_plan, billing_cycle, outstanding_balance,
       usage: {transactions, wallets, api_calls}}`.

    The frontend hits this on every authenticated user; if the user has no
    active subscription we return a zeroed Starter view rather than 404,
    so the page renders cleanly during the demo.
    """
    org_id = user.get("organization_id") or user.get("current_organization_id")
    summary: dict | None = None
    if org_id:
        try:
            summary = await billing_service.get_usage_summary(org_id)
        except AttributeError:
            # Service-side aggregation not implemented yet — fall through
            # to the zeroed default. We expose the same shape either way.
            summary = None

    if summary:
        return summary

    return {
        "current_plan": "starter",
        "billing_cycle": "monthly",
        "outstanding_balance": "0.00",
        "usage": {
            "transactions": {"used": 0, "limit": 1000},
            "wallets":      {"used": 0, "limit": 10},
            "api_calls":    {"used": 0, "limit": 100000},
        },
    }


# ==================== Stripe Checkout ====================

class CheckoutRequest(BaseModel):
    organization_id: UUID
    plan_slug: str = Field(..., description="starter | basic | pro")
    billing_cycle: str = Field("monthly", pattern="^(monthly|yearly)$")


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    payload: CheckoutRequest,
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout Session and return its URL.

    Frontend redirects the browser to `url`. Stripe sends the user back to
    `/billing/success` (or `/billing/cancel`) and fires a webhook to
    `/api/v1/billing/webhook` which actually activates the subscription.
    """
    svc = get_stripe_service()
    if not svc.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured on this deployment",
        )
    try:
        return svc.create_checkout_session(
            organization_id=payload.organization_id,
            plan_slug=payload.plan_slug,
            billing_cycle=payload.billing_cycle,
            customer_email=user.get("email"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    billing_service: BillingService = Depends(get_billing_service),
):
    """Stripe webhook receiver — verifies signature, updates subscription
    state. Public (no auth) — security comes from the HMAC signature check.

    Dispatches:
      checkout.session.completed              → activate subscription
      customer.subscription.updated           → mirror status change
      customer.subscription.deleted           → mark cancelled
      invoice.payment_failed                  → mark past_due
    """
    svc = get_stripe_service()
    if not svc.configured:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = svc.verify_webhook(payload, sig)
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # SignatureVerificationError, malformed JSON, etc.
        logger.warning("Stripe webhook signature check failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    et = event.get("type")
    obj = event.get("data", {}).get("object", {}) or {}
    metadata = obj.get("metadata") or {}
    org_id_raw = metadata.get("organization_id") or obj.get("client_reference_id")

    logger.info("Stripe webhook received: %s · org=%s", et, org_id_raw)

    handled = False
    try:
        if et == "checkout.session.completed":
            # Stripe sends `subscription` (sub_…) and `customer` (cus_…) on the
            # session. metadata carries our plan_slug + billing_cycle (set in
            # StripeService.create_checkout_session).
            sub_id = obj.get("subscription")
            if not sub_id or not org_id_raw:
                logger.warning(
                    "checkout.session.completed missing subscription/org — skipping (sub=%s org=%s)",
                    sub_id, org_id_raw,
                )
            else:
                row = await billing_service.upsert_subscription_from_checkout(
                    organization_id=UUID(str(org_id_raw)),
                    plan_slug=metadata.get("plan_slug", "starter"),
                    billing_cycle=metadata.get("billing_cycle", "monthly"),
                    stripe_subscription_id=str(sub_id),
                    stripe_customer_id=obj.get("customer"),
                    stripe_session_id=obj.get("id"),
                )
                if row is None:
                    logger.warning(
                        "checkout.session.completed: plan_slug '%s' not found locally — "
                        "subscription left unactivated",
                        metadata.get("plan_slug"),
                    )
                else:
                    handled = True

        elif et in ("customer.subscription.updated", "customer.subscription.deleted"):
            # On subscription events the object IS the subscription; status
            # is on `obj["status"]` directly.
            sub_id = obj.get("id")
            stripe_status = "canceled" if et == "customer.subscription.deleted" else obj.get("status", "")
            if sub_id:
                row = await billing_service.update_subscription_status_by_stripe_id(
                    stripe_subscription_id=str(sub_id),
                    stripe_status=stripe_status,
                )
                handled = row is not None

        elif et == "invoice.payment_failed":
            # Invoice object carries `subscription` (sub_…). Map to past_due.
            sub_id = obj.get("subscription")
            if sub_id:
                row = await billing_service.mark_invoice_past_due_by_stripe_id(
                    stripe_subscription_id=str(sub_id),
                )
                handled = row is not None

    except Exception:
        # Never 500 on an unhandled webhook — Stripe retries on non-2xx, so a
        # transient bug would cascade. Log + acknowledge instead. Errors get
        # caught by global_exception_handler too, but this keeps the contract
        # explicit at the endpoint level.
        logger.exception("Stripe webhook handler raised on event %s", et)

    return {"received": True, "type": et, "handled": handled}


# ==================== Organization Subscriptions ====================

@router.post("/subscribe", response_model=OrganizationSubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    organization_id: UUID,
    plan_id: UUID,
    billing_cycle: str = "monthly",
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Subscribe organization to a plan (TASK-005).
    
    - **organization_id**: Organization UUID
    - **plan_id**: Plan UUID (starter/professional/enterprise)
    - **billing_cycle**: monthly or yearly
    
    Creates:
    - Subscription record (active)
    - First invoice (auto-generated)
    """
    # Get plan details
    plan = await billing_service.get_subscription_plan_by_id(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription plan not found"
        )
    
    # Calculate price
    if billing_cycle == "yearly" and plan.get('yearly_price'):
        price = plan['yearly_price']
    else:
        price = plan['monthly_price']
    
    # Create subscription (imports OrganizationSubscriptionCreate internally)
    from backend.api.schemas_billing import OrganizationSubscriptionCreate
    
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(organization_id),
        plan_id=str(plan_id),
        billing_cycle=billing_cycle,
        price=Decimal(str(price)),
        currency="KGS",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(
        subscription_data,
        UUID(str(user['id']))
    )
    
    return subscription


@router.delete("/subscribe/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_subscription(
    subscription_id: UUID,
    reason: str = "User cancelled",
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Cancel subscription (TASK-005).
    
    - **subscription_id**: Subscription UUID
    - **reason**: Cancellation reason (optional)
    
    Note: Subscription remains active until end_date.
    """
    subscription = await billing_service.cancel_subscription(subscription_id, reason)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    return None


@router.get("/subscription/{organization_id}", response_model=Optional[OrganizationSubscriptionResponse])
async def get_organization_subscription(
    organization_id: UUID,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get current subscription for organization."""
    subscription = await billing_service.get_organization_subscription(organization_id)
    return subscription


# ==================== Invoices ====================

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    org_id: Optional[UUID] = Query(None, description="Organization ID filter"),
    invoice_status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Get invoices (TASK-005).
    
    - **org_id**: Filter by organization (optional)
    - **invoice_status**: Filter by status (draft/sent/paid/overdue/cancelled)
    - **limit**: Max results (default 50, max 100)
    """
    if not org_id:
        # If no org_id, user must be admin (would need to fetch all orgs)
        # For TASK-005, require org_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="org_id parameter required"
        )
    
    invoices = await billing_service.get_organization_invoices(
        org_id,
        status=invoice_status,
        limit=limit
    )
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get invoice by ID."""
    invoice = await billing_service.get_invoice_by_id(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


# ==================== Payments ====================

@router.post("/pay", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def process_payment(
    invoice_id: UUID,
    payment_method: str,
    amount: Decimal,
    payment_reference: Optional[str] = None,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Process payment for invoice (TASK-005).
    
    - **invoice_id**: Invoice UUID to pay
    - **payment_method**: card/bank_transfer/crypto
    - **amount**: Payment amount (must match invoice total)
    - **payment_reference**: Optional reference (auto-generated if not provided)
    
    Creates payment record and marks invoice as paid.
    """
    try:
        payment = await billing_service.process_payment(
            invoice_id,
            payment_method,
            amount,
            payment_reference
        )
        return payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payments", response_model=List[PaymentResponse])
async def get_payments(
    org_id: UUID = Query(..., description="Organization ID"),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """Get payment history for organization."""
    payments = await billing_service.get_organization_payments(org_id, limit)
    return payments


# ==================== Billing Summary (Dashboard) ====================

@router.get("/summary/{org_id}")
async def get_billing_summary(
    org_id: UUID,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Get billing summary for organization (TASK-005 dashboard).
    
    Returns:
    - Current subscription
    - Plan details
    - Outstanding balance
    - Total spend
    - Recent invoices (5)
    - Recent payments (5)
    - Next invoice date
    """
    summary = await billing_service.get_billing_summary(org_id)
    return summary


# ==================== Admin: Generate Invoice (Manual Trigger) ====================

@router.post("/admin/generate-invoice/{subscription_id}", response_model=InvoiceResponse)
async def generate_invoice_manual(
    subscription_id: UUID,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Manually generate invoice for subscription (Admin only).
    
    Normally auto-triggered by cron monthly.
    """
    # TODO: Check if user is admin
    try:
        invoice = await billing_service.generate_monthly_invoice_for_subscription(subscription_id)
        return invoice
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== Admin: Confirm Manual Payment ====================

@router.post("/admin/confirm-payment/{payment_id}", response_model=PaymentResponse)
async def confirm_manual_payment(
    payment_id: UUID,
    user: dict = Depends(require_roles("super_admin")),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Admin confirms a manual payment (bank transfer).
    Sets payment status to completed and marks invoice as paid.
    """
    try:
        payment = await billing_service.confirm_manual_payment(
            payment_id, UUID(str(user['id']))
        )
        return payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== Public: Request Manual Payment ====================

@router.post("/payment/manual", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def request_manual_payment(
    invoice_id: UUID,
    user: dict = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service)
):
    """
    Organization requests manual payment (bank transfer).
    Creates a pending payment that admin must confirm.
    """
    try:
        payment = await billing_service.create_manual_payment_request(invoice_id)
        return payment
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
