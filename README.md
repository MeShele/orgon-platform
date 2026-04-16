# ORGON - Multi-Signature Wallet Platform

**ORGON** is a multi-tenancy, multi-signature cryptocurrency wallet platform designed for crypto exchanges and financial institutions. Built with Next.js 16, FastAPI, and PostgreSQL.

> **Status:** Phase 1 complete (Multi-Tenancy Foundation)  
> **Version:** 1.0.0-alpha  
> **License:** Proprietary

---

## Features

### Phase 1: Multi-Tenancy Foundation ✅
- **Organizations Management:** Create and manage multiple organizations (exchanges)
- **Role-Based Access Control:** Admin, Operator, Viewer roles
- **Row-Level Security (RLS):** Postgres-based tenant isolation
- **Settings Management:** Billing, KYC, features per organization
- **Audit Logging:** Complete activity tracking

### Phase 2: Safina Integration (In Progress)
- Crypto exchange API integration
- Multi-signature wallet workflows
- Transaction scheduling
- Real-time price feeds

---

## Architecture

### Tech Stack

**Frontend:**
- Next.js 16 (App Router, Turbopack)
- React 19
- TypeScript 5
- Tailwind CSS 4
- Radix UI + Framer Motion
- i18n (en/ru/ky)

**Backend:**
- FastAPI (Python 3.12)
- PostgreSQL 16 + asyncpg
- JWT Authentication
- Pydantic validation
- Event-driven architecture

**Infrastructure:**
- Docker + Docker Compose
- Cloudflare Tunnel (optional)
- Neon Postgres (production)

### Database Schema

```
users
  ├── organizations (multi-tenancy)
  │   ├── organization_settings
  │   └── user_organizations (members)
  ├── wallets
  │   └── wallet_users
  ├── transactions
  │   └── signatures
  └── audit_logs
```

**Multi-Tenancy Model:**
- Each organization is a tenant
- Row-Level Security (RLS) enforces data isolation
- Users can belong to multiple organizations
- Context switching via `set_tenant_context()`

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.12+ (for local backend dev)

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd ORGON
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your values:
# - DATABASE_URL (Postgres connection)
# - JWT_SECRET_KEY
# - CORS_ORIGINS
```

3. **Start services:**
```bash
docker compose up -d
```

4. **Apply database migrations:**
```bash
docker compose exec backend python -c "
from backend.migrations.runner import apply_migrations
apply_migrations()
"
```

5. **Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev        # Start dev server (port 3000)
npm run build      # Production build
npm run lint       # ESLint check
```

**Project Structure:**
```
frontend/
├── src/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components
│   ├── lib/              # Utilities, API client
│   └── i18n/             # Translations (en/ru/ky)
└── public/               # Static assets
```

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Project Structure:**
```
backend/
├── api/                  # FastAPI routes & schemas
├── services/             # Business logic
├── database/             # Database layer
├── migrations/           # SQL migrations
├── tests/                # Pytest test suites
└── main.py               # FastAPI application
```

---

## Testing

### Run All Tests

```bash
# Backend tests (24 test cases)
docker compose exec backend pytest -v

# Frontend tests (if configured)
cd frontend && npm test
```

### Test Suites

1. **Basic Tests** (10 tests)
   - CRUD operations
   - Member management
   - Settings management

2. **E2E Tests** (4 tests)
   - Organization creation flow
   - Member workflows
   - Tenant isolation

3. **Performance Tests** (5 tests)
   - Throughput: 616 orgs/sec
   - Pagination: <100ms
   - RLS overhead: 62%

4. **Security Tests** (5 tests)
   - SQL injection resistance
   - RLS bypass prevention
   - Permission escalation checks

**Test Coverage:** 100% of Organizations API

---

## Database Migrations

### Create Migration

```bash
# Create new migration file
cat > backend/migrations/007_your_migration.sql << 'EOF'
-- Migration 007: Description
-- Phase: 1.x
-- Date: YYYY-MM-DD

-- Your SQL here
CREATE TABLE ...;
EOF
```

### Apply Migrations

```bash
# Via Docker
docker compose exec backend python -c "
from backend.migrations.runner import apply_migrations
apply_migrations()
"

# Or manually via psql
docker compose exec postgres psql -U orgon_user -d orgon_db -f /app/backend/migrations/007_your_migration.sql
```

### Migration Files (Current)

- `000_base_schema.sql` - Users, sessions
- `001_create_organizations.sql` - Organizations table
- `002_add_tenant_columns.sql` - Tenant context
- `003_create_user_organizations.sql` - Members
- `004_create_tenant_settings.sql` - Settings
- `005_enable_rls_policies.sql` - RLS functions
- `006_create_billing_tables.sql` - Billing

