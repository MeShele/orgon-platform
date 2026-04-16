#!/usr/bin/env python3

# Test JWT verification directly through AuthService

import sys
sys.path.append('/root/ORGON')
import asyncio
import asyncpg
from backend.config import settings 
from backend.services.auth_service import AuthService, JWT_SECRET

async def test_jwt():
    # Connect to database
    pool = await asyncpg.create_pool(settings.DATABASE_URL, min_size=1, max_size=5)
    
    # Create AuthService
    auth_service = AuthService(pool)
    
    print(f"JWT_SECRET in config: {settings.SECRET_KEY[:20]}...")
    print(f"JWT_SECRET in auth_service: {JWT_SECRET[:20]}...")
    print(f"Are they equal? {settings.SECRET_KEY == JWT_SECRET}")
    
    # Test token
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNSIsImVtYWlsIjoidGVzdDJAZXhhbXBsZS5jb20iLCJyb2xlIjoidmlld2VyIiwidHlwZSI6ImFjY2VzcyIsImV4cCI6MTc3MTAyOTY5MiwiaWF0IjoxNzcxMDI4NzkyfQ.8o91L8dKFiYbmpaM0677cJ6QtCb0CIJOTubhpr5_fkc"
    
    result = auth_service.decode_token(test_token)
    print(f"Token decode result: {result}")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(test_jwt())