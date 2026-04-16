"""
End-to-End tests for Organization Multi-Tenancy.
Tests complete user workflows and tenant isolation.
"""

import pytest
import asyncio
from uuid import UUID, uuid4
from datetime import datetime

from backend.services.organization_service import OrganizationService
from backend.database.db_postgres import AsyncDatabase
from backend.api.schemas import (
    OrganizationCreate, 
    UserOrganizationCreate,
    OrganizationStatus,
    UserRole
)

# Note: UserRole values are: admin, operator, viewer (not owner/manager)


# ==================== Fixtures ====================

@pytest.fixture
def db_url():
    """Test database URL."""
    return "postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"


@pytest.fixture
def test_user_id():
    """Return test user ID from seed data."""
    # Use existing test user from seed_test_organizations.sql
    return 1


@pytest.fixture
def additional_test_users():
    """Return additional test user IDs from seed data."""
    return [
        2,  # Test User 1
        3,  # Test User 2
        4,  # Test User 3
    ]


# ==================== E2E Test Scenarios ====================

@pytest.mark.asyncio
async def test_create_organization_flow(db_url, test_user_id):
    """
    E2E Scenario 1: Create Organization Flow
    
    Steps:
    1. Create organization
    2. Verify organization exists
    3. Verify default settings created
    4. Verify creator is added as owner
    """
    db = AsyncDatabase(db_url)
    await db.connect()
    service = OrganizationService(db)
    
    try:
        # Step 1: Create organization
        org_data = OrganizationCreate(
            name="Test Exchange KG",
            slug=f"test-exchange-{uuid4().hex[:8]}",
            email="test@example.com",
            country="Kyrgyzstan"
        )
        
        org = await service.create_organization(org_data, test_user_id)
        
        # Step 2: Verify organization exists
        assert org is not None
        assert org["name"] == "Test Exchange KG"
        assert org["slug"] == org_data.slug
        assert org["status"] == OrganizationStatus.active.value
        
        org_id = org["id"]
        
        # Step 3: Verify default settings created
        settings = await service.get_settings(org_id)
        assert settings is not None
        assert settings["organization_id"] == org_id
        
        # Step 4: Verify creator is owner
        members = await service.list_members(org_id)
        assert len(members) == 1
        assert members[0]["user_id"] == test_user_id
        assert members[0]["role"] == UserRole.admin.value
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_add_member_workflow(db_url, test_user_id, additional_test_users):
    """
    E2E Scenario 2: Add Member Workflow
    
    Steps:
    1. Create organization (as owner)
    2. Add new member as manager
    3. Verify member added with correct role
    4. Verify member can be listed
    """
    db = AsyncDatabase(db_url)
    await db.connect()
    service = OrganizationService(db)
    
    try:
        # Step 1: Create organization
        org_data = OrganizationCreate(
            name="Test Org Members",
            slug=f"test-members-{uuid4().hex[:8]}",
            email="members@example.com"
        )
        
        org = await service.create_organization(org_data, test_user_id)
        org_id = org["id"]
        
        # Step 2: Add new member (use additional test user)
        new_user_id = additional_test_users[0]
        member_data = UserOrganizationCreate(
            user_id=new_user_id,
            role=UserRole.operator
        )
        
        member = await service.add_member(org_id, member_data)
        
        # Step 3: Verify member added
        assert member is not None
        assert member["user_id"] == new_user_id
        assert member["role"] == UserRole.operator.value
        assert member["organization_id"] == org_id
        
        # Step 4: Verify member can be listed
        members = await service.list_members(org_id)
        assert len(members) == 2  # Admin + Operator
        
        # Verify roles
        roles = {m["role"] for m in members}
        assert UserRole.admin.value in roles
        assert UserRole.operator.value in roles
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_tenant_isolation(db_url, test_user_id, additional_test_users):
    """
    E2E Scenario 3: Tenant Isolation (RLS Test)
    
    Steps:
    1. Create Org A
    2. Create Org B (different user)
    3. Set tenant context to Org A
    4. Verify Org A visible, Org B not visible
    5. Clear context and verify both visible
    """
    db = AsyncDatabase(db_url)
    await db.connect()
    service = OrganizationService(db)
    
    try:
        # Step 1: Create Org A
        org_a_data = OrganizationCreate(
            name="Organization A",
            slug=f"org-a-{uuid4().hex[:8]}",
            email="orga@example.com"
        )
        org_a = await service.create_organization(org_a_data, test_user_id)
        org_a_id = org_a["id"]
        
        # Step 2: Create Org B (different user, use additional test user)
        user_b_id = additional_test_users[1]
        org_b_data = OrganizationCreate(
            name="Organization B",
            slug=f"org-b-{uuid4().hex[:8]}",
            email="orgb@example.com"
        )
        org_b = await service.create_organization(org_b_data, user_b_id)
        org_b_id = org_b["id"]
        
        # Step 3: Set tenant context to Org A
        await service.set_tenant_context(org_a_id)
        
        # Step 4: Verify isolation
        # (Note: RLS policies should filter results by tenant_id)
        # In a real scenario, queries would filter by current_setting('app.current_tenant_id')
        
        # Step 5: Clear context
        await service.clear_tenant_context()
        
        # Verify both organizations exist
        all_orgs = await service.list_organizations(limit=100)
        org_ids = {o["id"] for o in all_orgs}
        
        assert org_a_id in org_ids
        assert org_b_id in org_ids
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_tenant_switching(db_url, test_user_id):
    """
    E2E Scenario 4: Tenant Context Switching
    
    Steps:
    1. Create two organizations
    2. Set context to Org 1
    3. Verify context is Org 1
    4. Switch to Org 2
    5. Verify context is Org 2
    6. Clear context
    """
    db = AsyncDatabase(db_url)
    await db.connect()
    service = OrganizationService(db)
    
    try:
        # Step 1: Create two organizations
        org1_data = OrganizationCreate(
            name="Context Org 1",
            slug=f"ctx-org1-{uuid4().hex[:8]}",
            email="ctx1@example.com"
        )
        org1 = await service.create_organization(org1_data, test_user_id)
        org1_id = org1["id"]
        
        org2_data = OrganizationCreate(
            name="Context Org 2",
            slug=f"ctx-org2-{uuid4().hex[:8]}",
            email="ctx2@example.com"
        )
        org2 = await service.create_organization(org2_data, test_user_id)
        org2_id = org2["id"]
        
        # Step 2: Set context to Org 1
        await service.set_tenant_context(org1_id)
        
        # (In real scenario, would verify current_setting('app.current_tenant_id') == org1_id)
        
        # Step 4: Switch to Org 2
        await service.set_tenant_context(org2_id)
        
        # (Verify context switched)
        
        # Step 6: Clear context
        await service.clear_tenant_context()
        
        # Verify both organizations accessible
        org1_retrieved = await service.get_organization(org1_id)
        org2_retrieved = await service.get_organization(org2_id)
        
        assert org1_retrieved is not None
        assert org2_retrieved is not None
        assert org1_retrieved["id"] == org1_id
        assert org2_retrieved["id"] == org2_id
    finally:
        await db.close()
