#!/usr/bin/env python3
"""List all users in the database"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def list_users():
    db_url = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require")
    conn = await asyncpg.connect(db_url)
    try:
        users = await conn.fetch("SELECT id, email, full_name, role, is_active FROM users ORDER BY id")
        print("\n=== Users in Database ===\n")
        for user in users:
            print(f"ID: {user['id']}")
            print(f"Email: {user['email']}")
            print(f"Name: {user['full_name']}")
            print(f"Role: {user['role']}")
            print(f"Active: {user['is_active']}")
            print("-" * 40)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(list_users())
