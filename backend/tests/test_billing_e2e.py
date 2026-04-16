"""
End-to-End Tests: Billing System
Phase 2.3.1: Integration Testing

Test Scenarios:
1. Subscription Lifecycle (create → invoice → payment → renewal)
2. Plan Upgrade/Downgrade
3. Trial Period → Active Subscription
4. Subscription Cancellation
5. Invoice Generation & Payment Processing
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
import asyncpg

# Test configuration
TEST_DB_URL = "postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db"


@pytest.fixture(scope="module")
async def db_pool():
    """Create database connection pool for tests"""
    pool = await asyncpg.create_pool(TEST_DB_URL, min_size=1, max_size=5)
    yield pool
    await pool.close()


@pytest.fixture
async def test_org(db_pool):
    """Create test organization"""
    org_id = uuid4()
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO organizations (id, name, slug, status)
            VALUES ($1, $2, $3, $4)
        """, org_id, "Test Billing Org", "test-billing", "active")
    
    yield org_id
    
    # Cleanup
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM organizations WHERE id = $1", org_id)


@pytest.fixture
async def starter_plan_id(db_pool):
    """Get Starter plan ID"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id FROM subscription_plans WHERE slug = 'starter'
        """)
        return row['id']


@pytest.fixture
async def professional_plan_id(db_pool):
    """Get Professional plan ID"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id FROM subscription_plans WHERE slug = 'professional'
        """)
        return row['id']


# ============================================
# TEST 1: Complete Subscription Lifecycle
# ============================================

