"""
End-to-End Tests: Compliance System
Phase 2.3.1: Integration Testing

Test Scenarios:
1. KYC Verification Flow (submit → review → approve)
2. AML Alert Flow (detect → investigate → resolve)
3. Compliance Report Generation
4. Sanctioned Address Check
5. Transaction Monitoring Rules
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4
import asyncpg
import json

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
        """, org_id, "Test Compliance Org", "test-compliance", "active")
    
    yield org_id
    
    # Cleanup
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM organizations WHERE id = $1", org_id)


# ============================================
# TEST 1: KYC Verification Flow
# ============================================

@pytest.mark.asyncio
async def test_kyc_verification_flow(db_pool, test_org):
    """
    Test complete KYC verification:
    1. Submit KYC record (pending)
    2. Move to in_review
    3. Approve KYC
    4. Verify status history
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Submit KYC record
        kyc_id = uuid4()
        customer_id = f"CUST-{uuid4().hex[:8].upper()}"
        
        await conn.execute("""
            INSERT INTO kyc_records (
                id, organization_id, customer_id, customer_name,
                customer_email, status, risk_level,
                kyc_provider, documents_submitted
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, kyc_id, test_org, customer_id, "John Doe",
             "john.doe@example.com", "pending", "unknown",
             "manual", json.dumps({
                 "passport": {"provided": True, "verified": False},
                 "address_proof": {"provided": True, "verified": False}
             }))
        
        # Verify pending status
        row = await conn.fetchrow("""
            SELECT status, risk_level FROM kyc_records WHERE id = $1
        """, kyc_id)
        assert row['status'] == 'pending'
        assert row['risk_level'] == 'unknown'
        
        # Step 2: Move to in_review
        await conn.execute("""
            UPDATE kyc_records
            SET status = 'in_review', updated_at = $2
            WHERE id = $1
        """, kyc_id, datetime.now())
        
        row = await conn.fetchrow("""
            SELECT status FROM kyc_records WHERE id = $1
        """, kyc_id)
        assert row['status'] == 'in_review'
        
        # Step 3: Approve KYC
        verified_at = datetime.now()
        await conn.execute("""
            UPDATE kyc_records
            SET status = 'approved', risk_level = 'low',
                verified_at = $2, verified_by = $3,
                risk_factors = $4, updated_at = $5
            WHERE id = $1
        """, kyc_id, verified_at, "compliance_officer_1",
             json.dumps({
                 "identity_verified": True,
                 "address_verified": True,
                 "sanctions_check": "clear",
                 "pep_check": "clear"
             }), datetime.now())
        
        # Step 4: Verify approval
        row = await conn.fetchrow("""
            SELECT status, risk_level, verified_at, verified_by, risk_factors
            FROM kyc_records WHERE id = $1
        """, kyc_id)
        
        assert row['status'] == 'approved'
        assert row['risk_level'] == 'low'
        assert row['verified_at'] is not None
        assert row['verified_by'] == 'compliance_officer_1'
        
        risk_factors = json.loads(row['risk_factors'])
        assert risk_factors['identity_verified'] is True
        assert risk_factors['sanctions_check'] == 'clear'
        
        print("✅ KYC verification flow test PASSED")


# ============================================
# TEST 2: AML Alert Flow
# ============================================

