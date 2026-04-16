#!/usr/bin/env python3
"""Reset password for test users"""
import asyncio
import asyncpg
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

async def reset_passwords():
    db_url = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require")
    conn = await asyncpg.connect(db_url)
    try:
        # Hash passwords
        test_pwd = bcrypt.hashpw("test1234".encode(), bcrypt.gensalt()).decode()
        admin_pwd = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        
        # Update test@orgon.app
        await conn.execute("""
            UPDATE users SET password_hash = $1 WHERE email = $2
        """, test_pwd, "test@orgon.app")
        print("✅ Updated password for test@orgon.app → test1234")
        
        # Check if admin@orgon.app exists
        admin = await conn.fetchrow("SELECT id FROM users WHERE email = $1", "admin@orgon.app")
        if admin:
            await conn.execute("""
                UPDATE users SET password_hash = $1 WHERE email = $2
            """, admin_pwd, "admin@orgon.app")
            print("✅ Updated password for admin@orgon.app → admin123")
        else:
            # Create admin@orgon.app
            await conn.execute("""
                INSERT INTO users (email, password_hash, full_name, role, is_active)
                VALUES ($1, $2, $3, $4, $5)
            """, "admin@orgon.app", admin_pwd, "Admin", "admin", True)
            print("✅ Created admin@orgon.app → admin123")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(reset_passwords())
