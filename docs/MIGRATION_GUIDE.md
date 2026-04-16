# Migration Guide - SQLite to PostgreSQL

**Version:** 1.0.0  
**Last Updated:** 2026-02-08

This guide covers migrating ORGON from SQLite (development) to PostgreSQL (production).

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Migration Steps](#migration-steps)
4. [Verification](#verification)
5. [Rollback Procedure](#rollback-procedure)
6. [Troubleshooting](#troubleshooting)

---

## Overview

### Why PostgreSQL?

✅ **Production-ready** - Better concurrency, ACID compliance  
✅ **B2B Platform** - Supports UUID primary keys, JSONB, full-text search  
✅ **Performance** - Optimized indexes, query planner  
✅ **Scalability** - Connection pooling, replication  

### What's Migrated

- **Wallets** - All wallet data
- **Transactions** - Transaction history
- **Signatures** - Pending and completed signatures
- **Users** - User accounts and sessions
- **2FA** - TOTP secrets and backup codes
- **B2B Tables** - Partners, webhooks, audit log, analytics

---

## Prerequisites

### 1. PostgreSQL Database

We recommend **Neon.tech** (serverless PostgreSQL):

1. Sign up at https://neon.tech
2. Create a new project
3. Copy the connection string:
   ```
   postgresql://user:password@host/database?sslmode=require
   ```

**Alternative:** Self-hosted PostgreSQL 14+

```bash
# macOS (Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt-get install postgresql-14
sudo systemctl start postgresql
```

### 2. Backup SQLite Database

```bash
cd /path/to/ORGON

# Backup database
cp backend/orgon.db backend/orgon.db.backup

# Export to SQL (optional)
sqlite3 backend/orgon.db .dump > orgon_backup.sql
```

### 3. Install Dependencies

```bash
# Python PostgreSQL driver
pip install asyncpg

# Migration tools (optional)
pip install pgcli  # PostgreSQL CLI
```

---

## Migration Steps

### Step 1: Configure PostgreSQL Connection

Edit `backend/.env`:

```bash
# Old (SQLite)
# DATABASE_URL=sqlite:///backend/orgon.db

# New (PostgreSQL)
DATABASE_URL=postgresql://neondb_owner:PASSWORD@ep-late-sea-aglfcbe1-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require
```

Or use `.env`:

```bash
cd backend
cat > .env <<EOF
DATABASE_URL=postgresql://user:password@host/database?sslmode=require
SAFINA_EC_PRIVATE_KEY=your_key_here
JWT_SECRET_KEY=your_jwt_secret
EOF
```

### Step 2: Run Migrations

**Automatic (Recommended):**

```bash
cd /path/to/ORGON

# Run all migrations
python3 backend/database/migrations/run_migrations.py
```

**Manual (if needed):**

```bash
# Connect to PostgreSQL
psql "postgresql://user:password@host/database"

# Run migrations in order
\i backend/database/migrations/001_initial.sql
\i backend/database/migrations/002_two_factor_auth.sql
\i backend/database/migrations/003_users.sql
\i backend/database/migrations/004_scheduled_transactions.sql
\i backend/database/migrations/005_address_book.sql
\i backend/database/migrations/006_audit_log.sql
\i backend/database/migrations/007_users.sql
\i backend/database/migrations/008_asystem_b2b_platform.sql
\i backend/database/migrations/009_webhooks.sql
\i backend/database/migrations/010_performance_indexes.sql
```

### Step 3: Migrate Data

**Option A: Fresh Start (No Existing Data)**

Skip this step. Your database is ready.

**Option B: Migrate Existing Data**

```bash
# Export SQLite data to JSON
python3 backend/database/export_sqlite.py > data_export.json

# Import to PostgreSQL
python3 backend/database/import_postgres.py < data_export.json
```

**Create export script:**

```python
# backend/database/export_sqlite.py
import sqlite3
import json

db = sqlite3.connect('backend/orgon.db')
db.row_factory = sqlite3.Row

# Export wallets
wallets = db.execute("SELECT * FROM wallets").fetchall()
print(json.dumps({
    'wallets': [dict(w) for w in wallets]
}))
```

**Create import script:**

```python
# backend/database/import_postgres.py
import asyncio
import asyncpg
import json
import sys

async def main():
    data = json.load(sys.stdin)
    
    conn = await asyncpg.connect(
        "postgresql://user:password@host/database"
    )
    
    # Import wallets
    for wallet in data['wallets']:
        await conn.execute("""
            INSERT INTO wallets (name, network, wallet_type, info, addr)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (name) DO NOTHING
        """, wallet['name'], wallet['network'], wallet['wallet_type'],
            wallet['info'], wallet.get('addr'))
    
    await conn.close()

asyncio.run(main())
```

### Step 4: Update Application Code

**No code changes needed!** The backend auto-detects PostgreSQL via `DATABASE_URL`.

```python
# backend/database/db_postgres.py (already exists)
class AsyncDatabase:
    async def connect(self, database_url: str):
        self.pool = await asyncpg.create_pool(database_url)
```

### Step 5: Test Connection

```bash
# Test PostgreSQL connection
python3 -c "
import asyncio
import asyncpg

async def test():
    conn = await asyncpg.connect('YOUR_DATABASE_URL')
    version = await conn.fetchval('SELECT version()')
    print(f'Connected: {version}')
    await conn.close()

asyncio.run(test())
"
```

### Step 6: Start Backend

```bash
cd backend
python3 main.py
```

**Verify logs:**

```
INFO: Using PostgreSQL database
INFO: Database initialized
INFO: Application startup complete
INFO: Uvicorn running on http://0.0.0.0:8890
```

---

## Verification

### 1. Check Tables

```bash
psql "YOUR_DATABASE_URL"

# List tables
\dt

# Expected output:
# wallets, transactions, signatures, users, partners, webhooks, etc.
```

### 2. Query Data

```sql
-- Count wallets
SELECT COUNT(*) FROM wallets;

-- List recent transactions
SELECT * FROM transactions ORDER BY created_at DESC LIMIT 10;

-- Check B2B tables
SELECT name, tier, status FROM partners;
```

### 3. Test API Endpoints

```bash
# Health check
curl http://localhost:8890/health

# List wallets
curl http://localhost:8890/api/wallets

# Create test wallet (requires authentication)
curl -X POST http://localhost:8890/api/wallets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"name": "test-wallet", "network_id": 5010, "wallet_type": 1}'
```

### 4. Check Indexes

```sql
-- List indexes
SELECT tablename, indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;

-- Verify performance indexes exist
SELECT COUNT(*) FROM pg_indexes
WHERE schemaname = 'public' AND indexname LIKE 'idx_%';
-- Expected: 100+ indexes
```

---

## Rollback Procedure

### If Migration Fails

**1. Stop backend:**

```bash
# Kill process
pkill -f "python3 main.py"

# Or via PM2 (if using)
pm2 stop orgon-backend
```

**2. Restore SQLite connection:**

```bash
# Edit backend/.env
DATABASE_URL=sqlite:///backend/orgon.db
```

**3. Restore SQLite backup (if needed):**

```bash
cp backend/orgon.db.backup backend/orgon.db
```

**4. Restart backend:**

```bash
cd backend
python3 main.py
```

### If Data Lost

**1. Check PostgreSQL backup:**

```bash
# Neon.tech: Use dashboard to restore snapshot
# Self-hosted: Restore from pg_dump

pg_restore -d database_name backup.dump
```

**2. Re-import from SQLite:**

```bash
python3 backend/database/export_sqlite.py > data_export.json
python3 backend/database/import_postgres.py < data_export.json
```

---

## Troubleshooting

### Connection Refused

**Symptom:**
```
asyncpg.exceptions.ConnectionRefusedError: connection refused
```

**Fix:**
1. Verify PostgreSQL is running: `pg_isready`
2. Check connection string: `psql "YOUR_DATABASE_URL"`
3. Verify firewall allows port 5432
4. Check Neon.tech dashboard (if using)

### Authentication Failed

**Symptom:**
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed
```

**Fix:**
1. Copy exact connection string from Neon.tech
2. Check for special characters in password (URL-encode if needed)
3. Verify username is correct

### Table Already Exists

**Symptom:**
```
asyncpg.exceptions.DuplicateTableError: relation "wallets" already exists
```

**Fix:**
```sql
-- Drop all tables (CAUTION: deletes data)
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

-- Re-run migrations
python3 backend/database/migrations/run_migrations.py
```

### Slow Queries

**Symptom:** API responses >500ms

**Fix:**

1. **Check missing indexes:**
   ```sql
   SELECT schemaname, tablename, indexname
   FROM pg_indexes
   WHERE schemaname = 'public' AND indexname LIKE 'idx_%';
   ```

2. **Analyze query plan:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM transactions WHERE wallet_id = 123;
   ```

3. **Re-run index migration:**
   ```bash
   psql "YOUR_DATABASE_URL" < backend/database/migrations/010_performance_indexes.sql
   ```

### Connection Pool Exhausted

**Symptom:**
```
asyncpg.exceptions.TooManyConnectionsError: too many connections
```

**Fix:**

1. **Increase pool size** (backend/database/db_postgres.py):
   ```python
   self.pool = await asyncpg.create_pool(
       database_url,
       min_size=5,
       max_size=20  # Increase from default 10
   )
   ```

2. **Check active connections:**
   ```sql
   SELECT COUNT(*) FROM pg_stat_activity;
   ```

3. **Close idle connections:**
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle' AND state_change < NOW() - INTERVAL '5 minutes';
   ```

---

## Performance Optimization

### After Migration

**1. Analyze tables:**

```sql
ANALYZE wallets;
ANALYZE transactions;
ANALYZE partners;
-- ... for all tables
```

**2. Vacuum database:**

```sql
VACUUM FULL;
```

**3. Enable autovacuum (if not enabled):**

```sql
ALTER TABLE wallets SET (autovacuum_enabled = true);
```

**4. Monitor slow queries:**

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- View slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

---

## Production Checklist

Before going live:

- [ ] PostgreSQL database created (Neon.tech or self-hosted)
- [ ] All migrations run successfully
- [ ] Indexes created (100+ indexes verified)
- [ ] Data migrated (if applicable)
- [ ] Connection pool configured (min=5, max=20)
- [ ] Backup strategy in place (daily snapshots)
- [ ] Monitoring enabled (Prometheus metrics)
- [ ] SSL/TLS enforced (sslmode=require)
- [ ] Environment variables set (.env file)
- [ ] Backend tested (all API endpoints working)
- [ ] Frontend connected (no errors in console)
- [ ] Load testing passed (100 req/s)

---

## Support

**Issues?** Contact support:

- Email: support@asystem.ai
- Telegram: @urmatdigital
- GitHub: https://github.com/asystem/orgon/issues

---

**Last updated:** 2026-02-08  
**Version:** 1.0.0