@pytest.mark.asyncio
async def test_aml_alert_flow(db_pool, test_org):
    """
    Test AML alert lifecycle:
    1. Create AML alert (suspicious transaction)
    2. Assign to investigator
    3. Investigate & add notes
    4. Resolve alert
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Create AML alert
        alert_id = uuid4()
        transaction_id = uuid4()
        
        await conn.execute("""
            INSERT INTO aml_alerts (
                id, organization_id, alert_type, severity,
                status, transaction_id, amount, currency,
                description, detected_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, alert_id, test_org, 'suspicious_transaction', 'high',
             'open', transaction_id, Decimal('150000.00'), 'USD',
             'Large transaction from high-risk jurisdiction',
             datetime.now())
        
        # Verify alert created
        row = await conn.fetchrow("""
            SELECT status, severity, alert_type
            FROM aml_alerts WHERE id = $1
        """, alert_id)
        
        assert row['status'] == 'open'
        assert row['severity'] == 'high'
        assert row['alert_type'] == 'suspicious_transaction'
        
        # Step 2: Assign to investigator
        await conn.execute("""
            UPDATE aml_alerts
            SET assigned_to = $2, status = 'investigating', updated_at = $3
            WHERE id = $1
        """, alert_id, 'investigator_1', datetime.now())
        
        row = await conn.fetchrow("""
            SELECT status, assigned_to FROM aml_alerts WHERE id = $1
        """, alert_id)
        assert row['status'] == 'investigating'
        assert row['assigned_to'] == 'investigator_1'
        
        # Step 3: Add investigation notes
        await conn.execute("""
            UPDATE aml_alerts
            SET investigation_notes = $2, updated_at = $3
            WHERE id = $1
        """, alert_id, "Verified customer identity and source of funds. Transaction legitimate - business payment.", datetime.now())
        
        # Step 4: Resolve alert
        resolved_at = datetime.now()
        await conn.execute("""
            UPDATE aml_alerts
            SET status = 'resolved', resolution = $2,
                resolved_at = $3, resolved_by = $4,
                requires_sar = $5, updated_at = $6
            WHERE id = $1
        """, alert_id, 'false_positive', resolved_at, 'investigator_1',
             False, datetime.now())
        
        # Verify resolution
        row = await conn.fetchrow("""
            SELECT status, resolution, resolved_at, resolved_by, requires_sar
            FROM aml_alerts WHERE id = $1
        """, alert_id)
        
        assert row['status'] == 'resolved'
        assert row['resolution'] == 'false_positive'
        assert row['resolved_at'] is not None
        assert row['resolved_by'] == 'investigator_1'
        assert row['requires_sar'] is False
        
        print("✅ AML alert flow test PASSED")


# ============================================
# TEST 3: Compliance Report Generation
# ============================================

@pytest.mark.asyncio
async def test_compliance_report_generation(db_pool, test_org):
    """
    Test compliance report generation:
    1. Generate monthly report
    2. Verify report data
    3. Mark as submitted to regulator
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Generate monthly report
        report_id = uuid4()
        report_number = f"COMP-{date.today().strftime('%Y%m')}-{report_id.hex[:6].upper()}"
        
        report_data = {
            "summary": {
                "total_transactions": 450,
                "total_volume": "2500000.00",
                "kyc_approved": 25,
                "kyc_rejected": 2,
                "aml_alerts": 5,
                "aml_resolved": 4
            },
            "transactions": {
                "deposits": 200,
                "withdrawals": 150,
                "exchanges": 100
            },
            "risk_assessment": {
                "high_risk_transactions": 5,
                "medium_risk_transactions": 20,
                "low_risk_transactions": 425
            }
        }
        
        await conn.execute("""
            INSERT INTO compliance_reports (
                id, report_number, organization_id, report_type,
                period_start, period_end, status, report_data,
                generated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, report_id, report_number, test_org, 'monthly_transactions',
             date.today().replace(day=1), date.today(),
             'draft', json.dumps(report_data), datetime.now())
        
        # Step 2: Verify report data
        row = await conn.fetchrow("""
            SELECT status, report_type, report_data
            FROM compliance_reports WHERE id = $1
        """, report_id)
        
        assert row['status'] == 'draft'
        assert row['report_type'] == 'monthly_transactions'
        
        data = json.loads(row['report_data'])
        assert data['summary']['total_transactions'] == 450
        assert data['summary']['kyc_approved'] == 25
        
        # Step 3: Mark as submitted
        submitted_at = datetime.now()
        await conn.execute("""
            UPDATE compliance_reports
            SET status = 'submitted', submitted_at = $2,
                submitted_to = $3, updated_at = $4
            WHERE id = $1
        """, report_id, submitted_at, 'National Bank of Kyrgyzstan',
             datetime.now())
        
        # Verify submission
        row = await conn.fetchrow("""
            SELECT status, submitted_at, submitted_to
            FROM compliance_reports WHERE id = $1
        """, report_id)
        
        assert row['status'] == 'submitted'
        assert row['submitted_at'] is not None
        assert row['submitted_to'] == 'National Bank of Kyrgyzstan'
        
        print("✅ Compliance report generation test PASSED")


# ============================================
# TEST 4: Sanctioned Address Check
# ============================================

