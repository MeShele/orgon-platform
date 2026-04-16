"""API routes for user management (admin + profile)."""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional, List
import bcrypt
from datetime import datetime

from backend.services.user_service import UserService
from backend.rbac import require_roles
from backend.api.routes_auth import get_current_user_from_token

router = APIRouter(prefix="/api/users", tags=["users"])


# Dependency injection helper
def get_user_service(request: Request) -> UserService:
    """Get UserService from app state."""
    return request.app.state.user_service


class UserUpdate(BaseModel):
    """User update request."""
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str


class UserResponse(BaseModel):
    """User profile response."""
    id: int
    email: str
    name: Optional[str] = None
    role: str
    created_at: str


class SessionResponse(BaseModel):
    """Session response."""
    id: int
    user_id: int
    ip_address: str
    user_agent: str
    created_at: str
    last_active: str
    is_current: bool = False


def require_admin(current_user: dict = Depends(get_current_user_from_token)):
    """Dependency to require admin role - now uses RBAC."""
    import logging
    logger = logging.getLogger("orgon.api.users")
    logger.info(f"require_admin: user={current_user.get('email')}, role={current_user.get('role')}")
    
    from backend.rbac import LEGACY_ROLE_MAP
    effective_role = LEGACY_ROLE_MAP.get(current_user.get("role", ""), current_user.get("role", ""))
    if current_user.get("role") != "super_admin" and effective_role not in ("super_admin", "company_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("")
async def list_users(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_admin),
    service: UserService = Depends(get_user_service)
):
    """
    List all users (admin only).
    
    Query parameters:
    - limit: Maximum users to return (default: 50)
    - offset: Pagination offset (default: 0)
    
    Requires: Admin role
    """
    try:
        users = await service.list_users(limit=limit, offset=offset)
        
        return {
            "total": len(users),
            "users": users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Profile / Current User Endpoints (non-admin) ---
# NOTE: /me routes MUST be defined BEFORE /{user_id} to avoid route conflicts

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user_from_token),
    service: UserService = Depends(get_user_service)
):
    """
    Get current user profile (any authenticated user).
    """
    try:
        user = await service.get_user_by_id(current_user["id"])
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user["id"],
            email=user["email"],
            name=user.get("full_name"),
            role=user["role"],
            created_at=user["created_at"].isoformat() if isinstance(user["created_at"], datetime) else user["created_at"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@router.put("/me/password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user_from_token),
    service: UserService = Depends(get_user_service)
):
    """
    Change current user's password (any authenticated user).
    """
    try:
        user = await service.get_user_by_id(current_user["id"])
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Verify current password
        if not bcrypt.checkpw(request.current_password.encode("utf-8"), user["password_hash"].encode("utf-8")):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Validate new password
        if len(request.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
        
        # Hash new password
        new_hash = bcrypt.hashpw(request.new_password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")
        
        # Update password in database
        from backend.database.db import get_db_connection
        
        async with get_db_connection() as conn:
            await conn.execute(
                "UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2",
                new_hash,
                current_user["id"]
            )
        
        return {"message": "Password changed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")


@router.get("/me/sessions", response_model=List[SessionResponse])
async def get_user_sessions(current_user: dict = Depends(get_current_user_from_token)):
    """
    Get all active sessions for current user (any authenticated user).
    """
    from backend.database.db import get_db
    
    try:
        db = get_db()
        rows = db.fetchall(
            """
            SELECT id, user_id, ip_address, user_agent, created_at, last_active
            FROM user_sessions
            WHERE user_id = ?
            AND expires_at > datetime('now')
            ORDER BY last_active DESC
            """,
            (current_user["id"],)
        )
        
        sessions = []
        current_session_id = current_user.get("session_id")
        
        for row in rows:
            sessions.append(SessionResponse(
                id=row["id"],
                user_id=row["user_id"],
                ip_address=row.get("ip_address", ""),
                user_agent=row.get("user_agent", ""),
                created_at=str(row["created_at"]),
                last_active=str(row["last_active"]),
                is_current=(row["id"] == current_session_id)
            ))
        
        return sessions
    
    except Exception as e:
        # Graceful fallback if user_sessions table doesn't exist
        error_str = str(e)
        if "no such table" in error_str or "does not exist" in error_str:
            return []
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {error_str}")


@router.delete("/me/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Revoke a specific session (logout that device) for current user.
    """
    from backend.database.db import get_db_connection
    
    try:
        # Prevent revoking current session
        if session_id == current_user.get("session_id"):
            raise HTTPException(status_code=400, detail="Cannot revoke current session")
        
        async with get_db_connection() as conn:
            # Verify session belongs to user
            session = await conn.fetchrow(
                "SELECT id FROM user_sessions WHERE id = $1 AND user_id = $2",
                session_id,
                current_user["id"]
            )
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Revoke session by setting expires_at to now
            await conn.execute(
                "UPDATE user_sessions SET expires_at = NOW() WHERE id = $1",
                session_id
            )
        
        return {"message": "Session revoked successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to revoke session: {str(e)}")


# --- Admin CRUD Endpoints (parametric routes MUST be after /me) ---

@router.get("/{user_id}")
async def get_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    service: UserService = Depends(get_user_service)
):
    """Get user by ID (admin only)."""
    try:
        user = await service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: dict = Depends(require_admin),
    service: UserService = Depends(get_user_service)
):
    """Update user (admin only)."""
    try:
        updated_user = await service.update_user(
            user_id=user_id,
            full_name=data.full_name,
            role=data.role,
            is_active=data.is_active
        )
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "success": True,
            "message": "User updated successfully",
            "user": updated_user
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    service: UserService = Depends(get_user_service)
):
    """Delete user (admin only)."""
    try:
        if user_id == current_user["id"]:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        await service.update_user(user_id=user_id, is_active=False)
        return {
            "success": True,
            "message": "User deactivated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
