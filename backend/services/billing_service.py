"""
Billing Service — subscription management, invoicing, payments.
Handles Asystem white-label platform monetization (170+ exchanges).
"""

import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import secrets
import json

from backend.api.schemas_billing import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    OrganizationSubscriptionCreate,
    OrganizationSubscriptionUpdate,
    InvoiceCreate,
    InvoiceUpdate,
    PaymentCreate,
    PaymentUpdate,
    TransactionFeeCreate,
    OrganizationPaymentMethodCreate,
    SubscriptionStatus,
    InvoiceStatus,
    PaymentStatus,
)


class BillingService:
    """Service for billing operations (subscriptions, invoices, payments)."""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    @staticmethod
    def _fix_jsonb_fields(d: dict) -> dict:
        """Parse JSONB fields and convert UUIDs to strings."""
        from uuid import UUID as _UUID
        for key in ('features', 'line_items', 'gateway_response'):
            if key in d and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except (json.JSONDecodeError, TypeError):
                    d[key] = {}
        # Convert UUID objects to strings for Pydantic
        for key, val in d.items():
            if isinstance(val, _UUID):
                d[key] = str(val)
        return d

    # ==================== Subscription Plans ====================
    
    async def get_subscription_plans(
        self, 
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all subscription plans."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM subscription_plans
                WHERE ($1 = FALSE OR is_active = TRUE)
                ORDER BY sort_order ASC, monthly_price ASC
            """
            rows = await conn.fetch(query, active_only)
            return [self._fix_jsonb_fields(dict(row)) for row in rows]
    
    async def get_subscription_plan_by_id(self, plan_id: UUID) -> Optional[Dict[str, Any]]:
        """Get subscription plan by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM subscription_plans WHERE id = $1",
                plan_id
            )
            return self._fix_jsonb_fields(dict(row)) if row else None
    
    async def get_subscription_plan_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get subscription plan by slug (e.g., 'pro', 'enterprise')."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM subscription_plans WHERE slug = $1",
                slug
            )
            return self._fix_jsonb_fields(dict(row)) if row else None
    
    # ==================== Stripe Webhook → Subscription State ====================

    # Stripe lifecycle states → values our schema accepts. Anything not in this
    # map falls through to no-op so we don't surprise the CHECK constraint.
    _STRIPE_STATUS_MAP = {
        "active":             "active",
        "trialing":           "trialing",
        "past_due":           "past_due",
        "unpaid":             "past_due",
        "canceled":           "cancelled",
        "incomplete":         "pending",
        "incomplete_expired": "expired",
        "paused":             "suspended",
    }

    async def upsert_subscription_from_checkout(
        self,
        *,
        organization_id: UUID,
        plan_slug: str,
        billing_cycle: str,
        stripe_subscription_id: str,
        stripe_customer_id: Optional[str],
        stripe_session_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Activate a subscription after `checkout.session.completed`.

        Looks up the local plan by slug, then INSERT-or-UPDATE the
        organization_subscriptions row keyed by stripe_subscription_id.
        Returns the resulting row (or None if no plan matches the slug —
        operator misconfigured Stripe price IDs).
        """
        plan = await self.get_subscription_plan_by_slug(plan_slug)
        if not plan:
            return None

        price = plan.get("yearly_price") if billing_cycle == "yearly" else plan.get("monthly_price")
        currency = plan.get("currency", "USD")
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=365 if billing_cycle == "yearly" else 30)

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO organization_subscriptions (
                    organization_id, plan_id, billing_cycle, start_date, end_date,
                    status, price, currency, auto_renew,
                    stripe_subscription_id, stripe_customer_id, stripe_session_id
                ) VALUES ($1, $2, $3, $4, $5, 'active', $6, $7, TRUE, $8, $9, $10)
                ON CONFLICT (stripe_subscription_id) DO UPDATE SET
                    organization_id    = EXCLUDED.organization_id,
                    plan_id            = EXCLUDED.plan_id,
                    billing_cycle      = EXCLUDED.billing_cycle,
                    start_date         = EXCLUDED.start_date,
                    end_date           = EXCLUDED.end_date,
                    status             = 'active',
                    price              = EXCLUDED.price,
                    currency           = EXCLUDED.currency,
                    stripe_customer_id = EXCLUDED.stripe_customer_id,
                    stripe_session_id  = EXCLUDED.stripe_session_id,
                    updated_at         = NOW()
                RETURNING *
                """,
                organization_id, UUID(str(plan["id"])), billing_cycle, start_date, end_date,
                Decimal(str(price or 0)), currency,
                stripe_subscription_id, stripe_customer_id, stripe_session_id,
            )
            return self._fix_jsonb_fields(dict(row)) if row else None

    async def update_subscription_status_by_stripe_id(
        self,
        *,
        stripe_subscription_id: str,
        stripe_status: str,
    ) -> Optional[Dict[str, Any]]:
        """Mirror a Stripe subscription state change.

        Maps Stripe's lifecycle string to one of our allowed status values
        and updates the matching row. Returns None if either no local row
        is correlated yet, or the Stripe status isn't one we recognise (in
        which case we deliberately don't touch the row).
        """
        local_status = self._STRIPE_STATUS_MAP.get(stripe_status)
        if not local_status:
            return None
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE organization_subscriptions
                   SET status     = $2,
                       updated_at = NOW(),
                       cancelled_at = CASE WHEN $2 = 'cancelled' THEN NOW() ELSE cancelled_at END
                 WHERE stripe_subscription_id = $1
                 RETURNING *
                """,
                stripe_subscription_id, local_status,
            )
            return self._fix_jsonb_fields(dict(row)) if row else None

    async def mark_invoice_past_due_by_stripe_id(
        self,
        *,
        stripe_subscription_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Flip the matching subscription to past_due on invoice.payment_failed."""
        return await self.update_subscription_status_by_stripe_id(
            stripe_subscription_id=stripe_subscription_id,
            stripe_status="past_due",
        )

    # ==================== Organization Subscriptions ====================

    async def create_subscription(
        self,
        data: OrganizationSubscriptionCreate,
        creator_user_id: UUID
    ) -> Dict[str, Any]:
        """Create new subscription for organization."""
        async with self.pool.acquire() as conn:
            # Calculate end_date based on billing_cycle
            start_date = datetime.utcnow()
            if data.billing_cycle == "monthly":
                end_date = start_date + timedelta(days=30)
            else:  # yearly
                end_date = start_date + timedelta(days=365)
            
            # If trial, override end_date
            if data.is_trial and data.trial_end_date:
                end_date = data.trial_end_date
            
            row = await conn.fetchrow(
                """
                INSERT INTO organization_subscriptions (
                    organization_id, plan_id, billing_cycle, start_date, end_date,
                    status, price, currency, trial_end_date, is_trial, auto_renew
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
                """,
                UUID(data.organization_id), UUID(data.plan_id), data.billing_cycle,
                start_date, end_date, SubscriptionStatus.ACTIVE.value,
                data.price, data.currency, data.trial_end_date, data.is_trial, data.auto_renew
            )
            return dict(row)
    
    async def get_organization_subscription(
        self,
        organization_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get active subscription for organization."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM organization_subscriptions
                WHERE organization_id = $1 AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
                """,
                organization_id
            )
            return self._fix_jsonb_fields(dict(row)) if row else None
    
    async def update_subscription(
        self,
        subscription_id: UUID,
        data: OrganizationSubscriptionUpdate
    ) -> Dict[str, Any]:
        """Update subscription (plan change, cancellation, etc.)."""
        async with self.pool.acquire() as conn:
            # Build dynamic UPDATE query
            updates = []
            values = []
            param_counter = 1
            
            if data.plan_id:
                updates.append(f"plan_id = ${param_counter}")
                values.append(UUID(data.plan_id))
                param_counter += 1
            
            if data.billing_cycle:
                updates.append(f"billing_cycle = ${param_counter}")
                values.append(data.billing_cycle.value)
                param_counter += 1
            
            if data.auto_renew is not None:
                updates.append(f"auto_renew = ${param_counter}")
                values.append(data.auto_renew)
                param_counter += 1
            
            if data.cancellation_reason:
                updates.append(f"cancellation_reason = ${param_counter}")
                values.append(data.cancellation_reason)
                param_counter += 1
                updates.append(f"cancelled_at = ${param_counter}")
                values.append(datetime.utcnow())
                param_counter += 1
                updates.append(f"status = ${param_counter}")
                values.append(SubscriptionStatus.CANCELLED.value)
                param_counter += 1
            
            if not updates:
                # No changes
                return await self.get_subscription_by_id(subscription_id)
            
            updates.append(f"updated_at = ${param_counter}")
            values.append(datetime.utcnow())
            param_counter += 1
            
            query = f"""
                UPDATE organization_subscriptions
                SET {', '.join(updates)}
                WHERE id = ${param_counter}
                RETURNING *
            """
            values.append(subscription_id)
            
            row = await conn.fetchrow(query, *values)
            return self._fix_jsonb_fields(dict(row)) if row else None
    
    async def cancel_subscription(
        self,
        subscription_id: UUID,
        reason: str
    ) -> Dict[str, Any]:
        """Cancel subscription (sets status to cancelled, keeps active until end_date)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE organization_subscriptions
                SET status = 'cancelled', cancelled_at = $1, cancellation_reason = $2, 
                    auto_renew = FALSE, updated_at = $1
                WHERE id = $3
                RETURNING *
                """,
                datetime.utcnow(), reason, subscription_id
            )
            return dict(row)
    
    # ==================== Invoices ====================
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number (INV-2026-000123)."""
        year = datetime.utcnow().year
        # In production, increment counter from database
        # For now, use random 6-digit number
        number = secrets.randbelow(999999) + 1
        return f"INV-{year}-{number:06d}"
    
    async def create_invoice(
        self,
        data: InvoiceCreate,
        creator_user_id: UUID
    ) -> Dict[str, Any]:
        """Create new invoice for organization."""
        async with self.pool.acquire() as conn:
            invoice_number = self._generate_invoice_number()
            
            row = await conn.fetchrow(
                """
                INSERT INTO invoices (
                    organization_id, subscription_id, invoice_number, issue_date, due_date,
                    subtotal, tax_rate, tax_amount, total, currency, status, line_items, notes
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING *
                """,
                UUID(data.organization_id), UUID(data.subscription_id) if data.subscription_id else None,
                invoice_number, datetime.utcnow(), data.due_date,
                data.subtotal, data.tax_rate, data.tax_amount, data.total, data.currency,
                InvoiceStatus.DRAFT.value, [item.dict() for item in data.line_items], data.notes
            )
            return dict(row)
    
    async def get_organization_invoices(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get invoices for organization."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT * FROM invoices
                WHERE organization_id = $1
                AND ($2::text IS NULL OR status = $2)
                ORDER BY created_at DESC
                LIMIT $3
            """
            rows = await conn.fetch(query, organization_id, status, limit)
            return [self._fix_jsonb_fields(dict(row)) for row in rows]
    
    async def get_invoice_by_id(self, invoice_id: UUID) -> Optional[Dict[str, Any]]:
        """Get invoice by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM invoices WHERE id = $1",
                invoice_id
            )
            return self._fix_jsonb_fields(dict(row)) if row else None
    
    async def update_invoice(
        self,
        invoice_id: UUID,
        data: InvoiceUpdate
    ) -> Dict[str, Any]:
        """Update invoice (status, payment info, etc.)."""
        async with self.pool.acquire() as conn:
            updates = []
            values = []
            param_counter = 1
            
            if data.due_date:
                updates.append(f"due_date = ${param_counter}")
                values.append(data.due_date)
                param_counter += 1
            
            if data.status:
                updates.append(f"status = ${param_counter}")
                values.append(data.status.value)
                param_counter += 1
                
                # If status = paid, set paid_at
                if data.status == InvoiceStatus.PAID:
                    updates.append(f"paid_at = ${param_counter}")
                    values.append(datetime.utcnow())
                    param_counter += 1
            
            if data.payment_method:
                updates.append(f"payment_method = ${param_counter}")
                values.append(data.payment_method)
                param_counter += 1
            
            if data.payment_reference:
                updates.append(f"payment_reference = ${param_counter}")
                values.append(data.payment_reference)
                param_counter += 1
            
            if data.notes is not None:
                updates.append(f"notes = ${param_counter}")
                values.append(data.notes)
                param_counter += 1
            
            if not updates:
                return await self.get_invoice_by_id(invoice_id)
            
            updates.append(f"updated_at = ${param_counter}")
            values.append(datetime.utcnow())
            param_counter += 1
            
            query = f"""
                UPDATE invoices
                SET {', '.join(updates)}
                WHERE id = ${param_counter}
                RETURNING *
            """
            values.append(invoice_id)
            
            row = await conn.fetchrow(query, *values)
            return dict(row)
    
    async def mark_invoice_as_paid(
        self,
        invoice_id: UUID,
        payment_reference: str,
        payment_method: str
    ) -> Dict[str, Any]:
        """Mark invoice as paid."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE invoices
                SET status = 'paid', paid_at = $1, payment_reference = $2, 
                    payment_method = $3, updated_at = $1
                WHERE id = $4
                RETURNING *
                """,
                datetime.utcnow(), payment_reference, payment_method, invoice_id
            )
            return dict(row)
    
    # ==================== Payments ====================
    
    async def create_payment(
        self,
        data: PaymentCreate
    ) -> Dict[str, Any]:
        """Create payment record."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO payments (
                    organization_id, invoice_id, payment_reference, amount, currency,
                    payment_method, payment_gateway, card_last4, card_brand, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                UUID(data.organization_id), UUID(data.invoice_id) if data.invoice_id else None,
                data.payment_reference, data.amount, data.currency,
                data.payment_method.value, data.payment_gateway, data.card_last4, data.card_brand,
                PaymentStatus.PENDING.value
            )
            return dict(row)
    
    async def update_payment_status(
        self,
        payment_id: UUID,
        status: PaymentStatus,
        failed_reason: Optional[str] = None,
        gateway_response: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update payment status (completed/failed)."""
        async with self.pool.acquire() as conn:
            completed_at = datetime.utcnow() if status == PaymentStatus.COMPLETED else None
            
            row = await conn.fetchrow(
                """
                UPDATE payments
                SET status = $1, completed_at = $2, failed_reason = $3, 
                    gateway_response = $4, updated_at = $5
                WHERE id = $6
                RETURNING *
                """,
                status.value, completed_at, failed_reason, gateway_response, datetime.utcnow(), payment_id
            )
            return dict(row)
    
    async def get_organization_payments(
        self,
        organization_id: UUID,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get payments for organization."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM payments
                WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                organization_id, limit
            )
            return [self._fix_jsonb_fields(dict(row)) for row in rows]
    
    # ==================== Transaction Fees ====================
    
    async def record_transaction_fee(
        self,
        data: TransactionFeeCreate
    ) -> Dict[str, Any]:
        """Record blockchain transaction fee for billing."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO transaction_fees (
                    organization_id, transaction_id, network, transaction_hash,
                    amount, token, amount_usd, exchange_rate, fee_type, billable
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING *
                """,
                UUID(data.organization_id), UUID(data.transaction_id) if data.transaction_id else None,
                data.network, data.transaction_hash, data.amount, data.token,
                data.amount_usd, data.exchange_rate, data.fee_type, data.billable
            )
            return dict(row)
    
    async def get_unbilled_transaction_fees(
        self,
        organization_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get transaction fees not yet billed to organization."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM transaction_fees
                WHERE organization_id = $1 AND billable = TRUE AND billed_in_invoice_id IS NULL
                ORDER BY created_at ASC
                """,
                organization_id
            )
            return [self._fix_jsonb_fields(dict(row)) for row in rows]
    
    # ==================== Auto-Billing ====================
    
    async def generate_monthly_invoice_for_subscription(
        self,
        subscription_id: UUID
    ) -> Dict[str, Any]:
        """
        Auto-generate monthly invoice for subscription.
        Called by cron job at start of each month.
        """
        async with self.pool.acquire() as conn:
            # Get subscription + plan details
            subscription = await conn.fetchrow(
                """
                SELECT s.*, p.name as plan_name, p.slug as plan_slug
                FROM organization_subscriptions s
                JOIN subscription_plans p ON s.plan_id = p.id
                WHERE s.id = $1
                """,
                subscription_id
            )
            
            if not subscription or subscription['status'] != 'active':
                raise ValueError("Subscription is not active")
            
            # Get unbilled transaction fees
            fees = await self.get_unbilled_transaction_fees(subscription['organization_id'])
            
            # Calculate invoice
            subscription_amount = subscription['price']
            fees_total = sum(Decimal(str(fee.get('amount_usd', 0) or 0)) for fee in fees)
            subtotal = subscription_amount + fees_total
            
            # Tax (example: 18% for KG)
            tax_rate = Decimal("18.00")
            tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
            total = subtotal + tax_amount
            
            # Line items
            line_items = [
                {
                    "description": f"{subscription['plan_name']} - {datetime.utcnow().strftime('%B %Y')}",
                    "quantity": 1,
                    "unit_price": float(subscription_amount),
                    "total": float(subscription_amount)
                }
            ]
            
            if fees:
                fees_description = f"Blockchain transaction fees ({len(fees)} transactions)"
                line_items.append({
                    "description": fees_description,
                    "quantity": len(fees),
                    "unit_price": float(fees_total / len(fees)) if len(fees) > 0 else 0,
                    "total": float(fees_total)
                })
            
            # Create invoice
            invoice_number = self._generate_invoice_number()
            due_date = datetime.utcnow() + timedelta(days=7)  # 7 days to pay
            
            invoice = await conn.fetchrow(
                """
                INSERT INTO invoices (
                    organization_id, subscription_id, invoice_number, issue_date, due_date,
                    subtotal, tax_rate, tax_amount, total, currency, status, line_items
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                subscription['organization_id'], subscription_id, invoice_number,
                datetime.utcnow(), due_date, subtotal, tax_rate, tax_amount, total,
                subscription['currency'], InvoiceStatus.SENT.value, line_items
            )
            
            # Mark fees as billed
            if fees:
                await conn.execute(
                    """
                    UPDATE transaction_fees
                    SET billed_in_invoice_id = $1
                    WHERE organization_id = $2 AND billable = TRUE AND billed_in_invoice_id IS NULL
                    """,
                    invoice['id'], subscription['organization_id']
                )
            
            return dict(invoice)
    
    # ==================== Simplified Payment Processing (TASK-005) ====================
    
    async def process_payment(
        self,
        invoice_id: UUID,
        payment_method: str,
        amount: Decimal,
        payment_reference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process payment for invoice (simplified for TASK-005).
        
        Steps:
        1. Create payment record
        2. Mark invoice as paid
        3. Return payment details
        """
        async with self.pool.acquire() as conn:
            # Get invoice
            invoice = await self.get_invoice_by_id(invoice_id)
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
            
            if invoice['status'] == InvoiceStatus.PAID.value:
                raise ValueError("Invoice already paid")
            
            # Generate payment reference if not provided
            if not payment_reference:
                year = datetime.utcnow().year
                number = secrets.randbelow(999999) + 1
                payment_reference = f"PAY-{year}-{number:06d}"
            
            # Create payment record
            payment = await conn.fetchrow(
                """
                INSERT INTO payments (
                    organization_id, invoice_id, payment_reference, amount, currency,
                    payment_method, payment_gateway, status, completed_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING *
                """,
                invoice['organization_id'], invoice_id, payment_reference,
                amount, invoice['currency'], payment_method,
                None,  # gateway (mock for now)
                PaymentStatus.COMPLETED.value,
                datetime.utcnow()
            )
            
            # Mark invoice as paid
            await conn.execute(
                """
                UPDATE invoices
                SET status = $1, paid_at = $2, payment_reference = $3, 
                    payment_method = $4, updated_at = $2
                WHERE id = $5
                """,
                InvoiceStatus.PAID.value, datetime.utcnow(), payment_reference,
                payment_method, invoice_id
            )
            
            return dict(payment)
    
    async def get_billing_summary(
        self,
        organization_id: UUID
    ) -> Dict[str, Any]:
        """
        Get billing summary for organization (TASK-005 dashboard).
        
        Returns:
        - Current subscription (plan, status, renewal date)
        - Outstanding balance (unpaid invoices)
        - Recent invoices (last 5)
        - Recent payments (last 5)
        - Total spend (all-time)
        """
        async with self.pool.acquire() as conn:
            # Get current subscription
            subscription = await self.get_organization_subscription(organization_id)
            
            # Get plan details if subscription exists
            plan = None
            if subscription:
                plan = await self.get_subscription_plan_by_id(UUID(str(subscription['plan_id'])))
            
            # Get outstanding balance (unpaid invoices)
            outstanding_row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(total), 0) as outstanding_balance
                FROM invoices
                WHERE organization_id = $1 AND status IN ('sent', 'overdue')
                """,
                organization_id
            )
            outstanding_balance = outstanding_row['outstanding_balance'] if outstanding_row else Decimal("0")
            
            # Get recent invoices
            recent_invoices = await conn.fetch(
                """
                SELECT * FROM invoices
                WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT 5
                """,
                organization_id
            )
            
            # Get recent payments
            recent_payments = await conn.fetch(
                """
                SELECT * FROM payments
                WHERE organization_id = $1
                ORDER BY created_at DESC
                LIMIT 5
                """,
                organization_id
            )
            
            # Get total spend
            total_spend_row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(amount), 0) as total_spend
                FROM payments
                WHERE organization_id = $1 AND status = 'completed'
                """,
                organization_id
            )
            total_spend = total_spend_row['total_spend'] if total_spend_row else Decimal("0")
            
            return {
                "organization_id": str(organization_id),
                "subscription": dict(subscription) if subscription else None,
                "plan": dict(plan) if plan else None,
                "outstanding_balance": float(outstanding_balance),
                "total_spend": float(total_spend),
                "recent_invoices": [dict(inv) for inv in recent_invoices],
                "recent_payments": [dict(pay) for pay in recent_payments],
                "next_invoice_date": subscription['end_date'] if subscription else None
            }

    # ==================== Manual Payment Flow (KG Market) ====================
    
    async def create_manual_payment_request(
        self,
        invoice_id: "UUID"
    ) -> Dict[str, Any]:
        """
        Create a pending manual payment (bank transfer) for an invoice.
        Admin must confirm it later.
        """
        invoice = await self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        if invoice['status'] == 'paid':
            raise ValueError("Invoice already paid")
        
        # Generate reference
        year = datetime.utcnow().year
        number = secrets.randbelow(999999) + 1
        payment_reference = f"MAN-{year}-{number:06d}"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO payments (
                    organization_id, invoice_id, payment_reference, amount, currency,
                    payment_method, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                invoice['organization_id'], invoice_id, payment_reference,
                invoice['total'], invoice.get('currency', 'KGS'),
                'bank_transfer', PaymentStatus.PENDING.value
            )
            
            # Update invoice status to reflect pending payment
            await conn.execute(
                "UPDATE invoices SET status = 'sent', updated_at = $1 WHERE id = $2 AND status = 'draft'",
                datetime.utcnow(), invoice_id
            )
            
            return self._fix_jsonb_fields(dict(row))
    
    async def confirm_manual_payment(
        self,
        payment_id: "UUID",
        admin_user_id: "UUID"
    ) -> Dict[str, Any]:
        """
        Admin confirms a manual payment. Marks payment as completed and invoice as paid.
        """
        async with self.pool.acquire() as conn:
            # Get payment
            payment = await conn.fetchrow(
                "SELECT * FROM payments WHERE id = $1", payment_id
            )
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
            
            if payment['status'] == PaymentStatus.COMPLETED.value:
                raise ValueError("Payment already confirmed")
            
            now = datetime.utcnow()
            
            # Update payment
            row = await conn.fetchrow(
                """
                UPDATE payments SET 
                    status = $1, completed_at = $2, 
                    admin_confirmed_by = $3, admin_confirmed_at = $2,
                    updated_at = $2
                WHERE id = $4
                RETURNING *
                """,
                PaymentStatus.COMPLETED.value, now, admin_user_id, payment_id
            )
            
            # Mark invoice as paid
            if payment['invoice_id']:
                await conn.execute(
                    """
                    UPDATE invoices SET 
                        status = 'paid', paid_at = $1, 
                        payment_method = 'bank_transfer',
                        payment_reference = $2, updated_at = $1
                    WHERE id = $3
                    """,
                    now, payment['payment_reference'], payment['invoice_id']
                )
                
                # Activate subscription if linked
                invoice = await conn.fetchrow(
                    "SELECT subscription_id FROM invoices WHERE id = $1",
                    payment['invoice_id']
                )
                if invoice and invoice['subscription_id']:
                    await conn.execute(
                        """
                        UPDATE organization_subscriptions SET 
                            status = 'active', updated_at = $1
                        WHERE id = $2 AND status = 'pending'
                        """,
                        now, invoice['subscription_id']
                    )
            
            return self._fix_jsonb_fields(dict(row))

