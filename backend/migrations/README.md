# ORGON Database Migrations

**Phase:** 1.1 Database Design  
**Purpose:** Multi-tenancy for ORGON-Safina Integration (170+ crypto exchanges)  
**Created:** 2026-02-10

---

## Migration Files

| File | Description | Dependencies |
|------|-------------|--------------|
| `001_create_organizations.sql` | Core multi-tenant table | None |
| `002_add_tenant_columns.sql` | Add `organization_id` to existing tables | 001 |
| `003_create_user_organizations.sql` | User-Organization M2M (role-based) | 001 |
| `004_create_tenant_settings.sql` | Organization settings (features, limits, branding) | 001 |
| `005_enable_rls_policies.sql` | Row-Level Security (RLS) for tenant isolation | 001, 002 |

---

## How to Apply Migrations

### Option 1: PostgreSQL CLI (psql)

```bash
# Connect to database
psql -h localhost -U orgon_user -d orgon_db

# Apply migrations in order
\i backend/migrations/001_create_organizations.sql
\i backend/migrations/002_add_tenant_columns.sql
\i backend/migrations/003_create_user_organizations.sql
\i backend/migrations/004_create_tenant_settings.sql
\i backend/migrations/005_enable_rls_policies.sql

# Verify tables
\dt
\d organizations
\d user_organizations
\d organization_settings
```

### Option 2: Python Script (via asyncpg)

```python
import asyncpg

async def run_migrations():
    conn = await asyncpg.connect(
        host='localhost',
        user='orgon_user',
        password='your_password',
        database='orgon_db'
    )
    
    migrations = [
        '001_create_organizations.sql',
        '002_add_tenant_columns.sql',
        '003_create_user_organizations.sql',
        '004_create_tenant_settings.sql',
        '005_enable_rls_policies.sql',
    ]
    
    for migration in migrations:
        with open(f'backend/migrations/{migration}', 'r') as f:
            sql = f.read()
            await conn.execute(sql)
            print(f'✅ Applied: {migration}')
    
    await conn.close()

# Run
import asyncio
asyncio.run(run_migrations())
```

### Option 3: Docker (via running container)

```bash
# Copy migrations to container
docker cp backend/migrations/. orgon-backend:/tmp/migrations/

# Execute migrations
docker exec -it orgon-backend bash
cd /tmp/migrations
psql $DATABASE_URL -f 001_create_organizations.sql
psql $DATABASE_URL -f 002_add_tenant_columns.sql
psql $DATABASE_URL -f 003_create_user_organizations.sql
psql $DATABASE_URL -f 004_create_tenant_settings.sql
psql $DATABASE_URL -f 005_enable_rls_policies.sql
```

---

## Testing RLS (Row-Level Security)

After applying all migrations, test RLS isolation:

```sql
-- 1. Create 2 test organizations
INSERT INTO organizations (name, slug, license_type) VALUES
    ('Safina Exchange KG', 'safina-kg', 'enterprise'),
    ('BitExchange KG', 'bitexchange-kg', 'pro');

-- 2. Create a test wallet for Organization A
INSERT INTO wallets (name, address, organization_id)
VALUES ('Test Wallet A', '0xABC...', (SELECT id FROM organizations WHERE slug = 'safina-kg'));

-- 3. Set context for Organization A
SELECT set_tenant_context((SELECT id FROM organizations WHERE slug = 'safina-kg'), false);

-- 4. Query wallets (should return only Org A's wallet)
SELECT * FROM wallets;
-- Expected: 1 row (Test Wallet A)

-- 5. Clear context and set for Organization B
SELECT clear_tenant_context();
SELECT set_tenant_context((SELECT id FROM organizations WHERE slug = 'bitexchange-kg'), false);

-- 6. Query wallets (should return nothing)
SELECT * FROM wallets;
-- Expected: 0 rows (Org B has no wallets)

-- 7. Set Super Admin context
SELECT set_tenant_context('00000000-0000-0000-0000-000000000000', true);

-- 8. Query wallets (should return all)
SELECT * FROM wallets;
-- Expected: 1+ rows (all wallets)
```

**✅ RLS works correctly if:**
- Organization A sees only its data
- Organization B sees only its data (0 rows in test)
- Super Admin sees all data

---

## Backend Integration

### Middleware Example (FastAPI)

```python
from fastapi import Request
import asyncpg

async def set_tenant_context_middleware(request: Request, call_next):
    # Extract organization_id from JWT token
    user = request.state.user
    org_id = user.current_organization_id
    is_admin = user.is_super_admin
    
    # Set RLS context in database
    async with request.app.state.db.acquire() as conn:
        await conn.execute(
            "SELECT set_tenant_context($1, $2)",
            org_id, is_admin
        )
    
    response = await call_next(request)
    
    # Clear context after request
    async with request.app.state.db.acquire() as conn:
        await conn.execute("SELECT clear_tenant_context()")
    
    return response
```

### Service Example

```python
class WalletService:
    async def get_wallets(self, conn: asyncpg.Connection):
        # No need to filter by organization_id manually!
        # RLS automatically filters based on session context
        return await conn.fetch("SELECT * FROM wallets")
```

---

## Rollback Migrations

If needed, rollback in **reverse order**:

```sql
-- 005: Disable RLS
ALTER TABLE wallets DISABLE ROW LEVEL SECURITY;
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE signatures DISABLE ROW LEVEL SECURITY;
ALTER TABLE contacts DISABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;

DROP FUNCTION IF EXISTS set_tenant_context(UUID, BOOLEAN);
DROP FUNCTION IF EXISTS clear_tenant_context();

-- 004: Drop organization_settings
DROP TABLE IF EXISTS organization_settings CASCADE;

-- 003: Drop user_organizations
DROP TABLE IF EXISTS user_organizations CASCADE;

-- 002: Remove organization_id columns
ALTER TABLE wallets DROP COLUMN IF EXISTS organization_id;
ALTER TABLE transactions DROP COLUMN IF EXISTS organization_id;
ALTER TABLE signatures DROP COLUMN IF EXISTS organization_id;
ALTER TABLE contacts DROP COLUMN IF EXISTS organization_id;
ALTER TABLE scheduled_transactions DROP COLUMN IF EXISTS organization_id;
ALTER TABLE audit_logs DROP COLUMN IF EXISTS organization_id;

-- 001: Drop organizations
DROP TABLE IF EXISTS organizations CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column();
```

---

## Next Steps

After applying migrations:

1. **Create seed data** (2 test organizations)
2. **Update backend models** (add `organization_id` field)
3. **Update backend services** (use RLS context)
4. **Add organization selector** to frontend UI
5. **Write integration tests** (RLS isolation checks)

---

## Security Notes

⚠️ **CRITICAL:** Always call `set_tenant_context()` at the start of each request!

Without it, RLS will block all queries (no `app.current_organization_id` set).

✅ **Best Practices:**
- Use middleware to set context automatically
- Never trust client-provided `organization_id` — get it from JWT token
- Log all RLS context changes for audit
- Test RLS isolation thoroughly before production

---

**Status:** ✅ Migrations ready for dev testing  
**Next:** Apply to dev database → Seed data → Integration tests
