"""
Simple integration tests for Organization API.
Tests basic CRUD and authentication.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

# Test client
client = TestClient(app)


# ==================== Auth Tests ====================

def test_organizations_require_auth():
    """Test that organizations endpoint requires authentication."""
    response = client.get("/api/organizations")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_create_organization_requires_auth():
    """Test that creating organization requires authentication."""
    response = client.post(
        "/api/organizations",
        json={
            "name": "Test Org",
            "license_type": "free"
        }
    )
    assert response.status_code == 401


# ==================== Invalid Token Tests ====================

def test_invalid_token_rejected():
    """Test that invalid JWT tokens are rejected."""
    response = client.get(
        "/api/organizations",
        headers={"Authorization": "Bearer invalid_token_12345"}
    )
    # FastAPI HTTPBearer returns 403 for invalid tokens (standard behavior)
    assert response.status_code == 403


def test_malformed_auth_header():
    """Test malformed Authorization header."""
    response = client.get(
        "/api/organizations",
        headers={"Authorization": "NotBearer sometoken"}
    )
    # FastAPI HTTPBearer should reject this at the HTTP level
    assert response.status_code in [401, 403]


# ==================== Service Layer Tests ====================

@pytest.mark.asyncio
async def test_organization_service_initialization():
    """Test that OrganizationService can be initialized."""
    from backend.database.db_postgres import AsyncDatabase
    from backend.services.organization_service import OrganizationService
    import os
    
    # Get DB URL from environment (Docker uses service name 'postgres')
    db_url = os.getenv("DATABASE_URL", "postgresql://orgon_user:orgon_dev_password@postgres:5432/orgon_db")
    
    # Create AsyncDatabase instance
    db = AsyncDatabase(db_url)
    await db.connect()
    
    try:
        # Create service
        org_service = OrganizationService(db)
        
        # Test basic functionality (without RLS context for now)
        count = await org_service.count_organizations()
        assert isinstance(count, int)
        assert count >= 0
        
        print(f"✅ OrganizationService initialized, found {count} organizations")
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_rls_context_functions():
    """Test RLS context management functions."""
    from backend.database.db_postgres import AsyncDatabase
    from backend.services.organization_service import OrganizationService
    from uuid import UUID
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://orgon_user:orgon_dev_password@postgres:5432/orgon_db")
    db = AsyncDatabase(db_url)
    await db.connect()
    
    try:
        org_service = OrganizationService(db)
        
        # Test setting context (use test organization UUID from seed data)
        test_org_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        await org_service.set_tenant_context(test_org_id)
        print(f"✅ set_tenant_context({test_org_id}) executed")
        
        # Test clearing context
        await org_service.clear_tenant_context()
        print("✅ clear_tenant_context() executed")
        
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_list_organizations_without_rls():
    """Test listing organizations without RLS context."""
    from backend.database.db_postgres import AsyncDatabase
    from backend.services.organization_service import OrganizationService
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://orgon_user:orgon_dev_password@postgres:5432/orgon_db")
    db = AsyncDatabase(db_url)
    await db.connect()
    
    try:
        org_service = OrganizationService(db)
        
        # Clear any existing context
        await org_service.clear_tenant_context()
        
        # List organizations (as superuser, should see all)
        orgs = await org_service.list_organizations(limit=10)
        
        assert isinstance(orgs, list)
        print(f"✅ Found {len(orgs)} organizations")
        
        if orgs:
            # Check structure of first org
            first_org = orgs[0]
            assert 'id' in first_org
            assert 'name' in first_org
            print(f"   First org: {first_org['name']} (ID: {first_org['id']})")
    
    finally:
        await db.close()


# ==================== Schema Validation Tests ====================

def test_organization_create_schema_validation():
    """Test Pydantic schema validation for OrganizationCreate."""
    from backend.api.schemas import OrganizationCreate, LicenseType
    
    # Valid data
    org = OrganizationCreate(
        name="Test Organization",
        slug="test-organization",
        license_type=LicenseType.pro
    )
    assert org.name == "Test Organization"
    assert org.slug == "test-organization"
    assert org.license_type == LicenseType.pro
    
    # Test with optional fields
    org_full = OrganizationCreate(
        name="Full Org",
        slug="full-org",
        license_type=LicenseType.enterprise,
        address="123 Main St",
        city="Bishkek",
        country="KG",
        email="info@full-org.com",
        phone="+996555123456"
    )
    assert org_full.slug == "full-org"
    assert org_full.city == "Bishkek"
    assert org_full.email == "info@full-org.com"
    print("✅ OrganizationCreate schema validation passed")


def test_user_organization_schema():
    """Test UserOrganization schemas."""
    from backend.api.schemas import UserOrganizationCreate, UserRole
    from uuid import UUID
    
    test_user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    member = UserOrganizationCreate(
        user_id=test_user_id,
        role=UserRole.admin
    )
    assert member.user_id == test_user_id
    assert member.role == UserRole.admin
    print("✅ UserOrganizationCreate schema validation passed")


def test_organization_settings_schema():
    """Test OrganizationSettings schemas."""
    from backend.api.schemas import OrganizationSettingsUpdate
    
    settings = OrganizationSettingsUpdate(
        billing_enabled=True,
        kyc_enabled=True,
        features={"multi_sig": True, "auto_withdrawal": False},
        limits={"daily_withdrawal_usdt": 100000}
    )
    assert settings.billing_enabled is True
    assert settings.kyc_enabled is True
    assert settings.features["multi_sig"] is True
    assert settings.limits["daily_withdrawal_usdt"] == 100000
    print("✅ OrganizationSettingsUpdate schema validation passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
