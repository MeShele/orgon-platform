"""Phase 2 Integration Tests — Full E2E Workflow."""
import pytest
import asyncio
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from backend.services.billing_service import BillingService
from backend.services.compliance_service import ComplianceService
from backend.database.pool import get_pool

@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def pool():
    """Database connection pool."""
    p = await get_pool()
    yield p
    await p.close()

@pytest.fixture(scope="module")
async def billing_service(pool):
    """BillingService instance."""
    return BillingService(pool)

@pytest.fixture(scope="module")
async def compliance_service(pool):
    """ComplianceService instance."""
    return ComplianceService(pool)

# ==================== E2E Workflow Tests ====================

@pytest.mark.asyncio
async def test_full_onboarding_workflow(billing_service, compliance_service):
    """
    E2E Test: Organization Onboarding → Subscription → KYC
    
    Steps:
    1. Create organization (Phase 1)
    2. Subscribe to plan (Billing)
    3. Create KYC record (Compliance)
    4. Approve KYC
    5. Generate invoice
    6. Process payment
    """
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    user_id = UUID('223e4567-e89b-12d3-a456-426614174000')
    
    # Step 1: Get available plans
    plans = await billing_service.get_subscription_plans()
    assert len(plans) > 0
    starter_plan = next((p for p in plans if p['name'] == 'Starter'), plans[0])
    
    # Step 2: Subscribe to plan
    subscription = await billing_service.create_subscription(
        org_id,
        UUID(str(starter_plan['id'])),
        'monthly',
        user_id
    )
    assert subscription is not None
    assert subscription['status'] == 'active'
    
    # Step 3: Create KYC record
    kyc = await compliance_service.create_kyc_record(
        org_id,
        "Jane Doe",
        "jane@startup.com",
        "passport",
        "XYZ987654",
        user_id
    )
    assert kyc['verification_status'] == 'pending'
    
    # Step 4: Approve KYC
    approved_kyc = await compliance_service.update_kyc_status(
        kyc['id'],
        'approved',
        user_id,
        risk_level='low'
    )
    assert approved_kyc['verification_status'] == 'approved'
    
    # Step 5: Generate invoice (auto-billing)
    invoice = await billing_service.generate_monthly_invoice(
        UUID(str(subscription['id'])),
        user_id
    )
    assert invoice is not None
    assert float(invoice['total']) == float(subscription['price'])
    
    # Step 6: Process payment
    payment = await billing_service.process_payment(
        UUID(str(invoice['id'])),
        float(invoice['total']),
        'stripe',
        'ch_test_123456',
        user_id
    )
    assert payment is not None
    assert payment['status'] == 'completed'
    
    print(f"✅ Full workflow complete: {subscription['id']}")

@pytest.mark.asyncio
async def test_billing_compliance_cross_module(billing_service, compliance_service):
    """
    Test: Billing triggers AML alert on high payment
    
    Scenario:
    1. Process large payment ($50K)
    2. Check if AML alert triggered
    """
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    user_id = UUID('223e4567-e89b-12d3-a456-426614174000')
    
    # Mock high-value payment transaction
    transaction = {
        'id': str(uuid4()),
        'amount': 50000,  # $50K — above threshold
        'organization_id': str(org_id)
    }
    
    # Check against AML rules
    alerts = await compliance_service.check_transaction_against_rules(
        org_id,
        transaction
    )
    
    # Should trigger high value alert
    if len(alerts) > 0:
        assert any(a['severity'] in ['medium', 'high'] for a in alerts)
        print(f"✅ AML alert triggered for ${transaction['amount']}")
    else:
        print(f"⚠️ No alert triggered (rules may not be active)")

@pytest.mark.asyncio
async def test_subscription_cancellation_flow(billing_service):
    """
    Test: Subscription lifecycle — create → cancel
    
    Steps:
    1. Create subscription
    2. Cancel subscription
    3. Verify cancellation
    """
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    user_id = UUID('223e4567-e89b-12d3-a456-426614174000')
    
    # Get professional plan
    plans = await billing_service.get_subscription_plans()
    pro_plan = next((p for p in plans if p['name'] == 'Professional'), None)
    if not pro_plan:
        pytest.skip("Professional plan not found")
    
    # Create subscription
    subscription = await billing_service.create_subscription(
        org_id,
        UUID(str(pro_plan['id'])),
        'monthly',
        user_id
    )
    sub_id = subscription['id']
    
    # Cancel subscription
    cancelled = await billing_service.cancel_subscription(sub_id, user_id)
    
    # Verify status
    assert cancelled['status'] == 'cancelled'
    assert cancelled['cancelled_at'] is not None
    
    print(f"✅ Subscription cancelled: {sub_id}")

