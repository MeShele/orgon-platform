"""
Integration tests for Organization API endpoints.
Tests multi-tenant isolation, CRUD operations, and RLS.
"""

import pytest
import asyncio
import asyncpg
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.auth_service import AuthService

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
async def auth_service(db_pool):
    """Create AuthService instance."""
    return AuthService(db_pool)


@pytest.fixture
async def test_users(auth_service):
    """Create test users with different roles."""
    users = {}
    
    # Admin user
    admin = await auth_service.create_user(
        email="test_admin@orgon.test",
        password="AdminPass123!",
        full_name="Test Admin",
        role="admin"
    )
    users['admin'] = admin
    
    # Operator user
    operator = await auth_service.create_user(
        email="test_operator@orgon.test",
        password="OperatorPass123!",
        full_name="Test Operator",
        role="operator"
    )
    users['operator'] = operator
    
    # Viewer user
    viewer = await auth_service.create_user(
        email="test_viewer@orgon.test",
        password="ViewerPass123!",
        full_name="Test Viewer",
        role="viewer"
    )
    users['viewer'] = viewer
    
    yield users
    
    # Cleanup
    async with auth_service.pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM users WHERE email LIKE 'test_%@orgon.test'"
        )


@pytest.fixture
async def admin_token(auth_service, test_users):
    """Get admin JWT token."""
    admin = test_users['admin']
    token = auth_service.create_access_token(
        user_id=admin['id'],
        email=admin['email'],
        role=admin['role']
    )
    return token


@pytest.fixture
async def operator_token(auth_service, test_users):
    """Get operator JWT token."""
    operator = test_users['operator']
    token = auth_service.create_access_token(
        user_id=operator['id'],
        email=operator['email'],
        role=operator['role']
    )
    return token


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


# ==================== Organization CRUD Tests ====================

def test_create_organization_as_admin(client, admin_token):
    """Admin can create organization."""
    response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test Exchange",
            "slug": "test-exchange",
            "license_type": "pro",
            "status": "active"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data['name'] == "Test Exchange"
    assert data['slug'] == "test-exchange"
    assert data['license_type'] == "pro"
    assert 'id' in data


def test_create_organization_as_operator_forbidden(client, operator_token):
    """Operator cannot create organization."""
    response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {operator_token}"},
        json={
            "name": "Forbidden Org",
            "slug": "forbidden-org",
            "license_type": "basic"
        }
    )
    assert response.status_code == 403


