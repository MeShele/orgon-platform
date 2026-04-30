#!/bin/sh
# ORGON backend container entrypoint.
#
# By default, just inits the SQLite fallback file and starts uvicorn.
# Two opt-in modes for greenfield deploys (Coolify, fresh VPS, etc.):
#
#   ORGON_AUTO_MIGRATE=1   apply backend/migrations/000_canonical_schema.sql
#                          on first boot when the schema_migrations marker
#                          is absent. Safe to leave on across restarts.
#
#   ORGON_AUTO_SEED=1      after migration, apply
#                          backend/migrations/seed_test_organizations.sql
#                          to insert the demo organisations + users + wallets
#                          (Demo Exchange KG / Demo Broker KG, demo-admin /
#                          demo-signer / demo-viewer @ orgon.io, password
#                          demo2026). Idempotent — uses ON CONFLICT DO NOTHING.

set -e

# 1. SQLite fallback file (used when DATABASE_URL is unset).
python3 -c "
import sqlite3, os
os.makedirs('/app/data', exist_ok=True)
c = sqlite3.connect('/app/data/orgon.db')
c.execute('CREATE TABLE IF NOT EXISTS sync_state (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS wallets (id TEXT PRIMARY KEY, network TEXT, address TEXT, name TEXT, balance REAL DEFAULT 0)')
c.execute('CREATE TABLE IF NOT EXISTS transactions (id TEXT PRIMARY KEY, wallet_id TEXT, tx_hash TEXT, amount REAL, status TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS signatures (id TEXT PRIMARY KEY, tx_id TEXT, signer TEXT, status TEXT)')
c.commit()
print('SQLite fallback ready')
"

# 2. Optional Postgres canonical apply (greenfield deploys).
if [ "${ORGON_AUTO_MIGRATE:-0}" = "1" ] && [ -n "${DATABASE_URL:-}" ]; then
    echo "[entrypoint] ORGON_AUTO_MIGRATE=1 — checking canonical schema marker"
    python3 - <<'PYEOF'
import asyncio, os, sys
from pathlib import Path

import asyncpg

CANONICAL = Path("/app/backend/migrations/000_canonical_schema.sql")

async def main():
    if not CANONICAL.exists():
        print(f"[entrypoint] {CANONICAL} not found — skipping auto-migrate", file=sys.stderr)
        return

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        # Probe for the marker. If schema_migrations doesn't exist yet, that
        # itself means a virgin DB and we apply the canonical.
        try:
            row = await conn.fetchval(
                "SELECT 1 FROM schema_migrations WHERE version = $1",
                "000_canonical_schema",
            )
        except asyncpg.UndefinedTableError:
            row = None

        if row:
            print("[entrypoint] canonical already applied — skipping")
        else:
            print("[entrypoint] applying canonical schema (one-time)")
            sql = CANONICAL.read_text(encoding="utf-8")
            await conn.execute(sql)
            print("[entrypoint] canonical applied")

        # Apply any post-canonical overlay migrations in numeric order. They
        # MUST be idempotent (each inserts its own schema_migrations row).
        overlay_dir = CANONICAL.parent
        overlay = sorted(
            p for p in overlay_dir.glob("0*.sql")
            if p.name != "000_canonical_schema.sql"
            and not p.name.startswith("._")
        )
        for f in overlay:
            print(f"[entrypoint] overlay → {f.name}")
            await conn.execute(f.read_text(encoding="utf-8"))
    finally:
        await conn.close()

asyncio.run(main())
PYEOF
fi

# 3. Optional demo seed (after migration).
if [ "${ORGON_AUTO_SEED:-0}" = "1" ] && [ -n "${DATABASE_URL:-}" ]; then
    echo "[entrypoint] ORGON_AUTO_SEED=1 — applying seed_test_organizations.sql"
    python3 - <<'PYEOF'
import asyncio, os, sys
from pathlib import Path

import asyncpg

SEED = Path("/app/backend/migrations/seed_test_organizations.sql")

async def main():
    if not SEED.exists():
        print(f"[entrypoint] {SEED} not found — skipping seed", file=sys.stderr)
        return
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        # Idempotency probe — if any of the demo users exists, assume
        # the seed already ran. Saves time on container restart.
        try:
            seeded = await conn.fetchval(
                "SELECT 1 FROM users WHERE email = 'demo-admin@orgon.io' LIMIT 1"
            )
        except Exception:
            # users table doesn't exist yet (somehow) — skip seed safely.
            print("[entrypoint] users table missing — skipping seed", file=sys.stderr)
            return
        if seeded:
            print("[entrypoint] seed already applied (demo-admin found) — skipping")
            return
        sql = SEED.read_text(encoding="utf-8")
        await conn.execute(sql)
        print("[entrypoint] seed applied — demo users / orgs / wallets ready")
    finally:
        await conn.close()

asyncio.run(main())
PYEOF
fi

# 4. Boot the API.
exec uvicorn backend.main:app --host 0.0.0.0 --port 8890
