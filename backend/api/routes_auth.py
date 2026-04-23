"""
Authentication API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()


# ==================== Request/Response Models ====================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "viewer"  # Default role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str


from datetime import datetime as DateTime

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: Optional[DateTime] = None
    created_at: DateTime
    
    class Config:
        from_attributes = True  # Pydantic v2: allow ORM mode


class LoginResponse(BaseModel):
    user: Optional[UserResponse] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    # 2FA fields
    requires_2fa: Optional[bool] = None
    temp_token: Optional[str] = None
    user_id: Optional[int] = None


class Verify2FARequest(BaseModel):
    temp_token: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


# ==================== Dependencies ====================

def get_auth_service_dependency(request: Request) -> AuthService:
    """Dependency to get AuthService instance from main app."""
    from backend.dependencies import get_auth_service
    return get_auth_service(request)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Dependency to get current authenticated user from JWT token.
    Raises 401 if token invalid/expired.
    """
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    
    if not payload or payload.get('type') != 'access':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = int(payload['sub'])
    user = await auth_service.get_user_by_id(user_id)
    
    if not user or not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


async def require_role(required_role: str):
    """
    Dependency factory to require specific role.
    Usage: Depends(require_role("admin"))
    """
    async def check_role(user: dict = Depends(get_current_user)):
        role_hierarchy = {
            "end_user": 0, "viewer": 0,
            "company_auditor": 1,
            "company_operator": 2, "signer": 2,
            "company_admin": 3, "admin": 3,
            "platform_admin": 4,
            "super_admin": 5
        }
        user_level = role_hierarchy.get(user['role'], 0)
        required_level = role_hierarchy.get(required_role, 2)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return user
    
    return check_role


async def require_admin(user: dict = Depends(get_current_user)):
    """Dependency to require admin role."""
    if user['role'] not in ('admin', 'super_admin', 'platform_admin', 'company_admin'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


# Backward compatibility alias
get_current_user_from_token = get_current_user


# ==================== Helper Functions ====================

def get_client_info(request: Request) -> tuple:
    """Extract IP address and User-Agent from request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


# ==================== Routes ====================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service_dependency),
    # current_user: dict = Depends(require_admin)  # Uncomment to restrict registration to admins
):
    """
    Register new user.
    
    Note: Currently open for self-registration. 
    Uncomment the require_admin dependency to restrict to admin-only.
    """
    # Validate role
    if data.role not in ["super_admin", "platform_admin", "company_admin", "company_operator", "company_auditor", "end_user", "admin", "signer", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be one of: super_admin, platform_admin, company_admin, company_operator, company_auditor, end_user"
        )
    
    # Password validation
    if len(data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    user = await auth_service.create_user(
        email=data.email,
        password=data.password,
        full_name=data.full_name,
        role=data.role
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    
    return UserResponse(**user)


@router.post("/login", response_model=LoginResponse)
async def login(
    data: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Login with email and password.
    Returns access token (15 min) and refresh token (7 days).
    """
    import logging
    import traceback
    import sys
    logger = logging.getLogger("orgon.api.auth")
    
    try:
        print(f"[LOGIN] Attempt: {data.email}", file=sys.stderr, flush=True)
        logger.info(f"Login attempt: {data.email}")
        
        ip_address, user_agent = get_client_info(request)
        print(f"[LOGIN] Client: ip={ip_address}, ua={user_agent}", file=sys.stderr, flush=True)
        logger.info(f"Client info: ip={ip_address}, ua={user_agent}")
        
        print(f"[LOGIN] Calling auth_service.login...", file=sys.stderr, flush=True)
        logger.info("Calling auth_service.login...")
        
        result = await auth_service.login(
            email=data.email,
            password=data.password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        print(f"[LOGIN] Result: {result is not None}", file=sys.stderr, flush=True)
        logger.info(f"Login result: {result is not None}")
        
        if not result:
            print(f"[LOGIN] FAILED for {data.email}", file=sys.stderr, flush=True)
            logger.warning(f"Login failed for {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        print(f"[LOGIN] SUCCESS for {data.email}", file=sys.stderr, flush=True)
        logger.info(f"Login successful for {data.email}")
        return LoginResponse(**result)
    except HTTPException:
        print(f"[LOGIN] HTTPException caught", file=sys.stderr, flush=True)
        raise
    except Exception as e:
        print(f"[LOGIN] EXCEPTION: {e}", file=sys.stderr, flush=True)
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        logger.error(f"Login exception: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/verify-2fa", response_model=LoginResponse)
async def verify_2fa(
    data: Verify2FARequest,
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Verify 2FA code and complete login.
    Called after login returns requires_2fa: true.
    """
    result = await auth_service.verify_2fa_login(
        temp_token=data.temp_token,
        code=data.code
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code"
        )
    
    return LoginResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Refresh access token using refresh token.
    Returns new access token and refresh token.
    """
    result = await auth_service.refresh_tokens(data.refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    return TokenResponse(**result)


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Logout by revoking refresh token session.
    """
    success = await auth_service.logout(data.refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {"status": "ok"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user info.
    """
    return UserResponse(**current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Change password for current user.
    Requires old password verification.
    """
    # Verify old password
    user_with_hash = await auth_service.get_user_by_email(current_user['email'])
    if not auth_service.verify_password(data.old_password, user_with_hash['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect current password"
        )
    
    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    
    # Change password
    success = await auth_service.change_password(current_user['id'], data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )
    
    # Revoke all sessions (force re-login)
    await auth_service.revoke_user_sessions(current_user['id'])
    
    return None


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def request_password_reset(
    data: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Request password reset token.
    Token is valid for 1 hour.
    
    Note: In production, send this token via email.
    For now, it's returned in the response (dev only).
    """
    token = await auth_service.create_password_reset_token(data.email)
    
    # In production, send email here instead of returning token
    # For development, we'll return it (remove this in production!)
    if not token:
        # Don't reveal if email exists (security best practice)
        return None
    
    # TODO: Send email with reset link
    # For now, log the token (dev only!)
    print(f"[DEV] Password reset token for {data.email}: {token}")
    print(f"[DEV] Reset URL: http://localhost:3000/reset-password?token={token}")
    
    return None


@router.post("/reset-password/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    data: ResetPasswordConfirm,
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Confirm password reset with token.
    """
    # Validate new password
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters"
        )
    
    success = await auth_service.use_password_reset_token(data.token, data.new_password)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return None


# ==================== Admin Routes ====================

@router.get("/users", response_model=dict)
async def list_users(
    limit: int = 50,
    offset: int = 0,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    List all users (admin only).
    Supports pagination and filtering.
    """
    users, total = await auth_service.list_users(
        limit=limit,
        offset=offset,
        role=role,
        is_active=is_active
    )
    
    return {
        "users": users,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Get user by ID (admin only).
    """
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service_dependency)
):
    """
    Update user details (admin only).
    """
    if role and role not in ["super_admin", "platform_admin", "company_admin", "company_operator", "company_auditor", "end_user", "admin", "signer", "viewer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    user = await auth_service.update_user(
        user_id=user_id,
        full_name=full_name,
        role=role,
        is_active=is_active
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user)


@router.get("/roles", response_model=dict)
async def get_roles(
    current_user: dict = Depends(get_current_user)
):
    """
    Get available roles and their permissions.
    """
    from backend.services.auth_service import ROLES
    
    return {
        "roles": {
            role: {
                "name": role,
                "permissions": perms
            }
            for role, perms in ROLES.items()
        }
    }