@pytest.mark.asyncio
async def test_sanctioned_address_check(db_pool, test_org):
    """
    Test sanctioned address blocking:
    1. Add sanctioned address to blocklist
    2. Check transaction against blocklist
    3. Verify block action
    """
    
    async with db_pool.acquire() as conn:
        # Step 1: Add sanctioned address
        sanction_id = uuid4()
        sanctioned_address = "0x1234567890abcdef1234567890abcdef12345678"
        
        await conn.execute("""
            INSERT INTO sanctioned_addresses (
                id, address, blockchain, sanction_type,
                listed_by, reason, is_active, listed_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, sanction_id, sanctioned_address, 'ethereum',
             'terrorism', 'OFAC', 'Associated with terrorist organization',
             True, datetime.now())
        
        # Verify address added
        row = await conn.fetchrow("""
            SELECT address, is_active, sanction_type
            FROM sanctioned_addresses WHERE id = $1
        """, sanction_id)
        
        assert row['address'] == sanctioned_address
        assert row['is_active'] is True
        assert row['sanction_type'] == 'terrorism'
        
        # Step 2: Check transaction against blocklist
        # (In real implementation, this would be in transaction processing logic)
        check_result = await conn.fetchrow("""
            SELECT EXISTS(
                SELECT 1 FROM sanctioned_addresses
                WHERE address = $1 AND is_active = true
            ) as is_sanctioned
        """, sanctioned_address)
        
        # Step 3: Verify block action
        assert check_result['is_sanctioned'] is True
        
        # Create AML alert for blocked transaction
        alert_id = uuid4()
        await conn.execute("""
            INSERT INTO aml_alerts (
                id, organization_id, alert_type, severity,
                status, description, detected_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, alert_id, test_org, 'sanctioned_address', 'critical',
             'blocked', f'Transaction blocked - sanctioned address {sanctioned_address}',
             datetime.now())
        
        # Verify alert created
        row = await conn.fetchrow("""
            SELECT alert_type, severity, status
            FROM aml_alerts WHERE id = $1
        """, alert_id)
        
        assert row['alert_type'] == 'sanctioned_address'
        assert row['severity'] == 'critical'
        assert row['status'] == 'blocked'
        
        print("✅ Sanctioned address check test PASSED")


# ============================================
# TEST 5: Transaction Monitoring Rules
# ============================================

@pytest.mark.asyncio
async def test_transaction_monitoring_rules(db_pool, test_org):
    """
    Test transaction monitoring:
    1. Check high value rule (threshold)
    2. Check rapid succession rule (velocity)
    3. Verify alert creation
    """
    
    async with db_pool.acquire() as conn:
        # Get high value rule
        rule = await conn.fetchrow("""
            SELECT id, rule_config FROM transaction_monitoring_rules
            WHERE rule_type = 'threshold' AND is_active = true
            LIMIT 1
        """)
        
        assert rule is not None
        
        # Step 1: Test high value transaction
        test_amount = Decimal('15000.00')  # Above $10K threshold
        rule_config = json.loads(rule['rule_config'])
        threshold = Decimal(rule_config['threshold_usd'])
        
        if test_amount > threshold:
            # Create alert
            alert_id = uuid4()
            await conn.execute("""
                INSERT INTO aml_alerts (
                    id, organization_id, alert_type, severity,
                    status, amount, currency, description, detected_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, alert_id, test_org, 'high_value', 'medium',
                 'open', test_amount, 'USD',
                 f'High value transaction detected: ${test_amount}',
                 datetime.now())
            
            # Verify alert
            row = await conn.fetchrow("""
                SELECT alert_type, amount FROM aml_alerts WHERE id = $1
            """, alert_id)
            
            assert row['alert_type'] == 'high_value'
            assert row['amount'] == test_amount
        
        # Step 2: Test rapid succession (simulate multiple transactions)
        # In real implementation, this would check transaction history
        rapid_tx_count = 12  # More than 10 per hour
        if rapid_tx_count > 10:
            alert_id = uuid4()
            await conn.execute("""
                INSERT INTO aml_alerts (
                    id, organization_id, alert_type, severity,
                    status, description, detected_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, alert_id, test_org, 'rapid_movement', 'medium',
                 'open', f'Rapid transaction pattern detected: {rapid_tx_count} transactions in 1 hour',
                 datetime.now())
            
            # Verify alert
            row = await conn.fetchrow("""
                SELECT alert_type FROM aml_alerts WHERE id = $1
            """, alert_id)
            
            assert row['alert_type'] == 'rapid_movement'
        
        print("✅ Transaction monitoring rules test PASSED")


# ============================================
# RUN ALL TESTS
# ============================================

if __name__ == "__main__":
    import asyncio
    
    print("Running Compliance E2E Tests...")
    print("=" * 60)
    
    # Note: Run with pytest for proper fixture support
    print("Run with: pytest test_compliance_e2e.py -v")