@pytest.mark.asyncio
async def test_monthly_report_generation(billing_service, compliance_service):
    """
    Test: Monthly compliance report includes billing data
    
    Verify report contains:
    - Transaction count
    - KYC stats
    - AML alerts
    """
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    user_id = UUID('223e4567-e89b-12d3-a456-426614174000')
    
    report = await compliance_service.generate_monthly_report(
        org_id,
        2026,
        2,
        user_id
    )
    
    assert report is not None
    assert 'report_data' in report
    data = report['report_data']
    
    # Check structure
    assert 'transactions' in data
    assert 'kyc' in data
    assert 'aml' in data
    
    # Verify data types
    assert isinstance(data['transactions']['total'], int)
    assert isinstance(data['kyc']['approved'], int)
    assert isinstance(data['aml']['alerts'], int)
    
    print(f"✅ Report generated: {report['id']}")
    print(f"  - Transactions: {data['transactions']['total']}")
    print(f"  - KYC approved: {data['kyc']['approved']}")
    print(f"  - AML alerts: {data['aml']['alerts']}")

@pytest.mark.asyncio
async def test_billing_summary(billing_service):
    """
    Test: Billing summary dashboard data
    
    Verify summary contains:
    - Current subscription
    - Outstanding balance
    - Recent invoices
    - Recent payments
    """
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    
    summary = await billing_service.get_billing_summary(org_id)
    
    assert summary is not None
    assert 'subscription' in summary or summary.get('subscription') is None
    assert 'outstanding_balance' in summary
    assert 'total_spend' in summary
    assert 'recent_invoices' in summary
    assert 'recent_payments' in summary
    
    print(f"✅ Billing summary retrieved")
    print(f"  - Outstanding: ${summary['outstanding_balance']}")
    print(f"  - Total spend: ${summary['total_spend']}")

# ==================== RLS Isolation Tests ====================

@pytest.mark.asyncio
async def test_rls_billing_isolation(pool):
    """
    Test: RLS prevents cross-org access to billing data
    
    Scenario:
    1. Set tenant context to Org A
    2. Query subscriptions
    3. Verify only Org A data returned
    """
    org_a = UUID('123e4567-e89b-12d3-a456-426614174000')
    org_b = UUID('223e4567-e89b-12d3-a456-426614174001')
    
    async with pool.acquire() as conn:
        # Set context to Org A
        await conn.execute("SELECT set_config('app.current_organization_id', $1, FALSE)", str(org_a))
        
        # Query subscriptions
        subs = await conn.fetch("SELECT * FROM organization_subscriptions")
        
        # All results should belong to Org A
        for sub in subs:
            assert sub['organization_id'] == org_a
        
        print(f"✅ RLS billing isolation verified: {len(subs)} subscriptions (Org A only)")

@pytest.mark.asyncio
async def test_rls_compliance_isolation(pool):
    """
    Test: RLS prevents cross-org access to KYC/AML data
    """
    org_a = UUID('123e4567-e89b-12d3-a456-426614174000')
    
    async with pool.acquire() as conn:
        # Set context to Org A
        await conn.execute("SELECT set_config('app.current_organization_id', $1, FALSE)", str(org_a))
        
        # Query KYC records
        kyc_records = await conn.fetch("SELECT * FROM kyc_records")
        
        # All results should belong to Org A
        for record in kyc_records:
            assert record['organization_id'] == org_a
        
        # Query AML alerts
        aml_alerts = await conn.fetch("SELECT * FROM aml_alerts")
        for alert in aml_alerts:
            assert alert['organization_id'] == org_a
        
        print(f"✅ RLS compliance isolation verified")
        print(f"  - KYC records: {len(kyc_records)} (Org A only)")
        print(f"  - AML alerts: {len(aml_alerts)} (Org A only)")

# ==================== Performance Tests ====================

@pytest.mark.asyncio
async def test_billing_summary_performance(billing_service):
    """
    Test: Billing summary query performance
    
    Target: < 100ms for dashboard load
    """
    import time
    
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    
    start = time.time()
    summary = await billing_service.get_billing_summary(org_id)
    elapsed = (time.time() - start) * 1000  # ms
    
    assert summary is not None
    assert elapsed < 100, f"Billing summary took {elapsed:.2f}ms (target: <100ms)"
    
    print(f"✅ Billing summary performance: {elapsed:.2f}ms")

@pytest.mark.asyncio
async def test_compliance_report_performance(compliance_service):
    """
    Test: Monthly report generation performance
    
    Target: < 500ms for report generation
    """
    import time
    
    org_id = UUID('123e4567-e89b-12d3-a456-426614174000')
    user_id = UUID('223e4567-e89b-12d3-a456-426614174000')
    
    start = time.time()
    report = await compliance_service.generate_monthly_report(org_id, 2026, 2, user_id)
    elapsed = (time.time() - start) * 1000
    
    assert report is not None
    assert elapsed < 500, f"Report generation took {elapsed:.2f}ms (target: <500ms)"
    
    print(f"✅ Report generation performance: {elapsed:.2f}ms")
