# Multi-Tenancy API Documentation

**Phase:** 1.2 Backend API  
**Status:** Complete  
**Created:** 2026-02-10

---

## Overview

Multi-tenancy support for ORGON: Organizations, Members, Settings.

**Base URL:** `/api/organizations`

---

## Schemas (Pydantic Models)

**File:** `backend/api/schemas.py`

### Core Enums
- `LicenseType`: free, basic, pro, enterprise
- `OrganizationStatus`: active, suspended, cancelled
- `UserRole`: admin, operator, viewer

### Organization Models
- `OrganizationCreate`: Create new organization
- `OrganizationUpdate`: Update organization (partial)
- `OrganizationResponse`: Organization details
- `OrganizationList`: List with pagination

### User-Organization Models
- `UserOrganizationCreate`: Add user to org
- `UserOrganizationUpdate`: Update user role
- `OrganizationMember`: Member with user details
- `OrganizationMembersList`: List with pagination

### Settings Models
- `OrganizationSettingsUpdate`: Update settings (partial)
- `OrganizationSettingsResponse`: Settings details

### Context Models
- `TenantContext`: Current tenant (RLS)
- `OrganizationSwitchRequest`: Switch organization

---

## API Endpoints

**File:** `backend/api/routes_organizations.py`

### Organization CRUD

#### `POST /api/organizations`
**Create organization**
- **Permissions:** Any authenticated user
- **Note:** User becomes admin automatically

**Request:**
```json
{
  "name": "Safina Exchange KG",
  "slug": "safina-kg",
  "email": "admin@safina.kg",
  "phone": "+996 555 123456",
  "city": "Bishkek",
  "country": "Kyrgyzstan",
  "license_type": "enterprise"
}
```

**Response:** `OrganizationResponse` (201)

---

#### `GET /api/organizations`
**List organizations for current user**
- **Permissions:** Authenticated user
- **Query:** `limit` (1-100), `offset` (0+)

**Response:** `OrganizationList`

---

#### `GET /api/organizations/{organization_id}`
**Get organization details**
- **Permissions:** User must be a member

**Response:** `OrganizationResponse`

---

#### `PUT /api/organizations/{organization_id}`
**Update organization**
- **Permissions:** Admin role required

**Request:** `OrganizationUpdate` (partial)

**Response:** `OrganizationResponse`

---

#### `DELETE /api/organizations/{organization_id}`
**Delete organization**
- **Permissions:** Admin role required
- **Warning:** Cascade deletes all data!

**Response:** `SuccessResponse`

---

### Organization Members

#### `GET /api/organizations/{organization_id}/members`
**List members**
- **Permissions:** User must be a member
- **Query:** `limit`, `offset`

**Response:** `OrganizationMembersList`

---

#### `POST /api/organizations/{organization_id}/members`
**Add user to organization**
- **Permissions:** Admin role required

**Request:**
```json
{
  "user_id": "uuid",
  "role": "operator"
}
```

**Response:** `OrganizationMember` (201)

---

#### `PUT /api/organizations/{organization_id}/members/{member_user_id}`
**Update member role**
- **Permissions:** Admin role required

**Request:**
```json
{
  "role": "admin"
}
```

**Response:** `OrganizationMember`

---

#### `DELETE /api/organizations/{organization_id}/members/{member_user_id}`
**Remove member**
- **Permissions:** Admin role required
- **Note:** Cannot remove last admin

**Response:** `SuccessResponse`

---

### Organization Settings

#### `GET /api/organizations/{organization_id}/settings`
**Get settings**
- **Permissions:** User must be a member

**Response:** `OrganizationSettingsResponse`

---

#### `PUT /api/organizations/{organization_id}/settings`
**Update settings**
- **Permissions:** Admin role required

**Request:** `OrganizationSettingsUpdate` (partial)

**Example:**
```json
{
  "billing_enabled": true,
  "kyc_enabled": true,
  "fiat_enabled": true,
  "features": {
    "auto_withdrawal": true,
    "2fa_required": true
  },
  "limits": {
    "daily_withdrawal_usdt": 100000,
    "monthly_transactions": 10000
  },
  "branding": {
    "logo_url": "https://safina.kg/logo.png",
    "primary_color": "#1E40AF"
  }
}
```

