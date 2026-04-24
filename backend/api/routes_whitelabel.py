"""White Label API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from typing import Optional
from uuid import UUID
from backend.services.whitelabel_service import WhiteLabelService
from backend.dependencies import get_current_user, get_db_pool
from backend.rbac import require_roles

router = APIRouter(prefix="/api/v1/whitelabel", tags=["White Label"])

async def get_whitelabel_service(pool = Depends(get_db_pool)) -> WhiteLabelService:
    return WhiteLabelService(pool)

# ==================== Branding ====================

@router.get("/branding")
async def get_branding(
    org_id: UUID = Query(None),
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Get organization branding."""
    branding = await service.get_branding(org_id)
    if not branding:
        # Return defaults if no branding set
        return {
            "organization_id": str(org_id),
            "color_primary": "#3B82F6",
            "color_secondary": "#10B981",
            "color_accent": "#F59E0B",
            "platform_name": "ORGON"
        }
    return branding

@router.put("/branding")
async def update_branding(
    org_id: UUID, logo_url: Optional[str] = None, color_primary: Optional[str] = None,
    color_secondary: Optional[str] = None, platform_name: Optional[str] = None,
    tagline: Optional[str] = None, support_email: Optional[str] = None,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Update organization branding."""
    branding_data = {k: v for k, v in {
        'logo_url': logo_url,
        'color_primary': color_primary,
        'color_secondary': color_secondary,
        'platform_name': platform_name,
        'tagline': tagline,
        'support_email': support_email
    }.items() if v is not None}
    
    branding = await service.create_or_update_branding(org_id, branding_data)
    return branding

# ==================== Email Templates ====================

@router.get("/email-templates")
async def list_email_templates(
    org_id: UUID = Query(None),
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """List email templates."""
    templates = await service.list_email_templates(org_id)
    return templates

@router.get("/email-templates/{template_type}")
async def get_email_template(
    template_type: str, org_id: UUID = Query(None),
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Get email template by type."""
    template = await service.get_email_template(org_id, template_type)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/email-templates/{template_type}")
async def update_email_template(
    template_type: str, org_id: UUID, subject: str, body_html: str,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Update email template."""
    template = await service.create_or_update_email_template(
        org_id, template_type, subject, body_html, UUID(str(user['id']))
    )
    return template

# ==================== Custom Domains ====================

@router.post("/domains", status_code=status.HTTP_201_CREATED)
async def create_custom_domain(
    org_id: UUID, domain: str,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Create custom domain verification."""
    domain_record = await service.create_custom_domain(org_id, domain)
    return domain_record

@router.get("/domains")
async def list_custom_domains(
    org_id: UUID = Query(None),
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """List custom domains."""
    domains = await service.get_custom_domains(org_id)
    return domains

@router.post("/domains/{domain_id}/verify")
async def verify_domain(
    domain_id: UUID,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Verify custom domain (after DNS check)."""
    domain = await service.verify_custom_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain

# ==================== Upload Assets ====================

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_asset(
    org_id: UUID, asset_type: str,
    file: UploadFile = File(...),
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """Upload asset (logo/favicon).
    
    Note: This is a placeholder. In production, upload to CloudFlare R2/S3 first,
    then call this endpoint with the storage_url.
    """
    # TODO: Implement actual file upload to R2/S3
    # For now, return mock response
    storage_url = f"https://cdn.orgon.ai/{org_id}/{file.filename}"
    
    asset = await service.create_upload_asset(
        org_id, file.filename, file.content_type or 'application/octet-stream',
        storage_url, asset_type, UUID(str(user['id']))
    )
    return asset

@router.get("/assets")
async def list_assets(
    org_id: UUID = Query(None),
    asset_type: Optional[str] = None,
    user: dict = Depends(require_roles("company_admin", "platform_admin")),
    service: WhiteLabelService = Depends(get_whitelabel_service)
):
    """List uploaded assets."""
    assets = await service.get_assets(org_id, asset_type)
    return assets
