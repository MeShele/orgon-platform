"""
Shared dependencies for FastAPI routes.
Provides database connections, services, and auth dependencies.
"""

from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.services.auth_service import AuthService
from backend.services.organization_service import OrganizationService
import asyncpg

# Security scheme for JWT
security = HTTPBearer()


# ==================== Database Pool ====================

def get_db_pool(request: Request) -> asyncpg.Pool:
    """Get database connection pool from app state."""
    return request.app.state.db_pool


# ==================== Service Dependencies ====================

def get_auth_service(request: Request) -> AuthService:
    """Get AuthService instance from app state."""
    if not hasattr(request.app.state, 'auth_service'):
        pool = get_db_pool(request)
        request.app.state.auth_service = AuthService(pool)
    return request.app.state.auth_service


def get_organization_service(request: Request) -> OrganizationService:
    """Get OrganizationService instance from app state."""
    if not hasattr(request.app.state, 'organization_service'):
        pool = get_db_pool(request)
        request.app.state.organization_service = OrganizationService(pool)
    return request.app.state.organization_service


# ==================== Auth Dependencies ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
):
    """
    Dependency to get current authenticated user from JWT token.
    
    Returns:
        dict: User data with keys: id, email, role, full_name, is_active
    
    Raises:
        HTTPException 401: If token is invalid or expired
    """
    auth_service = get_auth_service(request)
    token = credentials.credentials
    
    # Decode JWT token
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract user_id from token
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user from database
    user = await auth_service.get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check if user is active
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    return user


async def get_current_active_user(
    user: dict = Depends(get_current_user)
):
    """
    Dependency to get current active user.
    (Already checked in get_current_user, but kept for compatibility)
    """
    return user


async def require_role(role: str):
    """
    Dependency factory to require specific role.
    
    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(user: dict = Depends(get_current_user)):
        if user.get("role") != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: {role} role required"
            )
        return user
    return check_role


async def require_admin(user: dict = Depends(get_current_user)):
    """Dependency to require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


async def require_signer(user: dict = Depends(get_current_user)):
    """Dependency to require signer or admin role."""
    if user.get("role") not in ("admin", "signer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signer or admin access required"
        )
    return user


# ==================== Optional Auth ====================

async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
):
    """
    Optional auth dependency - returns user if token present, None otherwise.
    Does not raise 401 if no token.
    """
    try:
        return await get_current_user(credentials, request)
    except HTTPException:
        return None


# ==================== Organization Isolation ====================

async def get_user_org_ids(
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """
    Get organization IDs the user belongs to.
    Returns None for super_admin/admin (no filtering).
    Returns list of UUIDs for regular users.
    """
    role = current_user.get("role", "")
    if role in ("super_admin", "admin", "platform_admin"):
        return None  # No filtering - access all
    
    pool = get_db_pool(request)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT organization_id FROM user_organizations WHERE user_id = $1",
            current_user["id"]
        )
    return [r["organization_id"] for r in rows]
