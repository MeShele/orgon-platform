# ORGON API Documentation

**API Version:** v1  
**Base URL:** `http://localhost:8000/api/v1` (dev) | `https://api.orgon.dev/api/v1` (prod)  
**Interactive Docs:** http://localhost:8000/docs (Swagger UI)

---

## Authentication

### Login

Obtain JWT access token.

**Endpoint:** `POST /auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Usage:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'
```

### Authenticated Requests

Include JWT token in `Authorization` header:

```bash
curl http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Organizations

### List Organizations

Get all organizations the authenticated user belongs to.

**Endpoint:** `GET /organizations`

**Query Parameters:**
- `limit` (int, optional): Max results (default: 50, max: 100)
- `offset` (int, optional): Pagination offset (default: 0)
- `status` (string, optional): Filter by status (`active`, `suspended`, `cancelled`)

**Response:**
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Exchange KG",
    "slug": "exchange-kg",
    "license_type": "pro",
    "status": "active",
    "email": "info@exchangekg.com",
    "created_at": "2026-02-10T12:00:00Z",
    "updated_at": "2026-02-10T12:00:00Z"
  }
]
```

**Example:**
```bash
curl http://localhost:8000/api/v1/organizations?limit=10&offset=0 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Create Organization

Create a new organization (authenticated user becomes admin).

**Endpoint:** `POST /organizations`

**Request:**
```json
{
  "name": "My Exchange",
  "slug": "my-exchange",
  "email": "contact@myexchange.com",
  "phone": "+996700123456",
  "address": "Bishkek, Kyrgyzstan",
  "city": "Bishkek",
  "country": "Kyrgyzstan",
  "license_type": "free"
}
```

**Field Validation:**
- `name`: Required, 1-255 chars
- `slug`: Required, unique, lowercase alphanumeric + hyphens (`^[a-z0-9-]+$`)
- `email`: Optional, valid email format
- `license_type`: `free`, `basic`, `pro`, `enterprise` (default: `free`)

**Response:**
```json
{
  "id": "456e7890-e89b-12d3-a456-426614174999",
  "name": "My Exchange",
  "slug": "my-exchange",
  "license_type": "free",
  "status": "active",
  "email": "contact@myexchange.com",
  "created_at": "2026-02-11T10:00:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174000"
}
```

---

### Get Organization

Retrieve a single organization by ID.

**Endpoint:** `GET /organizations/{organization_id}`

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Exchange KG",
  "slug": "exchange-kg",
  "license_type": "pro",
  "status": "active",
  "email": "info@exchangekg.com",
  "phone": "+996700123456",
  "address": "Chui Ave 123",
  "city": "Bishkek",
  "country": "Kyrgyzstan",
  "created_at": "2026-02-10T12:00:00Z",
  "updated_at": "2026-02-10T12:00:00Z"
}
```

**Errors:**
- `404 Not Found`: Organization doesn't exist or user lacks access

---

### Update Organization

Update organization details (admin only).

**Endpoint:** `PATCH /organizations/{organization_id}`

**Request (partial update):**
```json
{
  "name": "Updated Name",
  "license_type": "enterprise",
  "email": "new-email@example.com"
}
```

**Response:** Updated organization object (same as GET)

**Permissions:**
- Only organization `admin` role can update

---

### Delete Organization

Soft-delete organization (sets status to `cancelled`).

**Endpoint:** `DELETE /organizations/{organization_id}`

**Response:**
```json
{
  "message": "Organization deleted successfully"
}
```

**Notes:**
- Soft delete (status → `cancelled`, data retained)
- Hard delete not supported (compliance requirement)
- Admin role required

---

## Organization Members

### List Members

Get all members of an organization.

**Endpoint:** `GET /organizations/{organization_id}/members`

**Query Parameters:**
- `limit` (int): Max results (default: 50)
- `offset` (int): Pagination offset (default: 0)

**Response:**
```json
[
  {
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "organization_id": "456e7890-e89b-12d3-a456-426614174999",
    "role": "admin",
    "email": "admin@example.com",
    "name": "John Doe",
    "created_at": "2026-02-10T12:00:00Z"
  },
  {
    "user_id": "789e0123-e89b-12d3-a456-426614174888",
    "organization_id": "456e7890-e89b-12d3-a456-426614174999",
    "role": "operator",
    "email": "operator@example.com",
    "name": "Jane Smith",
    "created_at": "2026-02-11T10:00:00Z"
  }
]
```

---

### Add Member

Add a user to an organization with a specific role.

**Endpoint:** `POST /organizations/{organization_id}/members`

**Request:**
```json
{
  "user_id": "789e0123-e89b-12d3-a456-426614174888",
  "role": "operator"
}
```

**Roles:**
- `admin`: Full access (manage wallets, users, settings, billing)
- `operator`: Create transactions, sign, manage contacts
- `viewer`: Read-only access (compliance, reporting)

**Response:**
```json
{
  "user_id": "789e0123-e89b-12d3-a456-426614174888",
  "organization_id": "456e7890-e89b-12d3-a456-426614174999",
  "role": "operator",
  "created_at": "2026-02-11T10:30:00Z"
}
```

**Permissions:**
- Only `admin` role can add members

---

### Update Member Role

Change a member's role within an organization.

**Endpoint:** `PATCH /organizations/{organization_id}/members/{user_id}`

**Request:**
```json
{
  "role": "admin"
}
```

