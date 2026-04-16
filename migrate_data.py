#!/usr/bin/env python3
"""
ORGON Data Migration: SQLite → PostgreSQL
Migrates all data from local SQLite to Neon PostgreSQL
"""

import sqlite3
import asyncio
import asyncpg
from datetime import datetime

SQLITE_DB = "data/orgon.db"
POSTGRES_URL = "postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"

TABLES = [
    "wallets",
    "transactions",
    "tx_signatures",
    "sync_state",
    "token_balances",
    "networks_cache",
    "tokens_info_cache",
    "balance_history",
    "signature_history",
    "pending_signatures_checked",
]


def convert_datetime(dt_str):
    """Convert SQLite datetime string to Python datetime."""
    if not dt_str:
        return None
    try:
        # Try ISO format first
        return datetime.fromisoformat(dt_str.replace(" ", "T"))
    except:
        try:
            # Try SQLite format
            return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except:
            return None


async def migrate_table(sqlite_conn, pg_conn, table_name):
    """Migrate one table from SQLite to PostgreSQL."""
    print(f"📦 Migrating {table_name}...")
    
    cursor = sqlite_conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    
    if not rows:
        print(f"   ⏭️  {table_name}: No data")
        return 0
    
    # Convert rows to list of dicts
    data = []
    for row in rows:
        row_dict = {}
        for col, val in zip(columns, row):
            # Convert datetime strings
            if col.endswith("_at") or col == "recorded_at":
                row_dict[col] = convert_datetime(val) if val else None
            else:
                row_dict[col] = val
        data.append(row_dict)
    
    # Build INSERT query
    placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
    insert_query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """
    
    # Insert data
    count = 0
    for row_dict in data:
        values = [row_dict[col] for col in columns]
        try:
            await pg_conn.execute(insert_query, *values)
            count += 1
        except Exception as e:
            print(f"   ⚠️  Error inserting row: {e}")
            print(f"      Row: {row_dict}")
    
    print(f"   ✅ {table_name}: {count}/{len(rows)} rows migrated")
    return count


async def main():
    print("🚀 ORGON Data Migration: SQLite → PostgreSQL\n")
    
    # Connect to SQLite
    print("📂 Connecting to SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    
    # Connect to PostgreSQL
    print("🐘 Connecting to PostgreSQL (Neon)...")
    pg_conn = await asyncpg.connect(POSTGRES_URL)
    
    # Migrate each table
    total_rows = 0
    for table in TABLES:
        try:
            count = await migrate_table(sqlite_conn, pg_conn, table)
            total_rows += count
        except Exception as e:
            print(f"   ❌ {table}: Failed - {e}")
    
    # Close connections
    sqlite_conn.close()
    await pg_conn.close()
    
    print(f"\n✅ Migration complete!")
    print(f"   Total rows migrated: {total_rows}")
    print(f"\n🔍 Verify:")
    print(f"   psql '{POSTGRES_URL}' -c \"SELECT 'wallets', COUNT(*) FROM wallets;\"")


if __name__ == "__main__":
    asyncio.run(main())
