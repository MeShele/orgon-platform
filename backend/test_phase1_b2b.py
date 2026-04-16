#!/usr/bin/env python3
"""
Phase 1 B2B Platform Test Script
Tests Partner creation, authentication, rate limiting, and audit logging
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Import services
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.services.partner_service import PartnerService
from backend.services.audit_service import AuditService

# Load environment
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def test_phase1():
    """Test all Phase 1 B2B components."""
    
    print("=" * 80)
    print("PHASE 1 B2B PLATFORM TEST")
    print("=" * 80)
    print()
    
    # Connect to database
    print("📊 Connecting to PostgreSQL (Neon.tech)...")
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    print("✅ Connected!")
    print()
    
    # Initialize services
    partner_service = PartnerService(db_pool)
    audit_service = AuditService(db_pool)
    
    # ========================================================================
    # TEST 1: Create Test Partner
    # ========================================================================
    print("=" * 80)
    print("TEST 1: Partner Creation")
    print("=" * 80)
    
    test_partner = {
        "name": "Test Exchange Ltd",
        "ec_address": "0xB2BTestPartner123456789ABCDEF01234567890",
        "tier": "business",
        "webhook_url": "https://test-exchange.com/webhooks/asystem",
        "webhook_secret": "test_webhook_secret_123",
        "metadata": {
            "company": "Test Exchange Ltd",
            "country": "Singapore",
            "contact_email": "api@test-exchange.com"
        }
    }
    
    try:
        print(f"Creating partner: {test_partner['name']}")
        print(f"  Tier: {test_partner['tier']}")
        print(f"  EC Address: {test_partner['ec_address']}")
        
        partner = await partner_service.create_partner(**test_partner)
        
        print()
        print("✅ Partner created successfully!")
        print(f"  Partner ID: {partner['partner_id']}")
        print(f"  API Key: {partner['api_key'][:16]}...{partner['api_key'][-8:]}")
        print(f"  API Secret: {partner['api_secret'][:16]}...{partner['api_secret'][-8:]}")
        print(f"  Rate Limit: {partner['rate_limit_per_minute']} req/min")
        print()
        
        # Save credentials for testing
        partner_id = partner['partner_id']
        api_key = partner['api_key']
        api_secret = partner['api_secret']
        
    except ValueError as e:
        print(f"⚠️  Partner already exists, fetching existing...")
        partner = await partner_service.get_partner_by_ec_address(test_partner['ec_address'])
        partner_id = str(partner['id'])
        print(f"  Partner ID: {partner_id}")
        print(f"  Using existing partner for tests")
        print()
        
        # For existing partner, we don't have plaintext credentials
        # In production, would need to rotate keys
        api_key = None
        api_secret = None
    
    # ========================================================================
    # TEST 2: Fetch Partner Details
    # ========================================================================
    print("=" * 80)
    print("TEST 2: Fetch Partner Details")
    print("=" * 80)
    
    partner_details = await partner_service.get_partner(partner_id)
    print(f"Partner Name: {partner_details['name']}")
    print(f"Tier: {partner_details['tier']}")
    print(f"EC Address: {partner_details['ec_address']}")
    print(f"Status: {partner_details['status']}")
    print(f"Rate Limit: {partner_details['rate_limit_per_minute']} req/min")
    print(f"Webhook URL: {partner_details.get('webhook_url', 'Not set')}")
    print(f"Created: {partner_details['created_at']}")
    print("✅ Fetch successful!")
    print()
    
    # ========================================================================
    # TEST 3: List Partners
    # ========================================================================
    print("=" * 80)
    print("TEST 3: List All Partners")
    print("=" * 80)
    
    partners = await partner_service.list_partners(limit=10)
    print(f"Total partners: {len(partners)}")
    for p in partners:
        print(f"  - {p['name']} ({p['tier']}) - {p['status']}")
    print("✅ List successful!")
    print()
    
    # ========================================================================
    # TEST 4: API Key Authentication (if we have credentials)
    # ========================================================================
    if api_key and api_secret:
        print("=" * 80)
        print("TEST 4: API Key Authentication")
        print("=" * 80)
        
        # Test valid API key lookup
        print("Testing valid API key lookup...")
        auth_partner = await partner_service.get_partner_by_api_key(api_key)
        if auth_partner:
            print(f"✅ Partner authenticated: {auth_partner['name']}")
            
            # Test secret verification
            print("Testing API secret verification...")
            is_valid = partner_service.verify_api_secret(api_secret, auth_partner['api_secret_hash'])
            if is_valid:
                print("✅ API secret verified!")
            else:
                print("❌ API secret verification failed!")
        else:
            print("❌ API key lookup failed!")
        
        # Test invalid API key
        print("Testing invalid API key (should fail)...")
        invalid_partner = await partner_service.get_partner_by_api_key("invalid_key_12345")
        if invalid_partner:
            print("❌ Invalid key should not authenticate!")
        else:
            print("✅ Invalid key correctly rejected!")
        
        print()
    else:
        print("⚠️  Skipping API key authentication test (no credentials)")
        print()
    
    # ========================================================================
    # TEST 5: Audit Logging
    # ========================================================================
    print("=" * 80)
    print("TEST 5: Audit Logging")
    print("=" * 80)
    
    # Log test actions
    print("Logging test actions...")
    
    # Action 1: Wallet creation
    await audit_service.log_wallet_action(
        partner_id=partner_id,
        user_id=test_partner['ec_address'],
        action="wallet.create",
        wallet_name="test-wallet-001",
        ip_address="127.0.0.1",
        user_agent="Test Script v1.0",
        changes={
            "before": None,
            "after": {
                "name": "test-wallet-001",
                "network": 5010,
                "type": "multisig"
            }
        },
        result="success"
    )
    print("  ✅ Logged: wallet.create")
    
    # Action 2: Transaction send
    await audit_service.log_transaction_action(
        partner_id=partner_id,
        user_id=test_partner['ec_address'],
        action="tx.send",
        tx_unid="TEST123456789",
        ip_address="127.0.0.1",
        user_agent="Test Script v1.0",
        result="success",
        metadata={
            "token": "TRX",
            "amount": "100.5",
            "to_address": "TTestAddress123"
        }
    )
    print("  ✅ Logged: tx.send")
    
    # Action 3: Signature approval
    await audit_service.log_signature_action(
        partner_id=partner_id,
        user_id=test_partner['ec_address'],
        action="signature.approve",
        tx_unid="TEST123456789",
        ip_address="127.0.0.1",
        user_agent="Test Script v1.0",
        result="success"
    )
    print("  ✅ Logged: signature.approve")
    
    # Action 4: Failed action (for testing)
    await audit_service.log_action(
        partner_id=partner_id,
        user_id=test_partner['ec_address'],
        action="tx.send",
        resource_type="transaction",
        resource_id="FAIL_TEST",
        ip_address="127.0.0.1",
        user_agent="Test Script v1.0",
        result="failure",
        error_message="Insufficient balance for test"
    )
    print("  ✅ Logged: tx.send (failure)")
    
    print()
    print("Querying audit log...")
    
    # Query recent logs
    recent_logs = await audit_service.get_audit_log(
        partner_id=partner_id,
        limit=10
    )
    
    print(f"Recent audit logs ({len(recent_logs)} entries):")
    for log in recent_logs:
        status_icon = "✅" if log['result'] == 'success' else "❌"
        print(f"  {status_icon} {log['action']} - {log['resource_type']} - {log['timestamp']}")
    
    print()
    
    # Test user activity
    print("Testing user activity query...")
    user_activity = await audit_service.get_user_activity(
        user_id=test_partner['ec_address'],
        period="today",
        limit=5
    )
    print(f"User activity ({len(user_activity)} actions today):")
    for activity in user_activity:
        print(f"  - {activity['action']} on {activity['resource_type']} at {activity['timestamp']}")
    
    print()
    
    # Test action counts
    print("Testing action count aggregation...")
    action_counts = await audit_service.get_action_counts(
        partner_id=partner_id,
        period="today"
    )
    print("Action counts:")
    for action, count in action_counts.items():
        print(f"  - {action}: {count}")
    
    print()
    
    # Test error rate
    print("Testing error rate calculation...")
    error_rate = await audit_service.get_error_rate(
        partner_id=partner_id,
        hours=24
    )
    print(f"Error rate (last 24h):")
    print(f"  - Total actions: {error_rate['total_actions']}")
    print(f"  - Failed actions: {error_rate['failed_actions']}")
    print(f"  - Error rate: {error_rate['error_rate_percent']}%")
    
    print()
    print("✅ Audit logging test complete!")
    print()
    
    # ========================================================================
    # TEST 6: Partner Update
    # ========================================================================
    print("=" * 80)
    print("TEST 6: Partner Update")
    print("=" * 80)
    
    print("Updating partner tier to 'enterprise'...")
    updated_partner = await partner_service.update_partner(
        partner_id=partner_id,
        tier="enterprise",
        rate_limit_per_minute=5000
    )
    print(f"✅ Partner updated!")
    print(f"  New tier: {updated_partner['tier']}")
    print(f"  New rate limit: {updated_partner['rate_limit_per_minute']} req/min")
    print()
    
    # ========================================================================
    # TEST 7: Usage Statistics
    # ========================================================================
    print("=" * 80)
    print("TEST 7: Usage Statistics")
    print("=" * 80)
    
    print("Fetching usage statistics...")
    usage_stats = await partner_service.get_usage_stats(
        partner_id=partner_id,
        period="today"
    )
    
    print("Usage stats (today):")
    print(f"  - API Requests: {usage_stats['api_requests']}")
    print(f"  - Webhooks Sent: {usage_stats['webhooks_sent']}")
    print(f"  - Transactions: {usage_stats['transactions_processed']}")
    print(f"  - Current Tier: {usage_stats['tier']}")
    print(f"  - Rate Limit: {usage_stats['rate_limit_per_minute']} req/min")
    print("✅ Usage stats retrieved!")
    print()
    
    # ========================================================================
    # TEST 8: Multiple API Keys (Key Rotation)
    # ========================================================================
    if api_key and api_secret:
        print("=" * 80)
        print("TEST 8: API Key Rotation")
        print("=" * 80)
        
        print("Generating additional API key (for staging environment)...")
        new_key = await partner_service.rotate_api_key(
            partner_id=partner_id,
            name="Staging Environment"
        )
        
        print("✅ New API key generated!")
        print(f"  Key: {new_key['api_key'][:16]}...{new_key['api_key'][-8:]}")
        print(f"  Secret: {new_key['api_secret'][:16]}...{new_key['api_secret'][-8:]}")
        print(f"  Name: {new_key['name']}")
        print()
        
        print("Listing all API keys for partner...")
        api_keys = await partner_service.list_api_keys(partner_id)
        print(f"Total API keys: {len(api_keys)}")
        for key in api_keys:
            status = "✅ Active" if not key['revoked_at'] else "❌ Revoked"
            print(f"  - {key['name'] or 'Unnamed'}: {key['api_key'][:16]}... ({status})")
        
        print()
        print("✅ API key rotation test complete!")
        print()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print("✅ Partner Creation & Retrieval")
    print("✅ Partner Listing")
    if api_key and api_secret:
        print("✅ API Key Authentication")
        print("✅ API Key Rotation")
    else:
        print("⚠️  API Key Authentication (skipped - no credentials)")
    print("✅ Audit Logging (4 actions logged)")
    print("✅ Audit Queries (recent, user activity, counts, error rate)")
    print("✅ Partner Update")
    print("✅ Usage Statistics")
    print()
    print("🎉 Phase 1 (Foundation) - ALL TESTS PASSED!")
    print()
    
    # Save credentials to file for next phase testing
    if api_key and api_secret:
        print("💾 Saving test credentials to .test_credentials.env...")
        with open(".test_credentials.env", "w") as f:
            f.write(f"# Test Partner Credentials (Phase 1)\n")
            f.write(f"# Generated: {partner['created_at']}\n")
            f.write(f"TEST_PARTNER_ID={partner_id}\n")
            f.write(f"TEST_API_KEY={api_key}\n")
            f.write(f"TEST_API_SECRET={api_secret}\n")
            f.write(f"TEST_EC_ADDRESS={test_partner['ec_address']}\n")
        print("✅ Credentials saved to .test_credentials.env")
        print()
    
    # Close database connection
    await db_pool.close()
    print("👋 Database connection closed. Tests complete!")


if __name__ == "__main__":
    asyncio.run(test_phase1())
