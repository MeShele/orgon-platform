"""Debug endpoints for testing."""
from fastapi import APIRouter, Request
from typing import Dict, Any

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/app-state")
async def get_app_state(request: Request) -> Dict[str, Any]:
    """Get all attributes of app.state."""
    state_attrs = {}
    
    for attr in dir(request.app.state):
        if not attr.startswith('_'):
            try:
                value = getattr(request.app.state, attr)
                state_attrs[attr] = {
                    "type": type(value).__name__,
                    "exists": True
                }
            except Exception as e:
                state_attrs[attr] = {
                    "error": str(e),
                    "exists": False
                }
    
    return {
        "app_state_attributes": state_attrs,
        "has_auth_service": hasattr(request.app.state, 'auth_service'),
        "has_user_service": hasattr(request.app.state, 'user_service')
    }


@router.get("/test-auth-service")
async def test_auth_service(request: Request) -> Dict[str, Any]:
    """Test if auth_service can be accessed from dependency."""
    try:
        from backend.dependencies import get_auth_service
        auth_service = get_auth_service(request)
        
        return {
            "success": True,
            "auth_service_type": type(auth_service).__name__,
            "has_pool": hasattr(auth_service, 'pool'),
            "pool_type": type(auth_service.pool).__name__ if hasattr(auth_service, 'pool') else None
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