def test_list_organizations_as_admin(client, admin_token):
    """Admin can list all organizations."""
    response = client.get(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'items' in data
    assert 'total' in data
    assert isinstance(data['items'], list)


def test_get_organization_by_id(client, admin_token):
    """Get organization by ID."""
    # First create org
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Get Test Org", "slug": "get-test-org"}
    )
    org_id = create_response.json()['id']
    
    # Get org
    response = client.get(
        f"/api/organizations/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == org_id
    assert data['name'] == "Get Test Org"


def test_update_organization(client, admin_token):
    """Update organization details."""
    # Create org
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Update Test", "slug": "update-test"}
    )
    org_id = create_response.json()['id']
    
    # Update org
    response = client.put(
        f"/api/organizations/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Updated Name", "status": "suspended"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['name'] == "Updated Name"
    assert data['status'] == "suspended"


def test_delete_organization(client, admin_token):
    """Soft delete organization."""
    # Create org
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Delete Test", "slug": "delete-test"}
    )
    org_id = create_response.json()['id']
    
    # Delete org
    response = client.delete(
        f"/api/organizations/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204
    
    # Verify deleted
    get_response = client.get(
        f"/api/organizations/{org_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 200
    assert get_response.json()['status'] == 'archived'


# ==================== Members Management Tests ====================

def test_add_member_to_organization(client, admin_token, test_users):
    """Add member to organization."""
    # Create org
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Member Test", "slug": "member-test"}
    )
    org_id = create_response.json()['id']
    
    # Add member
    operator_id = test_users['operator']['id']
    response = client.post(
        f"/api/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": operator_id, "role": "operator"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data['user_id'] == operator_id
    assert data['role'] == 'operator'


def test_list_organization_members(client, admin_token, test_users):
    """List organization members."""
    # Create org and add member
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "List Members Test", "slug": "list-members-test"}
    )
    org_id = create_response.json()['id']
    
    operator_id = test_users['operator']['id']
    client.post(
        f"/api/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": operator_id, "role": "operator"}
    )
    
    # List members
    response = client.get(
        f"/api/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    members = response.json()
    assert len(members) >= 1
    assert any(m['user_id'] == operator_id for m in members)


def test_update_member_role(client, admin_token, test_users):
    """Update member's role in organization."""
    # Setup
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Update Role Test", "slug": "update-role-test"}
    )
    org_id = create_response.json()['id']
    
    operator_id = test_users['operator']['id']
    client.post(
        f"/api/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": operator_id, "role": "viewer"}
    )
    
    # Update role
    response = client.put(
        f"/api/organizations/{org_id}/members/{operator_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "admin"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data['role'] == 'admin'


def test_remove_member_from_organization(client, admin_token, test_users):
    """Remove member from organization."""
    # Setup
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Remove Member Test", "slug": "remove-member-test"}
    )
    org_id = create_response.json()['id']
    
    operator_id = test_users['operator']['id']
    client.post(
        f"/api/organizations/{org_id}/members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_id": operator_id, "role": "operator"}
    )
    
    # Remove member
    response = client.delete(
        f"/api/organizations/{org_id}/members/{operator_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204


# ==================== Settings Tests ====================

def test_get_organization_settings(client, admin_token):
    """Get organization settings."""
    # Create org
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Settings Test", "slug": "settings-test"}
    )
    org_id = create_response.json()['id']
    
    # Get settings
    response = client.get(
        f"/api/organizations/{org_id}/settings",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'billing_enabled' in data
    assert 'kyc_enabled' in data
    assert 'features' in data


def test_update_organization_settings(client, admin_token):
    """Update organization settings."""
    # Create org
    create_response = client.post(
        "/api/organizations",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "Update Settings", "slug": "update-settings"}
    )
    org_id = create_response.json()['id']
    
    # Update settings
    response = client.put(
        f"/api/organizations/{org_id}/settings",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "billing_enabled": False,
            "kyc_enabled": True,
            "features": {"auto_withdrawal": True},
            "limits": {"daily_withdrawal_usdt": 50000}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data['billing_enabled'] is False
    assert data['kyc_enabled'] is True
    assert data['features']['auto_withdrawal'] is True
    assert data['limits']['daily_withdrawal_usdt'] == 50000


# ==================== RLS Isolation Tests ====================

@pytest.mark.asyncio
async def test_rls_tenant_isolation(db_pool, auth_service, test_users):
    """
    Test Row-Level Security isolation between organizations.
    Org A should not see Org B's data.
    """
    async with db_pool.acquire() as conn:
        # Create 2 organizations
        org_a_id = await conn.fetchval(
            """
            INSERT INTO organizations (name, slug, license_type, created_by)
            VALUES ($1, $2, $3, $4) RETURNING id
            """,
            "RLS Test Org A", "rls-test-a", "pro", test_users['admin']['id']
        )
        
        org_b_id = await conn.fetchval(
            """
            INSERT INTO organizations (name, slug, license_type, created_by)
            VALUES ($1, $2, $3, $4) RETURNING id
            """,
            "RLS Test Org B", "rls-test-b", "basic", test_users['admin']['id']
        )
        
        # Create wallet for Org A
        await conn.execute(
            """
            SELECT set_tenant_context($1, false)
            """,
            org_a_id
        )
        await conn.execute(
            """
            INSERT INTO wallets (name, address, network, organization_id)
            VALUES ($1, $2, $3, $4)
            """,
            "Org A Wallet", "0xOrgA123", "tron", org_a_id
        )
        
        # Create wallet for Org B
        await conn.execute("SELECT clear_tenant_context()")
        await conn.execute(
            """
            SELECT set_tenant_context($1, false)
            """,
            org_b_id
        )
        await conn.execute(
            """
            INSERT INTO wallets (name, address, network, organization_id)
            VALUES ($1, $2, $3, $4)
            """,
            "Org B Wallet", "0xOrgB456", "tron", org_b_id
        )
        
        # Test isolation: Org A context should see only Org A wallet
        await conn.execute("SELECT clear_tenant_context()")
        await conn.execute(f"SELECT set_tenant_context($1, false)", org_a_id)
        
        wallets_a = await conn.fetch(
            "SELECT * FROM wallets WHERE address IN ('0xOrgA123', '0xOrgB456')"
        )
        assert len(wallets_a) == 1
        assert wallets_a[0]['address'] == '0xOrgA123'
        
        # Test isolation: Org B context should see only Org B wallet
        await conn.execute("SELECT clear_tenant_context()")
        await conn.execute(f"SELECT set_tenant_context($1, false)", org_b_id)
        
        wallets_b = await conn.fetch(
            "SELECT * FROM wallets WHERE address IN ('0xOrgA123', '0xOrgB456')"
        )
        assert len(wallets_b) == 1
        assert wallets_b[0]['address'] == '0xOrgB456'
        
        # Test Super Admin: should see both
        await conn.execute("SELECT clear_tenant_context()")
        await conn.execute(
            "SELECT set_tenant_context('00000000-0000-0000-0000-000000000000', true)"
        )
        
        wallets_admin = await conn.fetch(
            "SELECT * FROM wallets WHERE address IN ('0xOrgA123', '0xOrgB456')"
        )
        assert len(wallets_admin) == 2
        
        # Cleanup
        await conn.execute(
            "DELETE FROM wallets WHERE address IN ('0xOrgA123', '0xOrgB456')"
        )
        await conn.execute(
            "DELETE FROM organizations WHERE id IN ($1, $2)",
            org_a_id, org_b_id
        )
        await conn.execute("SELECT clear_tenant_context()")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
