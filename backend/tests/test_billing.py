"""
Pytest tests for Billing System (TASK-005).
Tests subscription management, invoicing, payments.
"""

import pytest
import asyncio
import asyncpg
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from backend.services.billing_service import BillingService
from backend.api.schemas_billing import (
    OrganizationSubscriptionCreate,
    PaymentStatus,
    InvoiceStatus,
)

# Test configuration
TEST_DB_URL = "postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    """Create database pool for tests."""
    pool = await asyncpg.create_pool(TEST_DB_URL, min_size=1, max_size=5)
    yield pool
    await pool.close()


@pytest.fixture
async def billing_service(db_pool):
    """Create BillingService instance."""
    return BillingService(db_pool)


@pytest.fixture
async def test_organization(db_pool):
    """Create test organization."""
    async with db_pool.acquire() as conn:
        # Create test org
        org_id = await conn.fetchval(
            """
            INSERT INTO organizations (name, slug, license_type)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            "Test Billing Org",
            f"test-billing-{uuid4().hex[:8]}",
            "pro"
        )
        
        yield org_id
        
        # Cleanup
        await conn.execute("DELETE FROM organizations WHERE id = $1", org_id)


@pytest.fixture
async def test_plan(db_pool):
    """Get starter plan from seed data."""
    async with db_pool.acquire() as conn:
        plan = await conn.fetchrow(
            "SELECT * FROM subscription_plans WHERE slug = 'starter' LIMIT 1"
        )
        if not plan:
            # Create if not exists
            plan_id = await conn.fetchval(
                """
                INSERT INTO subscription_plans (name, slug, monthly_price, yearly_price)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                "Starter", "starter", 99.00, 990.00
            )
            plan = await conn.fetchrow("SELECT * FROM subscription_plans WHERE id = $1", plan_id)
        
        return dict(plan)


# ==================== Subscription Tests ====================

@pytest.mark.asyncio
async def test_get_subscription_plans(billing_service):
    """Test getting subscription plans."""
    plans = await billing_service.get_subscription_plans(active_only=True)
    
    assert len(plans) >= 1
    assert all('id' in p and 'name' in p and 'monthly_price' in p for p in plans)


@pytest.mark.asyncio
async def test_create_subscription(billing_service, test_organization, test_plan):
    """Test creating subscription."""
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(
        subscription_data,
        test_organization  # creator_user_id
    )
    
    assert subscription['organization_id'] == test_organization
    assert subscription['plan_id'] == test_plan['id']
    assert subscription['status'] == 'active'
    assert subscription['price'] == test_plan['monthly_price']


@pytest.mark.asyncio
async def test_get_organization_subscription(billing_service, test_organization, test_plan):
    """Test getting organization's subscription."""
    # Create subscription first
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    created = await billing_service.create_subscription(subscription_data, test_organization)
    
    # Get subscription
    subscription = await billing_service.get_organization_subscription(test_organization)
    
    assert subscription is not None
    assert subscription['id'] == created['id']
    assert subscription['organization_id'] == test_organization


@pytest.mark.asyncio
async def test_cancel_subscription(billing_service, test_organization, test_plan):
    """Test cancelling subscription."""
    # Create subscription
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(subscription_data, test_organization)
    
    # Cancel
    cancelled = await billing_service.cancel_subscription(
        UUID(str(subscription['id'])),
        "Test cancellation"
    )
    
    assert cancelled['status'] == 'cancelled'
    assert cancelled['auto_renew'] is False
    assert cancelled['cancellation_reason'] == "Test cancellation"
    assert cancelled['cancelled_at'] is not None


# ==================== Invoice Tests ====================

@pytest.mark.asyncio
async def test_generate_monthly_invoice(billing_service, test_organization, test_plan):
    """Test auto-generating monthly invoice."""
    # Create subscription
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(subscription_data, test_organization)
    
    # Generate invoice
    invoice = await billing_service.generate_monthly_invoice_for_subscription(
        UUID(str(subscription['id']))
    )
    
    assert invoice['organization_id'] == test_organization
    assert invoice['subscription_id'] == subscription['id']
    assert invoice['status'] == 'sent'
    assert invoice['total'] > 0
    assert 'INV-' in invoice['invoice_number']


@pytest.mark.asyncio
async def test_get_organization_invoices(billing_service, test_organization, test_plan):
    """Test getting invoices for organization."""
    # Create subscription + invoice
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(subscription_data, test_organization)
    await billing_service.generate_monthly_invoice_for_subscription(UUID(str(subscription['id'])))
    
    # Get invoices
    invoices = await billing_service.get_organization_invoices(test_organization)
    
    assert len(invoices) >= 1
    assert all(inv['organization_id'] == test_organization for inv in invoices)


# ==================== Payment Tests ====================

@pytest.mark.asyncio
async def test_process_payment(billing_service, test_organization, test_plan):
    """Test processing payment for invoice."""
    # Create subscription + invoice
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(subscription_data, test_organization)
    invoice = await billing_service.generate_monthly_invoice_for_subscription(UUID(str(subscription['id'])))
    
    # Process payment
    payment = await billing_service.process_payment(
        invoice_id=UUID(str(invoice['id'])),
        payment_method='card',
        amount=Decimal(str(invoice['total'])),
        payment_reference=None  # Auto-generate
    )
    
    assert payment['invoice_id'] == invoice['id']
    assert payment['status'] == PaymentStatus.COMPLETED.value
    assert payment['amount'] == invoice['total']
    assert 'PAY-' in payment['payment_reference']
    
    # Verify invoice marked as paid
    updated_invoice = await billing_service.get_invoice_by_id(UUID(str(invoice['id'])))
    assert updated_invoice['status'] == InvoiceStatus.PAID.value
    assert updated_invoice['paid_at'] is not None


@pytest.mark.asyncio
async def test_payment_already_paid_error(billing_service, test_organization, test_plan):
    """Test error when trying to pay already paid invoice."""
    # Create subscription + invoice
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    subscription = await billing_service.create_subscription(subscription_data, test_organization)
    invoice = await billing_service.generate_monthly_invoice_for_subscription(UUID(str(subscription['id'])))
    
    # Pay first time
    await billing_service.process_payment(
        UUID(str(invoice['id'])),
        'card',
        Decimal(str(invoice['total']))
    )
    
    # Try to pay again
    with pytest.raises(ValueError, match="Invoice already paid"):
        await billing_service.process_payment(
            UUID(str(invoice['id'])),
            'card',
            Decimal(str(invoice['total']))
        )


# ==================== Billing Summary Tests ====================

@pytest.mark.asyncio
async def test_get_billing_summary(billing_service, test_organization, test_plan):
    """Test getting billing summary for organization."""
    # Create subscription
    subscription_data = OrganizationSubscriptionCreate(
        organization_id=str(test_organization),
        plan_id=str(test_plan['id']),
        billing_cycle="monthly",
        price=Decimal(str(test_plan['monthly_price'])),
        currency="USD",
        is_trial=False,
        auto_renew=True
    )
    
    await billing_service.create_subscription(subscription_data, test_organization)
    
    # Get summary
    summary = await billing_service.get_billing_summary(test_organization)
    
    assert summary['organization_id'] == str(test_organization)
    assert summary['subscription'] is not None
    assert summary['plan'] is not None
    assert 'outstanding_balance' in summary
    assert 'total_spend' in summary
    assert isinstance(summary['recent_invoices'], list)
    assert isinstance(summary['recent_payments'], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
