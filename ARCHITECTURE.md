# ORGON Architecture

**Document Version:** 1.0  
**Last Updated:** 2026-02-11  
**Phase:** 1 (Multi-Tenancy Foundation)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Multi-Tenancy Design](#multi-tenancy-design)
3. [Component Architecture](#component-architecture)
4. [Data Flow](#data-flow)
5. [Security Model](#security-model)
6. [Performance Considerations](#performance-considerations)
7. [Deployment Architecture](#deployment-architecture)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         ORGON Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┐         ┌───────────────┐                │
│  │   Frontend    │◄───────►│   Backend     │                │
│  │  (Next.js)    │  REST   │   (FastAPI)   │                │
│  │   Port 3000   │  API    │   Port 8000   │                │
│  └───────────────┘         └───────┬───────┘                │
│         │                           │                         │
│         │                           ▼                         │
│         │                  ┌─────────────────┐               │
│         │                  │   PostgreSQL    │               │
│         │                  │   (Multi-Tenant)│               │
│         │                  │    Port 5432    │               │
│         │                  └─────────────────┘               │
│         │                                                     │
│         └─────────────────────────────────────────────────┐  │
│                                                             │  │
│  ┌──────────────────────────────────────────────────────┐ │  │
│  │              External Services (Phase 2)              │ │  │
│  │  - Safina API (Crypto Exchanges)                    │ │  │
│  │  - Blockchain Networks                               │ │  │
│  └──────────────────────────────────────────────────────┘ │  │
│                                                             │  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16 (App Router) | Server-side rendering, routing |
| | React 19 | UI components |
| | TypeScript 5 | Type safety |
| | Tailwind CSS 4 | Styling |
| | Radix UI | Accessible components |
| | next-intl | i18n (en/ru/ky) |
| **Backend** | FastAPI | REST API framework |
| | Python 3.12 | Runtime |
| | Pydantic V2 | Data validation |
| | asyncpg | Async PostgreSQL driver |
| | JWT | Authentication |
| **Database** | PostgreSQL 16 | Primary data store |
| | Row-Level Security | Multi-tenancy isolation |
| **Infrastructure** | Docker Compose | Local development |
| | Cloudflare Tunnel | Secure public access |
| | Neon Postgres | Production database |

---

## Multi-Tenancy Design

### Tenant Model

ORGON uses **Shared Database, Shared Schema** multi-tenancy:

- **Single Database:** All tenants share one PostgreSQL database
- **Shared Schema:** All tenants use the same table structure
- **Row-Level Security:** Postgres RLS enforces data isolation
- **Tenant Context:** Session-level `app.current_tenant` variable

### Tenant Isolation Flow

```
┌──────────────────────────────────────────────────────────┐
│ 1. User Login → JWT Token (user_id, organizations[])    │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 2. User Selects Organization (Frontend)                 │
│    → API Request with Authorization header              │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 3. Backend Validates JWT + Organization Membership      │
│    → set_tenant_context(organization_id)                │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│ 4. PostgreSQL RLS Policies Filter Queries               │
│    → Only returns rows for current tenant                │
└──────────────────────────────────────────────────────────┘
```

### Database Schema (Multi-Tenancy)

```sql
-- Core tenant table
CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE,
    license_type VARCHAR(20),  -- free, basic, pro, enterprise
    status VARCHAR(20),         -- active, suspended, cancelled
    -- ... other columns
);

-- User-Organization membership (many-to-many)
CREATE TABLE user_organizations (
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(20),  -- admin, operator, viewer
    PRIMARY KEY (user_id, organization_id)
);

-- Tenant-aware table (example: wallets)
CREATE TABLE wallets (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),  -- Tenant FK
    name VARCHAR(255),
    -- ... other columns
);

-- Enable RLS
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;

-- RLS Policy (read-permissive, write-restrictive)
CREATE POLICY tenant_isolation ON wallets
    USING (
        organization_id = current_setting('app.current_tenant', TRUE)::uuid
        OR
        EXISTS (
            SELECT 1 FROM user_organizations uo
            WHERE uo.organization_id = wallets.organization_id
              AND uo.user_id = current_setting('app.current_user', TRUE)::uuid
        )
    );
```

### Tenant Context Management

**Python Service Layer:**
```python
class OrganizationService:
    async def set_tenant_context(self, org_id: UUID):
        """Set RLS tenant context for current session."""
        await self._db.execute(
            "SELECT set_tenant_context($1)",
            params=(org_id,)
        )
    
    async def clear_tenant_context(self):
        """Clear RLS context (admin queries)."""
        await self._db.execute("SELECT clear_tenant_context()")
```

**PostgreSQL Functions:**
```sql
CREATE OR REPLACE FUNCTION set_tenant_context(tenant_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant', tenant_id::text, false);
END;
$$ LANGUAGE plpgsql;
```

### RLS Design Philosophy

**Read-Permissive:**
- Users can see organizations they're members of
- Supports cross-tenant reporting (for admins)
- Simplifies UI data fetching

**Write-Restrictive:**
- Only organization admins can modify data
- Enforced at database level
- Prevents accidental cross-tenant updates

**Trade-offs:**
- 62% query overhead (measured)
- Simplified application code
- Enhanced security guarantees

---

## Component Architecture

### Frontend (Next.js)

```
frontend/
├── app/
│   ├── [locale]/              # i18n routing (en/ru/ky)
│   │   ├── (auth)/            # Auth pages (login, register)
│   │   └── (dashboard)/       # Protected dashboard
│   │       ├── organizations/ # Organizations management
│   │       ├── wallets/       # Wallets (Phase 2)
│   │       └── transactions/  # Transactions (Phase 2)
│   └── api/                   # API routes (if needed)
├── components/
│   ├── ui/                    # Reusable UI components
│   ├── layout/                # Layout components (Header, Sidebar)
│   └── features/              # Feature-specific components
├── lib/
│   ├── api.ts                 # Centralized API client
│   ├── auth.ts                # Authentication utilities
│   └── utils.ts               # Helper functions
└── i18n/
    └── locales/               # Translations (en.json, ru.json, ky.json)
```

**Key Patterns:**
- **Server Components by default** (App Router)
- **Client Components** only when interactivity needed (`"use client"`)
- **Centralized API client** (`lib/api.ts`)
- **SWR for data fetching** (client-side caching)
- **i18n with next-intl** (server-side translations)

### Backend (FastAPI)

```
backend/
├── api/
│   ├── routes_auth.py         # Authentication endpoints
│   ├── routes_organizations.py# Organizations CRUD
│   ├── routes_wallets.py      # Wallets (Phase 2)
│   └── schemas.py             # Pydantic models
├── services/
│   ├── organization_service.py# Business logic (organizations)
│   ├── auth_service.py        # JWT, password hashing
│   └── event_manager.py       # Event publishing
├── database/
│   ├── db_postgres.py         # AsyncDatabase wrapper
│   └── pool.py                # Connection pooling
├── migrations/
│   ├── 000_base_schema.sql    # Initial schema
│   ├── 001_create_organizations.sql
│   └── ...
├── tests/
│   ├── test_organizations_simple.py
│   ├── test_organizations_e2e.py
│   └── ...
└── main.py                    # FastAPI app entry point
```

**Key Patterns:**
- **Layered architecture** (API → Service → Database)
- **Dependency injection** (FastAPI DI)
- **Async/await** throughout (asyncpg, asyncio)
- **Pydantic validation** (request/response models)
- **Event-driven** (event_manager for audit logs)

---

## Data Flow

### Request Flow (Organizations API)

```
1. Frontend Request
   │
   │  GET /api/v1/organizations
   │  Authorization: Bearer JWT_TOKEN
   │
   ▼
2. FastAPI Route
   │
   │  @router.get("/organizations")
   │  async def list_organizations(
   │      current_user = Depends(get_current_user)
   │  )
   │
   ▼
3. Auth Middleware
   │
   │  Validate JWT → Extract user_id
   │  Check organization membership
   │
   ▼
4. Service Layer
   │
   │  OrganizationService.list_organizations()
   │  ├─ set_tenant_context(org_id)  # Optional
   │  └─ Query database
   │
   ▼
5. Database Layer
   │
   │  AsyncDatabase.fetch(sql, params)
   │  ├─ RLS policies filter rows
   │  └─ Return matching organizations
   │
   ▼
6. Response
   │
   │  Pydantic models serialize to JSON
   │  FastAPI sends response
   │
   ▼
7. Frontend
   │
   │  SWR caches data
   │  React re-renders UI
```

### Database Connection Flow

```
┌─────────────────────────────────────────────┐
│ FastAPI App Startup                         │
│  ├─ Create asyncpg pool (min=5, max=20)    │
│  └─ Store in app.state.db_pool             │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│ Per-Request                                 │
│  ├─ Get connection from pool                │
│  ├─ Execute queries (via AsyncDatabase)    │
│  ├─ Commit transaction                      │
│  └─ Return connection to pool               │
└─────────────────────────────────────────────┘
```

---

## Security Model

### Authentication & Authorization

**Authentication (JWT):**
```python
# Login endpoint
@router.post("/auth/login")
async def login(credentials: LoginRequest):
    user = await auth_service.authenticate(email, password)
    access_token = auth_service.create_access_token(user_id=user.id)
    return {"access_token": access_token, "token_type": "bearer"}
```

**Authorization (Dependency):**
```python
# Protected endpoint
@router.get("/organizations")
async def list_organizations(
    current_user: User = Depends(get_current_user)  # JWT validation
):
    # current_user.id extracted from JWT
    return await service.list_organizations(current_user.id)
```

### Security Layers

| Layer | Mechanism | Purpose |
|-------|-----------|---------|
| **Transport** | HTTPS/TLS | Encrypt data in transit |
| **Authentication** | JWT tokens | Verify user identity |
| **Authorization** | Role checks | Verify user permissions |
| **Database** | RLS policies | Isolate tenant data |
| **Input Validation** | Pydantic | Prevent injection attacks |
| **Audit** | Event logging | Track all actions |

### Threat Model

**Threats Addressed:**
- ✅ **SQL Injection:** Pydantic validation + parameterized queries
- ✅ **XSS:** React auto-escaping + Content-Security-Policy
- ✅ **CSRF:** SameSite cookies + token validation
- ✅ **Tenant Isolation:** RLS policies + context checks
- ✅ **Privilege Escalation:** Role-based access control
- ✅ **Data Leakage:** Audit logs + encryption at rest

**Known Limitations:**
- RLS read-permissive design allows cross-tenant reads for members
- Application-layer role checks required (not DB-enforced)
- JWT rotation not yet implemented

---

## Performance Considerations

### Measured Benchmarks (Phase 1.4 Testing)

| Metric | Value | Acceptance |
|--------|-------|------------|
| **Throughput** | 616 orgs/sec | > 100 orgs/sec |
| **Avg Create Time** | 1.62ms/org | < 300ms |
| **Pagination** | <100ms (50 orgs) | < 150ms |
| **RLS Overhead** | 62% | < 100% |
| **Concurrent Creates** | 10 orgs <5s | < 10s |

### Optimization Strategies

**Database:**
- Connection pooling (asyncpg pool: min=5, max=20)
- Indexes on frequently queried columns (`slug`, `status`)
- RLS function optimization (minimize `set_config` calls)

**Backend:**
- Async/await throughout (no blocking I/O)
- Response caching (SWR on frontend)
- Batch operations where possible

**Frontend:**
- Server-side rendering (Next.js App Router)
- Static asset optimization (Turbopack)
- Code splitting (dynamic imports)

### Scalability Roadmap

**Current (Phase 1):**
- Single database instance
- Vertical scaling (increase CPU/RAM)
- Expected load: 1,000 organizations, 10,000 users

**Future (Phase 3):**
- Read replicas for reporting
- Redis caching layer
- Horizontal scaling (API servers)
- Expected load: 100,000+ organizations

---

## Deployment Architecture

### Development Environment

```
docker-compose.yml
├── postgres (port 5432)
├── backend (port 8000)
└── frontend (port 3000)
```

**Start:** `docker compose up -d`  
**Logs:** `docker compose logs -f`  
**Stop:** `docker compose down`

### Production Environment (Recommended)

```
┌─────────────────────────────────────────────┐
│          Cloudflare (DNS + CDN)             │
│  ├─ DDoS protection                         │
│  ├─ SSL/TLS termination                     │
│  └─ Static asset caching                    │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│     Cloudflare Tunnel (Optional)            │
│  ├─ Secure ingress (no exposed ports)      │
│  └─ Automatic HTTPS                         │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          Docker Host (VPS/Cloud)            │
│  ├─ Backend (FastAPI container)            │
│  ├─ Frontend (Next.js container)           │
│  └─ Reverse Proxy (Nginx/Traefik)          │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│      Neon Postgres (Serverless DB)          │
│  ├─ Automatic scaling                       │
│  ├─ Point-in-time recovery                  │
│  └─ Built-in connection pooling             │
└─────────────────────────────────────────────┘
```

**Production Checklist:**
- [ ] Set strong `JWT_SECRET_KEY`
- [ ] Configure `CORS_ORIGINS` (whitelist domains)
- [ ] Enable HTTPS (Cloudflare or Let's Encrypt)
- [ ] Set up database backups (Neon auto-backups)
- [ ] Configure monitoring (Sentry, Prometheus)
- [ ] Enable rate limiting (FastAPI middleware)
- [ ] Review RLS policies (audit tenant isolation)

---

## Future Enhancements (Roadmap)

### Phase 2: Safina Integration
- Crypto exchange API client
- Multi-signature wallet management
- Transaction signing workflows
- Blockchain network abstraction

### Phase 3: Advanced Features
- Analytics dashboard (transaction volume, fees)
- Reporting engine (CSV/PDF exports)
- Webhook system (real-time notifications)
- Admin panel (platform-wide management)

### Phase 4: Enterprise
- SSO integration (OAuth2, SAML)
- Audit trail export (compliance)
- Custom branding per tenant
- API rate limiting per organization

---

## References

- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Next.js Docs:** https://nextjs.org/docs
- **PostgreSQL RLS:** https://www.postgresql.org/docs/16/ddl-rowsecurity.html
- **Pydantic V2:** https://docs.pydantic.dev/2.0/
- **asyncpg:** https://magicstack.github.io/asyncpg/

---

**Document Maintenance:**
- Update after each phase completion
- Review architecture decisions quarterly
- Keep diagrams in sync with code

**Last Review:** 2026-02-11 (Phase 1.5)
