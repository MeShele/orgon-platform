#!/usr/bin/env python3
"""
Restart AuthService with correct JWT secret
"""

import asyncio
import asyncpg
import sys
sys.path.append('/root/ORGON')

from backend.config import settings
from backend.services.auth_service import AuthService
import requests

async def main():
    print("Testing JWT after service restart...")
    
    # Test current config
    print(f"Current JWT_SECRET: {settings.SECRET_KEY[:20]}...")
    
    # Create fresh AuthService
    pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=5)
    auth_service = AuthService(pool)
    
    # Test token that was issued
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNSIsImVtYWlsIjoidGVzdDJAZXhhbXBsZS5jb20iLCJyb2xlIjoidmlld2VyIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc3MTAyOTg3NiwiaWF0IjoxNzcxMDI4OTc2fQ.EPNtRWE5yHAmSGurKHaIekNWjbAj_dDtqrGA5HyrNkM"
    
    # Test decode
    result = auth_service.decode_token(test_token)
    print(f"Token decode result: {result}")
    
    # Get user if token valid
    if result:
        user_id = int(result['sub'])
        user = await auth_service.get_user_by_id(user_id)
        print(f"User lookup result: {user}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())