**Response:** Updated member object

**Business Rules:**
- Cannot demote the last admin (must have ≥1 admin)
- Admin role required to update roles

---

### Remove Member

Remove a user from an organization.

**Endpoint:** `DELETE /organizations/{organization_id}/members/{user_id}`

**Response:**
```json
{
  "message": "Member removed successfully"
}
```

**Business Rules:**
- Cannot remove the last admin
- Admin role required

---

## Organization Settings

### Get Settings

Retrieve organization-specific settings.

**Endpoint:** `GET /organizations/{organization_id}/settings`

**Response:**
```json
{
  "organization_id": "456e7890-e89b-12d3-a456-426614174999",
  "billing_enabled": true,
  "kyc_enabled": false,
  "fiat_enabled": false,
  "features": {
    "multi_sig": true,
    "scheduled_transactions": true,
    "api_access": false,
    "white_label": false
  },
  "limits": {
    "max_wallets": 10,
    "max_monthly_volume": 50000.00,
    "max_transaction_size": 10000.00,
    "rate_limit_per_minute": 60
  },
  "branding": {
    "logo_url": null,
    "primary_color": "#3B82F6",
    "custom_domain": null
  },
  "integrations": {
    "webhook_url": null,
    "api_key": null,
    "enabled_integrations": []
  },
  "created_at": "2026-02-10T12:00:00Z",
  "updated_at": "2026-02-10T12:00:00Z"
}
```

---

### Update Settings

Update organization settings (admin only).

**Endpoint:** `PATCH /organizations/{organization_id}/settings`

**Request (partial update):**
```json
{
  "billing_enabled": true,
  "kyc_enabled": true,
  "features": {
    "api_access": true
  },
  "limits": {
    "max_wallets": 50
  }
}
```

**Response:** Updated settings object

**Notes:**
- JSONB fields (`features`, `limits`, `branding`, `integrations`) are merged, not replaced
- Admin role required

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message",
  "status_code": 400,
  "error_type": "validation_error"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | OK | Successful GET/PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid JSON, validation error |
| 401 | Unauthorized | Missing/invalid JWT token |
| 403 | Forbidden | Insufficient permissions (role) |
| 404 | Not Found | Resource doesn't exist or no access |
| 422 | Unprocessable Entity | Pydantic validation failed |
| 500 | Internal Server Error | Server-side error (bug) |

### Example Validation Error

**Request:** Invalid slug (uppercase chars)
```json
{
  "name": "Test Org",
  "slug": "TEST-ORG",
  "email": "test@example.com"
}
```

**Response (422):**
```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "slug"],
      "msg": "String should match pattern '^[a-z0-9-]+$'",
      "input": "TEST-ORG"
    }
  ]
}
```

---

## Rate Limiting

**Current Status:** Not implemented (Phase 1)

**Planned (Phase 2):**
- Per-organization limits (configurable in settings)
- Default: 60 requests/minute
- Header: `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## Pagination

**Parameters:**
- `limit`: Max results per page (default: 50, max: 100)
- `offset`: Number of items to skip (default: 0)

**Response Headers:**
- `X-Total-Count`: Total items available
- `Link`: Pagination links (next, prev, first, last)

**Example:**
```bash
curl "http://localhost:8000/api/v1/organizations?limit=20&offset=40" \
  -H "Authorization: Bearer TOKEN"
```

---

## Versioning

**Current Version:** `v1`

**URL Structure:** `/api/v1/{resource}`

**Deprecation Policy:**
- Major versions supported for 12 months
- Breaking changes require new version (`/api/v2`)
- Non-breaking changes can be added to existing version

---

## WebSockets (Phase 2)

**Planned endpoints:**
- `ws://localhost:8000/ws/transactions` - Real-time transaction updates
- `ws://localhost:8000/ws/prices` - Live crypto prices

**Authentication:** JWT token in query param or header

---

## Testing API

### Using cURL

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}' \
  | jq -r '.access_token')

# List organizations
curl http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer $TOKEN"

# Create organization
curl -X POST http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Exchange",
    "slug": "test-exchange",
    "email": "test@example.com"
  }'
```

### Using Postman

1. Import OpenAPI spec: http://localhost:8000/openapi.json
2. Set `Authorization` header: `Bearer {{token}}`
3. Create environment variable `token` from login response

### Using Python (httpx)

```python
import httpx

async with httpx.AsyncClient() as client:
    # Login
    response = await client.post(
        "http://localhost:8000/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password"}
    )
    token = response.json()["access_token"]
    
    # List organizations
    response = await client.get(
        "http://localhost:8000/api/v1/organizations",
        headers={"Authorization": f"Bearer {token}"}
    )
    orgs = response.json()
    print(orgs)
```

---

## Changelog

### v1.0.0 (2026-02-11) - Phase 1 Release
- Organizations CRUD
- Member management
- Settings management
- JWT authentication
- Multi-tenancy (RLS)

### Upcoming (Phase 2)
- Wallets API
- Transactions API
- Signatures API
- WebSocket support

---

## Support

- **Interactive Docs:** http://localhost:8000/docs (Swagger UI)
- **OpenAPI Spec:** http://localhost:8000/openapi.json
- **Issues:** Open a GitHub issue
- **Email:** api-support@orgon.dev

---

**API Documentation Version:** 1.0  
**Last Updated:** 2026-02-11
