#!/usr/bin/env python3
"""Test PostgreSQL connection and basic queries."""

import asyncio
import os
from dotenv import load_dotenv
from backend.database.db_postgres import AsyncDatabase

load_dotenv()

async def main():
    db_url = os.getenv("DATABASE_URL")
    print(f"🔗 Connecting to PostgreSQL...")
    print(f"   URL: {db_url[:50]}...")
    
    db = AsyncDatabase(db_url)
    await db.connect()
    
    try:
        # Test query
        print("\n📊 Querying data...")
        
        wallets = await db.fetch("SELECT name, network, label FROM wallets")
        print(f"   Wallets: {len(wallets)}")
        for w in wallets:
            print(f"      - {w['name']} (network {w['network']}): {w['label'] or '(no label)'}")
        
        tx_count = await db.fetchval("SELECT COUNT(*) FROM transactions")
        print(f"   Transactions: {tx_count}")
        
        networks = await db.fetch("SELECT network_id, network_name FROM networks_cache ORDER BY network_id")
        print(f"   Networks: {len(networks)}")
        for n in networks:
            print(f"      - {n['network_id']}: {n['network_name']}")
        
        print("\n✅ PostgreSQL connection works!")
        
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(main())
