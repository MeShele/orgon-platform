"""Organization management API endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from backend.api.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    UserOrganizationCreate,
    UserOrganizationUpdate,
    UserOrganizationResponse,
    OrganizationSettingsUpdate,
    OrganizationSettingsResponse,
    TenantContext,
    OrganizationStatus,
    UserRole,
)
from backend.services.organization_service import OrganizationService
from backend.rbac import require_roles
from backend.dependencies import (
    get_organization_service,
    get_current_user,
    require_admin,
)

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


# ==================== Dependencies ====================

def get_org_service_dependency(request: Request) -> OrganizationService:
    """Dependency to get OrganizationService from app state."""
    return get_organization_service(request)


async def get_user_org_role(
    org_id: int,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
) -> UserRole:
    """Get user's role in organization."""
    role = await org_service.get_user_role(org_id, user["id"])
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization"
        )
    return role


async def require_org_admin(
    org_id: int,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Require user to be admin of the organization."""
    role = await get_user_org_role(org_id, user, org_service)
    if role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin access required"
        )
    return user


# ==================== Organization CRUD ====================

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    user: dict = Depends(require_roles("company_admin")),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """
    Create a new organization.
    Current user becomes admin of the organization.
    """
    org = await org_service.create_organization(data, creator_user_id=user["id"])
    return org


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    status_filter: OrganizationStatus | None = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """
    List organizations.
    For admins: all organizations.
    For users: only organizations they belong to.
    """
    # If user is global admin, show all; otherwise filter by membership
    user_id = None if user.get("role") in ("admin", "super_admin", "platform_admin") else user["id"]
    
    orgs = await org_service.list_organizations(
        user_id=user_id,
        status=status_filter,
        limit=limit,
        offset=offset
    )
    return orgs


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: int,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Get organization details by ID."""
    # Check if user has access to this organization
    if user.get("role") not in ("admin", "super_admin", "platform_admin"):
        role = await org_service.get_user_role(org_id, user["id"])
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    org = await org_service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: int,
    data: OrganizationUpdate,
    user: dict = Depends(require_org_admin),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Update organization details. Requires admin role."""
    org = await org_service.update_organization(org_id, data)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: int,
    user: dict = Depends(require_org_admin),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Delete organization (soft delete). Requires admin role."""
    success = await org_service.delete_organization(org_id)
    if not success:
        raise HTTPException(status_code=404, detail="Organization not found")


# ==================== Organization Members ====================

@router.get("/{org_id}/members", response_model=list[UserOrganizationResponse])
async def list_members(
    org_id: int,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """List organization members."""
    # Check access
    if user.get("role") not in ("admin", "super_admin", "platform_admin"):
        role = await org_service.get_user_role(org_id, user["id"])
        if not role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    members = await org_service.list_members(org_id, limit=limit, offset=offset)
    return members


@router.post("/{org_id}/members", response_model=UserOrganizationResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: int,
    data: UserOrganizationCreate,
    user: dict = Depends(require_org_admin),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Add user to organization. Requires admin role."""
    member = await org_service.add_member(org_id, data)
    return member


@router.put("/{org_id}/members/{user_id}", response_model=UserOrganizationResponse)
async def update_member_role(
    org_id: int,
    user_id: int,
    data: UserOrganizationUpdate,
    user: dict = Depends(require_org_admin),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Update member's role. Requires admin role."""
    member = await org_service.update_member_role(org_id, user_id, data)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return member


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: int,
    user_id: int,
    user: dict = Depends(require_org_admin),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Remove user from organization. Requires admin role."""
    success = await org_service.remove_member(org_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found")


# ==================== Organization Settings ====================

@router.get("/{org_id}/settings", response_model=OrganizationSettingsResponse)
async def get_settings(
    org_id: int,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Get organization settings."""
    # Check access
    if user.get("role") not in ("admin", "super_admin", "platform_admin"):
        role = await org_service.get_user_role(org_id, user["id"])
        if not role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    settings = await org_service.get_settings(org_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    return settings


@router.put("/{org_id}/settings", response_model=OrganizationSettingsResponse)
async def update_settings(
    org_id: int,
    data: OrganizationSettingsUpdate,
    user: dict = Depends(require_org_admin),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """Update organization settings. Requires admin role."""
    settings = await org_service.update_settings(org_id, data)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    return settings


# ==================== Tenant Context ====================

@router.post("/tenant/switch", status_code=status.HTTP_204_NO_CONTENT)
async def switch_organization(
    data: TenantContext,
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """
    Switch current organization context.
    Sets RLS context for multi-tenancy.
    """
    # Verify user has access to this organization
    role = await org_service.get_user_role(data.organization_id, user["id"])
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    await org_service.set_tenant_context(data.organization_id)


@router.get("/tenant/current", response_model=OrganizationResponse | None)
async def get_current_organization(
    user: dict = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service_dependency)
):
    """
    Get current organization from session context.
    TODO: Store current_org_id in session/JWT for retrieval.
    For now, returns first organization user belongs to.
    """
    orgs = await org_service.list_organizations(user_id=user["id"], limit=1)
    if orgs:
        return orgs[0]
    return None
