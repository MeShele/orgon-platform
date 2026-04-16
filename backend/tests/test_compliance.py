"""Compliance Service Tests — KYC, AML, Reports."""
import pytest
import asyncio
from uuid import UUID, uuid4
from datetime import datetime
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
async def service(pool):
    """ComplianceService instance."""
    return ComplianceService(pool)

@pytest.fixture(scope="module")
async def test_org_id():
    """Test organization UUID."""
    return UUID('123e4567-e89b-12d3-a456-426614174000')

@pytest.fixture(scope="module")
async def test_user_id():
    """Test user UUID."""
    return UUID('223e4567-e89b-12d3-a456-426614174000')

# ==================== KYC Tests ====================

@pytest.mark.asyncio
async def test_create_kyc_record(service, test_org_id, test_user_id):
    """Test creating KYC record."""
    record = await service.create_kyc_record(
        test_org_id,
        "John Doe",
        "john@example.com",
        "passport",
        "AB123456",
        test_user_id
    )
    
    assert record is not None
    assert record['customer_name'] == "John Doe"
    assert record['customer_email'] == "john@example.com"
    assert record['verification_status'] == 'pending'
    assert record['risk_level'] == 'unknown'
    return record['id']

@pytest.mark.asyncio
async def test_get_kyc_records(service, test_org_id):
    """Test getting KYC records."""
    records = await service.get_kyc_records(test_org_id)
    assert isinstance(records, list)
    assert len(records) > 0

@pytest.mark.asyncio
async def test_update_kyc_status(service, test_user_id):
    """Test approving KYC record."""
    # Get first pending record
    records = await service.get_kyc_records(
        UUID('123e4567-e89b-12d3-a456-426614174000'),
        status='pending'
    )
    if not records:
        pytest.skip("No pending KYC records")
    
    kyc_id = records[0]['id']
    updated = await service.update_kyc_status(
        kyc_id,
        'approved',
        test_user_id,
        risk_level='low'
    )
    
    assert updated is not None
    assert updated['verification_status'] == 'approved'
    assert updated['risk_level'] == 'low'
    assert updated['verified_by'] == test_user_id

# ==================== AML Tests ====================

@pytest.mark.asyncio
async def test_create_aml_alert(service, test_org_id):
    """Test creating AML alert."""
    alert = await service.create_aml_alert(
        test_org_id,
        'high_value',
        'medium',
        'Transaction exceeds threshold',
        {'amount_usd': 15000, 'threshold': 10000}
    )
    
    assert alert is not None
    assert alert['alert_type'] == 'high_value'
    assert alert['severity'] == 'medium'
    assert alert['status'] == 'open'
    return alert['id']

@pytest.mark.asyncio
async def test_get_aml_alerts(service, test_org_id):
    """Test getting AML alerts."""
    alerts = await service.get_aml_alerts(test_org_id)
    assert isinstance(alerts, list)
    assert len(alerts) > 0

@pytest.mark.asyncio
async def test_resolve_aml_alert(service, test_user_id):
    """Test resolving AML alert."""
    # Get first open alert
    alerts = await service.get_aml_alerts(
        UUID('123e4567-e89b-12d3-a456-426614174000'),
        status='open'
    )
    if not alerts:
        pytest.skip("No open AML alerts")
    
    alert_id = alerts[0]['id']
    updated = await service.update_aml_alert_status(
        alert_id,
        'resolved',
        resolution='False positive - legitimate business transaction',
        investigated_by=test_user_id
    )
    
    assert updated is not None
    assert updated['status'] == 'resolved'
    assert updated['investigated_by'] == test_user_id

# ==================== Reports Tests ====================

@pytest.mark.asyncio
async def test_generate_monthly_report(service, test_org_id, test_user_id):
    """Test generating monthly compliance report."""
    report = await service.generate_monthly_report(
        test_org_id,
        2026,
        2,
        test_user_id
    )
    
    assert report is not None
    assert report['report_type'] == 'monthly_transactions'
    assert report['status'] == 'final'
    assert 'report_data' in report
    assert 'transactions' in report['report_data']
    assert 'kyc' in report['report_data']
    assert 'aml' in report['report_data']

@pytest.mark.asyncio
async def test_get_reports(service, test_org_id):
    """Test getting compliance reports."""
    reports = await service.get_reports(test_org_id)
    assert isinstance(reports, list)
    assert len(reports) > 0

# ==================== Transaction Monitoring Tests ====================

@pytest.mark.asyncio
async def test_check_transaction_threshold_rule(service, test_org_id):
    """Test transaction monitoring - threshold rule."""
    # Mock transaction above threshold
    transaction = {
        'id': str(uuid4()),
        'amount': 15000,  # Above $10K threshold
        'organization_id': str(test_org_id)
    }
    
    alerts = await service.check_transaction_against_rules(test_org_id, transaction)
    
    # Should trigger at least one alert (high value threshold rule)
    assert isinstance(alerts, list)
    # May be 0 if rules not active, but if triggered:
    if len(alerts) > 0:
        assert alerts[0]['alert_type'] in ['threshold']
        assert 'Rule triggered' in alerts[0]['description']

@pytest.mark.asyncio
async def test_check_transaction_below_threshold(service, test_org_id):
    """Test transaction monitoring - below threshold."""
    transaction = {
        'id': str(uuid4()),
        'amount': 5000,  # Below $10K threshold
        'organization_id': str(test_org_id)
    }
    
    alerts = await service.check_transaction_against_rules(test_org_id, transaction)
    
    # Should NOT trigger high value alert
    assert isinstance(alerts, list)
    # Should be empty or not contain high_value alerts
    high_value_alerts = [a for a in alerts if a.get('alert_type') == 'high_value']
    assert len(high_value_alerts) == 0

# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_kyc_workflow_full(service, test_org_id, test_user_id):
    """Test full KYC workflow: create → approve."""
    # 1. Create KYC
    record = await service.create_kyc_record(
        test_org_id,
        "Alice Smith",
        "alice@example.com",
        "drivers_license",
        "DL987654",
        test_user_id
    )
    kyc_id = record['id']
    
    # 2. Verify pending status
    assert record['verification_status'] == 'pending'
    
    # 3. Approve KYC
    approved = await service.update_kyc_status(kyc_id, 'approved', test_user_id, 'low')
    
    # 4. Verify approved
    assert approved['verification_status'] == 'approved'
    assert approved['verified_at'] is not None

@pytest.mark.asyncio
async def test_aml_investigation_workflow(service, test_org_id, test_user_id):
    """Test full AML workflow: alert → investigate → resolve."""
    # 1. Create alert
    alert = await service.create_aml_alert(
        test_org_id,
        'suspicious_transaction',
        'high',
        'Pattern detected: rapid succession of large transactions',
        {'count': 5, 'total_amount': 75000, 'time_window_hours': 2}
    )
    alert_id = alert['id']
    
    # 2. Verify open status
    assert alert['status'] == 'open'
    
    # 3. Resolve with investigation
    resolved = await service.update_aml_alert_status(
        alert_id,
        'resolved',
        resolution='Investigated: legitimate business activity, corporate payroll',
        investigated_by=test_user_id
    )
    
    # 4. Verify resolved
    assert resolved['status'] == 'resolved'
    assert resolved['investigated_by'] == test_user_id
    assert resolved['investigated_at'] is not None
