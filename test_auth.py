import asyncio
import asyncpg
from backend.services.auth_service import AuthService
from backend.api.routes_auth import login, LoginRequest
from fastapi import Request, FastAPI
from unittest.mock import Mock

async def test():
    # Create pool
    pool = await asyncpg.create_pool(
        'postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require',
        min_size=1,
        max_size=2
    )
    
    # Create auth service
    auth_service = AuthService(pool)
    
    # Create mock request with app.state
    app = FastAPI()
    app.state.auth_service = auth_service
    
    request = Mock(spec=Request)
    request.app = app
    
    # Create login request
    login_data = LoginRequest(email='test@orgon.app', password='test1234')
    
    # Try to call endpoint
    try:
        result = await login(login_data, request, auth_service)
        print('SUCCESS:', result.dict() if hasattr(result, 'dict') else result)
    except Exception as e:
        print('ERROR:', e)
        import traceback
        traceback.print_exc()
    
    await pool.close()

asyncio.run(test())