@pytest.mark.asyncio
async def test_subscription_lifecycle(db_pool, test_org, starter_plan_id):
    """
    Test complete subscription lifecycle:
    1. Create subscription (trial)
    2. Trial expires → active
    3. Generate invoice
    4. Process payment
    5. Next billing cycle
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Create subscription with trial
        subscription_id = uuid4()
        now = datetime.now()
        trial_end = now + timedelta(days=14)
        period_end = trial_end
        
        await conn.execute("""
            INSERT INTO subscriptions (
                id, organization_id, plan_id, status,
                trial_start_date, trial_end_date,
                start_date, current_period_start, current_period_end,
                billing_cycle, next_billing_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, subscription_id, test_org, starter_plan_id, 'trial',
             now, trial_end, now, now, period_end, 'monthly', trial_end)
        
        # Verify subscription created
        row = await conn.fetchrow("""
            SELECT status, trial_start_date, trial_end_date
            FROM subscriptions WHERE id = $1
        """, subscription_id)
        
        assert row['status'] == 'trial'
        assert row['trial_start_date'] is not None
        assert row['trial_end_date'] is not None
        
        # Step 2: Trial expires → change to active
        await conn.execute("""
            UPDATE subscriptions
            SET status = 'active', current_period_start = $2, current_period_end = $3
            WHERE id = $1
        """, subscription_id, trial_end, trial_end + timedelta(days=30))
        
        row = await conn.fetchrow("""
            SELECT status FROM subscriptions WHERE id = $1
        """, subscription_id)
        assert row['status'] == 'active'
        
        # Step 3: Generate invoice
        invoice_id = uuid4()
        invoice_number = f"INV-2026-{subscription_id.hex[:6].upper()}"
        
        await conn.execute("""
            INSERT INTO invoices (
                id, invoice_number, organization_id, subscription_id,
                status, subtotal, tax, discount, total, amount_due,
                currency, issue_date, due_date, period_start, period_end
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """, invoice_id, invoice_number, test_org, subscription_id,
             'open', Decimal('99.00'), Decimal('0'), Decimal('0'), 
             Decimal('99.00'), Decimal('99.00'), 'USD',
             date.today(), date.today() + timedelta(days=7),
             trial_end.date(), (trial_end + timedelta(days=30)).date())
        
        # Add line item
        await conn.execute("""
            INSERT INTO invoice_line_items (
                invoice_id, description, item_type, quantity,
                unit_price, amount, tax_rate, tax_amount
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, invoice_id, "Starter Plan - Monthly", "subscription",
             Decimal('1'), Decimal('99.00'), Decimal('99.00'),
             Decimal('0'), Decimal('0'))
        
        # Verify invoice created
        row = await conn.fetchrow("""
            SELECT status, total, amount_due FROM invoices WHERE id = $1
        """, invoice_id)
        
        assert row['status'] == 'open'
        assert row['total'] == Decimal('99.00')
        assert row['amount_due'] == Decimal('99.00')
        
        # Step 4: Process payment
        payment_id = uuid4()
        payment_number = f"PAY-2026-{payment_id.hex[:6].upper()}"
        
        await conn.execute("""
            INSERT INTO payments (
                id, payment_number, invoice_id, organization_id,
                amount, currency, status, payment_method, payment_gateway,
                paid_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, payment_id, payment_number, invoice_id, test_org,
             Decimal('99.00'), 'USD', 'succeeded', 'card', 'stripe',
             datetime.now())
        
        # Update invoice as paid
        await conn.execute("""
            UPDATE invoices
            SET status = 'paid', amount_paid = $2, amount_due = 0, paid_at = $3
            WHERE id = $1
        """, invoice_id, Decimal('99.00'), datetime.now())
        
        # Verify payment succeeded
        row = await conn.fetchrow("""
            SELECT status, amount FROM payments WHERE id = $1
        """, payment_id)
        assert row['status'] == 'succeeded'
        assert row['amount'] == Decimal('99.00')
        
        # Verify invoice paid
        row = await conn.fetchrow("""
            SELECT status, amount_paid, amount_due FROM invoices WHERE id = $1
        """, invoice_id)
        assert row['status'] == 'paid'
        assert row['amount_paid'] == Decimal('99.00')
        assert row['amount_due'] == Decimal('0')
        
        # Step 5: Next billing cycle
        next_period_start = trial_end + timedelta(days=30)
        next_period_end = next_period_start + timedelta(days=30)
        
        await conn.execute("""
            UPDATE subscriptions
            SET current_period_start = $2, current_period_end = $3,
                next_billing_date = $4
            WHERE id = $1
        """, subscription_id, next_period_start, next_period_end, next_period_end)
        
        # Verify cycle updated
        row = await conn.fetchrow("""
            SELECT current_period_start, current_period_end, next_billing_date
            FROM subscriptions WHERE id = $1
        """, subscription_id)
        
        assert row['current_period_start'] == next_period_start
        assert row['current_period_end'] == next_period_end
        
        print("✅ Subscription lifecycle test PASSED")


# ============================================
# TEST 2: Plan Upgrade
# ============================================

@pytest.mark.asyncio
async def test_plan_upgrade(db_pool, test_org, starter_plan_id, professional_plan_id):
    """
    Test plan upgrade:
    1. Create subscription on Starter
    2. Upgrade to Professional
    3. Generate prorated invoice
    4. Verify plan changed
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Create Starter subscription
        subscription_id = uuid4()
        now = datetime.now()
        period_end = now + timedelta(days=30)
        
        await conn.execute("""
            INSERT INTO subscriptions (
                id, organization_id, plan_id, status,
                start_date, current_period_start, current_period_end,
                billing_cycle, next_billing_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, subscription_id, test_org, starter_plan_id, 'active',
             now, now, period_end, 'monthly', period_end)
        
        # Verify Starter plan
        row = await conn.fetchrow("""
            SELECT plan_id FROM subscriptions WHERE id = $1
        """, subscription_id)
        assert row['plan_id'] == starter_plan_id
        
        # Step 2: Upgrade to Professional
        await conn.execute("""
            UPDATE subscriptions
            SET plan_id = $2, updated_at = $3
            WHERE id = $1
        """, subscription_id, professional_plan_id, datetime.now())
        
        # Verify upgrade
        row = await conn.fetchrow("""
            SELECT plan_id FROM subscriptions WHERE id = $1
        """, subscription_id)
        assert row['plan_id'] == professional_plan_id
        
        # Step 3: Generate prorated invoice (simplified - full amount)
        invoice_id = uuid4()
        invoice_number = f"INV-2026-{invoice_id.hex[:6].upper()}"
        
        await conn.execute("""
            INSERT INTO invoices (
                id, invoice_number, organization_id, subscription_id,
                status, subtotal, total, amount_due, currency,
                issue_date, due_date, description
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """, invoice_id, invoice_number, test_org, subscription_id,
             'open', Decimal('299.00'), Decimal('299.00'), Decimal('299.00'), 'USD',
             date.today(), date.today() + timedelta(days=7),
             "Upgrade to Professional Plan (prorated)")
        
        # Verify invoice for upgrade
        row = await conn.fetchrow("""
            SELECT total, description FROM invoices WHERE id = $1
        """, invoice_id)
        assert row['total'] == Decimal('299.00')
        assert 'Professional' in row['description']
        
        print("✅ Plan upgrade test PASSED")


# ============================================
# TEST 3: Subscription Cancellation
# ============================================

@pytest.mark.asyncio
async def test_subscription_cancellation(db_pool, test_org, starter_plan_id):
    """
    Test subscription cancellation:
    1. Create active subscription
    2. Cancel subscription
    3. Verify status = cancelled
    4. Verify cancelled_at set
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Create active subscription
        subscription_id = uuid4()
        now = datetime.now()
        period_end = now + timedelta(days=30)
        
        await conn.execute("""
            INSERT INTO subscriptions (
                id, organization_id, plan_id, status,
                start_date, current_period_start, current_period_end,
                billing_cycle
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, subscription_id, test_org, starter_plan_id, 'active',
             now, now, period_end, 'monthly')
        
        # Step 2: Cancel subscription
        cancelled_at = datetime.now()
        await conn.execute("""
            UPDATE subscriptions
            SET status = 'cancelled', cancelled_at = $2, updated_at = $3
            WHERE id = $1
        """, subscription_id, cancelled_at, datetime.now())
        
        # Step 3 & 4: Verify cancellation
        row = await conn.fetchrow("""
            SELECT status, cancelled_at FROM subscriptions WHERE id = $1
        """, subscription_id)
        
        assert row['status'] == 'cancelled'
        assert row['cancelled_at'] is not None
        assert row['cancelled_at'].date() == cancelled_at.date()
        
        print("✅ Subscription cancellation test PASSED")


# ============================================
# TEST 4: Invoice Generation & Payment
# ============================================

@pytest.mark.asyncio
async def test_invoice_payment_flow(db_pool, test_org):
    """
    Test invoice payment flow:
    1. Create invoice (open)
    2. Process payment (succeeded)
    3. Verify invoice status = paid
    4. Verify payment recorded
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Create invoice
        invoice_id = uuid4()
        invoice_number = f"INV-2026-TEST-{invoice_id.hex[:6].upper()}"
        
        await conn.execute("""
            INSERT INTO invoices (
                id, invoice_number, organization_id, status,
                subtotal, total, amount_due, currency,
                issue_date, due_date, description
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, invoice_id, invoice_number, test_org, 'open',
             Decimal('100.00'), Decimal('100.00'), Decimal('100.00'), 'USD',
             date.today(), date.today() + timedelta(days=7),
             "Test Invoice")
        
        # Verify invoice open
        row = await conn.fetchrow("""
            SELECT status, amount_due FROM invoices WHERE id = $1
        """, invoice_id)
        assert row['status'] == 'open'
        assert row['amount_due'] == Decimal('100.00')
        
        # Step 2: Process payment
        payment_id = uuid4()
        payment_number = f"PAY-2026-TEST-{payment_id.hex[:6].upper()}"
        paid_at = datetime.now()
        
        await conn.execute("""
            INSERT INTO payments (
                id, payment_number, invoice_id, organization_id,
                amount, currency, status, payment_method,
                payment_gateway, paid_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, payment_id, payment_number, invoice_id, test_org,
             Decimal('100.00'), 'USD', 'succeeded', 'card',
             'manual', paid_at)
        
        # Update invoice
        await conn.execute("""
            UPDATE invoices
            SET status = 'paid', amount_paid = $2, amount_due = 0, paid_at = $3
            WHERE id = $1
        """, invoice_id, Decimal('100.00'), paid_at)
        
        # Step 3: Verify invoice paid
        row = await conn.fetchrow("""
            SELECT status, amount_paid, amount_due, paid_at
            FROM invoices WHERE id = $1
        """, invoice_id)
        
        assert row['status'] == 'paid'
        assert row['amount_paid'] == Decimal('100.00')
        assert row['amount_due'] == Decimal('0')
        assert row['paid_at'] is not None
        
        # Step 4: Verify payment recorded
        row = await conn.fetchrow("""
            SELECT status, amount FROM payments WHERE id = $1
        """, payment_id)
        
        assert row['status'] == 'succeeded'
        assert row['amount'] == Decimal('100.00')
        
        print("✅ Invoice payment flow test PASSED")


# ============================================
# TEST 5: Transaction Fees
# ============================================

@pytest.mark.asyncio
async def test_transaction_fees(db_pool, test_org):
    """
    Test transaction fees:
    1. Create transaction fee (withdrawal 2.5%)
    2. Verify fee calculated correctly
    3. Mark as invoiced
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Create transaction fee
        fee_id = uuid4()
        base_amount = Decimal('1000.00')  # $1000 withdrawal
        fee_rate = Decimal('0.025')  # 2.5%
        fee_amount = base_amount * fee_rate  # $25.00
        
        await conn.execute("""
            INSERT INTO transaction_fees (
                id, organization_id, transaction_type, fee_type,
                fee_amount, currency, base_amount, fee_rate,
                status, transaction_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, fee_id, test_org, 'withdrawal', 'percentage',
             fee_amount, 'USD', base_amount, fee_rate,
             'pending', datetime.now())
        
        # Step 2: Verify fee calculated
        row = await conn.fetchrow("""
            SELECT fee_amount, base_amount, fee_rate
            FROM transaction_fees WHERE id = $1
        """, fee_id)
        
        assert row['fee_amount'] == Decimal('25.00')
        assert row['base_amount'] == Decimal('1000.00')
        assert row['fee_rate'] == Decimal('0.025')
        
        # Step 3: Mark as invoiced
        await conn.execute("""
            UPDATE transaction_fees
            SET status = 'invoiced', invoiced_at = $2
            WHERE id = $1
        """, fee_id, datetime.now())
        
        row = await conn.fetchrow("""
            SELECT status, invoiced_at FROM transaction_fees WHERE id = $1
        """, fee_id)
        
        assert row['status'] == 'invoiced'
        assert row['invoiced_at'] is not None
        
        print("✅ Transaction fees test PASSED")


# ============================================
# RUN ALL TESTS
# ============================================

if __name__ == "__main__":
    import asyncio
    
    print("Running Billing E2E Tests...")
    print("=" * 60)
    
    asyncio.run(test_subscription_lifecycle(None, None, None))
    # Note: Run with pytest for proper fixture support
    
    print("=" * 60)
    print("All tests completed. Run with: pytest test_billing_e2e.py -v")