---

## API Documentation

### Interactive API Docs

**Swagger UI:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

### Key Endpoints

#### Organizations
```http
POST   /api/v1/organizations          # Create organization
GET    /api/v1/organizations          # List organizations
GET    /api/v1/organizations/{id}     # Get organization
PATCH  /api/v1/organizations/{id}     # Update organization
DELETE /api/v1/organizations/{id}     # Delete (soft)
```

#### Members
```http
GET    /api/v1/organizations/{id}/members              # List members
POST   /api/v1/organizations/{id}/members              # Add member
PATCH  /api/v1/organizations/{id}/members/{user_id}    # Update role
DELETE /api/v1/organizations/{id}/members/{user_id}    # Remove member
```

#### Settings
```http
GET    /api/v1/organizations/{id}/settings    # Get settings
PATCH  /api/v1/organizations/{id}/settings    # Update settings
```

### Authentication

All API requests require JWT token:

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl http://localhost:8000/api/v1/organizations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Deployment

### Docker Production Build

```bash
# Build images
docker compose -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### Environment Variables (Production)

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Security
JWT_SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://yourdomain.com

# Optional
CLOUDFLARE_TUNNEL_TOKEN=your-tunnel-token
SAFINA_API_KEY=your-safina-api-key
```

### Cloudflare Tunnel (Optional)

Secure public access without exposing ports:

```bash
# Set CLOUDFLARE_TUNNEL_TOKEN in .env
docker compose up -d cloudflared
```

---

## Multi-Tenancy Guide

### Tenant Context

Organizations use Row-Level Security (RLS) for data isolation:

```python
# Set tenant context (Python service layer)
await service.set_tenant_context(organization_id)

# Queries now filtered to this organization
orgs = await service.list_organizations()  # Returns only accessible orgs

# Clear context
await service.clear_tenant_context()
```

### RLS Design

- **Read-permissive:** Users can see organizations they're members of
- **Write-restrictive:** Only admins can modify organization data
- **Context-aware:** Queries automatically filtered by tenant_id

### Adding Tenant-Aware Tables

```sql
-- 1. Add organization_id column
ALTER TABLE your_table ADD COLUMN organization_id UUID REFERENCES organizations(id);

-- 2. Enable RLS
ALTER TABLE your_table ENABLE ROW LEVEL SECURITY;

-- 3. Create RLS policy
CREATE POLICY tenant_isolation ON your_table
  USING (organization_id = current_setting('app.current_tenant', TRUE)::uuid);
```

---

## Troubleshooting

### Common Issues

**Frontend build fails:**
```bash
# Clear cache and rebuild
cd frontend
rm -rf .next node_modules
npm install
npm run build
```

**Backend tests fail:**
```bash
# Reset test database
docker compose down -v
docker compose up -d postgres
# Wait 10 seconds for DB to initialize
docker compose exec postgres psql -U orgon_user -d orgon_db -f /app/backend/migrations/000_base_schema.sql
# Re-run tests
docker compose exec backend pytest
```

**Database connection errors:**
```bash
# Check Postgres is running
docker compose ps postgres

# Test connection
docker compose exec postgres psql -U orgon_user -d orgon_db -c "SELECT 1;"
```

---

## Contributing

### Code Style

**Frontend:**
- ESLint + Prettier
- TypeScript strict mode
- Tailwind CSS (no inline styles)

**Backend:**
- Black formatter
- Type hints (mypy)
- Docstrings (Google style)

### Testing Requirements

- All new features must have tests
- Maintain 100% passing test suite
- Performance benchmarks for critical paths

---

## Roadmap

- [x] **Phase 1.1:** Database Design (Multi-Tenancy)
- [x] **Phase 1.2:** Backend API (Organizations CRUD)
- [x] **Phase 1.3:** Frontend UI (Organizations Management)
- [x] **Phase 1.4:** Testing (Basic + E2E + Performance + Security)
- [x] **Phase 1.5:** Documentation (This README)
- [ ] **Phase 2.1:** Safina Exchange Integration
- [ ] **Phase 2.2:** Multi-Signature Wallets
- [ ] **Phase 2.3:** Transaction Management
- [ ] **Phase 3:** Advanced Features (Analytics, Reporting)

---

## License

Proprietary - All rights reserved  
© 2026 ORGON Project

---

## Support

- **Issues:** Open a GitHub issue
- **Email:** support@orgon.dev
- **Documentation:** [docs.orgon.dev](https://docs.orgon.dev)

---

## Acknowledgments

Built with:
- [Next.js](https://nextjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [PostgreSQL](https://www.postgresql.org/)
- [Aceternity UI](https://ui.aceternity.com/)

**Development:** Forge (Atlas Chief Worker) + Team
