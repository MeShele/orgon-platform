"""
Production RBAC (Role-Based Access Control) for ORGON.

Usage:
    from backend.rbac import require_roles

    @router.get("/something")
    async def endpoint(user: dict = Depends(require_roles("super_admin", "company_admin"))):
        ...
"""

from fastapi import HTTPException, Depends, status
from backend.dependencies import get_current_user

# Role hierarchy levels (higher = more access)
ROLE_HIERARCHY = {
    "super_admin": 100,
    "platform_admin": 80,
    "company_admin": 60,
    "company_operator": 40,
    "company_auditor": 30,
    "end_user": 10,
    # Legacy compatibility
    "admin": 60,
    "signer": 40,
    "viewer": 30,
}

# Map legacy roles to new roles for permission checks
LEGACY_ROLE_MAP = {
    "admin": "company_admin",
    "signer": "company_operator",
    "viewer": "company_auditor",
}

ALL_ROLES = list(ROLE_HIERARCHY.keys())


def _normalize_role(role: str) -> str:
    """Map legacy role names to new role names."""
    return LEGACY_ROLE_MAP.get(role, role)


def require_roles(*allowed_roles: str):
    """
    FastAPI dependency factory that checks user role.
    super_admin always has access.
    Legacy roles (admin/signer/viewer) are mapped to new roles.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user = Depends(require_roles("company_admin", "platform_admin"))):
            ...
    """
    # Expand allowed roles to include legacy equivalents
    expanded = set(allowed_roles)
    # Also allow legacy names that map to allowed roles
    for legacy, new in LEGACY_ROLE_MAP.items():
        if new in expanded:
            expanded.add(legacy)
        if legacy in expanded:
            expanded.add(new)
    # super_admin always allowed
    expanded.add("super_admin")

    async def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("role", "")
        if user_role not in expanded:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' not authorized for this endpoint. Required: {', '.join(sorted(allowed_roles))}"
            )
        return current_user

    return role_checker


def require_any_auth():
    """Require any authenticated user (all roles allowed)."""
    async def checker(current_user: dict = Depends(get_current_user)):
        return current_user
    return checker
