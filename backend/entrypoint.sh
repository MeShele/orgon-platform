#!/bin/sh
# ORGON backend container entrypoint.
#
# By default, just inits the SQLite fallback file and starts uvicorn.
# Set `ORGON_AUTO_MIGRATE=1` to also apply the canonical Postgres schema
# (only when the `schema_migrations` marker for it is absent — so safe
# to leave on across restarts). Useful for greenfield Coolify deploys.

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

# 3. Boot the API.
exec uvicorn backend.main:app --host 0.0.0.0 --port 8890