**Response:** `OrganizationSettingsResponse`

---

### Organization Context

#### `POST /api/organizations/switch`
**Switch current organization**
- **Permissions:** User must be a member

**Request:**
```json
{
  "organization_id": "uuid"
}
```

**Response:** `SuccessResponse`

---

#### `GET /api/organizations/current`
**Get current organization**
- Returns organization from session context

**Response:** `OrganizationResponse`

---

## Service Layer

**File:** `backend/services/organization_service.py`

### Class: `OrganizationService`

**Methods:**
- `create_organization(data, created_by)` → OrganizationResponse
- `list_organizations(user_id, limit, offset)` → OrganizationList
- `get_organization(organization_id, user_id)` → OrganizationResponse
- `update_organization(organization_id, data, user_id)` → OrganizationResponse
- `delete_organization(organization_id, user_id)` → bool

**Members:**
- `list_members(organization_id, user_id, limit, offset)` → OrganizationMembersList
- `add_member(organization_id, new_user_id, role, added_by)` → OrganizationMember
- `update_member_role(organization_id, member_user_id, new_role, updated_by)` → OrganizationMember
- `remove_member(organization_id, member_user_id, removed_by)` → bool

**Settings:**
- `get_settings(organization_id, user_id)` → OrganizationSettingsResponse
- `update_settings(organization_id, data, user_id)` → OrganizationSettingsResponse

**Context:**
- `switch_organization(organization_id, user_id)` → bool

**Internal:**
- `_check_permission(organization_id, user_id, required_role)` → bool

**Permissions:**
- Viewer: Read-only access
- Operator: Create transactions, manage contacts
- Admin: Full access (manage members, settings, delete org)

---

## RLS Middleware

**File:** `backend/api/middleware.py`

### Class: `RLSMiddleware`

**Purpose:** Set tenant context for PostgreSQL RLS policies

**How it works:**
1. Extract `organization_id` from JWT token or header
2. Call `SELECT set_tenant_context($1, $2)`
3. Process request
4. Call `SELECT clear_tenant_context()`

**Headers (temporary, for testing):**
- `X-Organization-ID`: UUID of organization
- `X-Is-Super-Admin`: "true" or "false"

**Production:** Extract from JWT token

**Registered in:** `setup_middleware()` (after RequestLogging, before Auth)

---

## Database Integration

**RLS Functions Used:**
- `set_tenant_context(org_id UUID, is_admin BOOLEAN)`
- `clear_tenant_context()`

**Tables:**
- `organizations`
- `user_organizations`
- `organization_settings`

**RLS Policies:** Auto-filter by `organization_id`

---

## Testing

### Test with cURL:

```bash
# Create organization
curl -X POST http://localhost:8890/api/organizations \
  -H "Content-Type: application/json" \
  -H "X-Organization-ID: 00000000-0000-0000-0000-000000000000" \
  -d '{
    "name": "Test Org",
    "slug": "test-org",
    "license_type": "free"
  }'

# List organizations
curl http://localhost:8890/api/organizations \
  -H "X-Organization-ID: 123e4567-e89b-12d3-a456-426614174000"

# Get organization
curl http://localhost:8890/api/organizations/123e4567-e89b-12d3-a456-426614174000 \
  -H "X-Organization-ID: 123e4567-e89b-12d3-a456-426614174000"

# List members
curl http://localhost:8890/api/organizations/123e4567-e89b-12d3-a456-426614174000/members \
  -H "X-Organization-ID: 123e4567-e89b-12d3-a456-426614174000"

# Get settings
curl http://localhost:8890/api/organizations/123e4567-e89b-12d3-a456-426614174000/settings \
  -H "X-Organization-ID: 123e4567-e89b-12d3-a456-426614174000"
```

---

## Next Steps (Phase 1.3)

1. **Frontend UI:**
   - Organization Selector dropdown
   - Organization Management page (CRUD)
   - Members Management page
   - Settings page

2. **JWT Integration:**
   - Store `current_organization_id` in JWT token
   - Extract in RLSMiddleware
   - Update AuthService

3. **Testing:**
   - pytest integration tests
   - RLS isolation tests
   - Permission checks

---

**Status:** Backend API Complete ✅  
**Next:** Frontend UI (Phase 1.3)
