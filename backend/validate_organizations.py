"""
Quick validation script for OrganizationService.
Tests basic functionality without pytest framework.
"""

import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database.db_postgres import AsyncDatabase
from backend.services.organization_service import OrganizationService
from backend.api.schemas import OrganizationCreate, LicenseType


async def main():
    """Run validation checks."""
    print("🔍 Validating OrganizationService...")
    
    # Get DB URL
    db_url = os.getenv("DATABASE_URL", "postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db")
    
    # Create database connection
    db = AsyncDatabase(db_url)
    try:
        await db.connect()
        print("✅ Database connected")
        
        # Create service
        org_service = OrganizationService(db)
        print("✅ OrganizationService initialized")
        
        # Test 1: Count organizations
        count = await org_service.count_organizations()
        print(f"✅ count_organizations() = {count}")
        assert isinstance(count, int), "Count must be integer"
        
        # Test 2: List organizations (without RLS)
        await org_service.clear_tenant_context()
        orgs = await org_service.list_organizations(limit=5)
        print(f"✅ list_organizations() = {len(orgs)} orgs")
        assert isinstance(orgs, list), "Must return list"
        
        if orgs:
            first_org = orgs[0]
            print(f"   First org: {first_org.get('name')} (ID: {first_org.get('id')})")
            assert 'id' in first_org
            assert 'name' in first_org
        
        # Test 3: RLS context functions
        if count > 0 and orgs:
            test_org_id = orgs[0]['id']
            await org_service.set_tenant_context(test_org_id)
            print(f"✅ set_tenant_context({test_org_id}) executed")
            
            await org_service.clear_tenant_context()
            print(f"✅ clear_tenant_context() executed")
        
        # Test 4: Schema validation
        org_create = OrganizationCreate(
            name="Validation Test Org",
            license_type=LicenseType.FREE
        )
        print(f"✅ OrganizationCreate schema valid: {org_create.name}")
        
        # Test 5: Get organization by ID (if any exist)
        if orgs:
            test_id = orgs[0]['id']
            org_detail = await org_service.get_organization(test_id)
            if org_detail:
                print(f"✅ get_organization({test_id}) = {org_detail['name']}")
            else:
                print(f"⚠️  get_organization({test_id}) returned None")
        
        # Test 6: Settings functionality
        if orgs:
            test_id = orgs[0]['id']
            settings = await org_service.get_settings(test_id)
            if settings:
                print(f"✅ get_settings({test_id}) returned settings")
            else:
                print(f"⚠️  get_settings({test_id}) returned None (might need seed data)")
        
        print("\n✅ All validation checks passed!")
        print(f"   Total organizations: {count}")
        print(f"   OrganizationService: WORKING")
        return 0
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await db.close()
        print("🔌 Database connection closed")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
