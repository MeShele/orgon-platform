"""
ORGON Core API Schemas (Pydantic Models)
Multi-tenancy support: Organizations, Users, Settings
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from uuid import UUID


# ============================================================================
# ENUMS
# ============================================================================

class LicenseType(str, Enum):
    """Organization license type."""
    free = "free"
    basic = "basic"
    pro = "pro"
    enterprise = "enterprise"


class OrganizationStatus(str, Enum):
    """Organization status."""
    active = "active"
    suspended = "suspended"
    cancelled = "cancelled"


class UserRole(str, Enum):
    """User role in organization."""
    admin = "admin"
    operator = "operator"
    viewer = "viewer"


# ============================================================================
# ORGANIZATION MODELS
# ============================================================================

class OrganizationBase(BaseModel):
    """Base organization fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$", description="URL-friendly slug")
    email: Optional[EmailStr] = Field(None, description="Contact email")
    phone: Optional[str] = Field(None, max_length=50, description="Contact phone")
    address: Optional[str] = Field(None, description="Physical address")
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Ensure slug is lowercase and valid."""
        if not v:
            raise ValueError('Slug cannot be empty')
        if not v.islower():
            raise ValueError('Slug must be lowercase')
        return v


class OrganizationCreate(OrganizationBase):
    """Create organization request."""
    license_type: LicenseType = Field(LicenseType.free, description="Initial license type")


class OrganizationUpdate(BaseModel):
    """Update organization request (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    license_type: Optional[LicenseType] = None
    status: Optional[OrganizationStatus] = None
    subscription_expires_at: Optional[datetime] = None


class OrganizationResponse(OrganizationBase):
    """Organization response."""
    id: UUID
    license_type: LicenseType
    status: OrganizationStatus
    subscription_expires_at: Optional[datetime]
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator("settings", mode="before")
    @classmethod
    def parse_settings(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {}
        return v if v is not None else {}
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class OrganizationList(BaseModel):
    """List of organizations with pagination."""
    total: int
    organizations: List[OrganizationResponse]


# ============================================================================
# USER-ORGANIZATION MODELS
# ============================================================================

class UserOrganizationBase(BaseModel):
    """Base user-organization fields."""
    user_id: int
    organization_id: UUID
    role: UserRole = Field(UserRole.viewer, description="User role in organization")


class UserOrganizationCreate(BaseModel):
    """Add user to organization request."""
    user_id: int
    role: UserRole = Field(UserRole.viewer, description="User role")


class UserOrganizationUpdate(BaseModel):
    """Update user role in organization."""
    role: UserRole


class UserOrganizationResponse(UserOrganizationBase):
    """User-organization relationship response."""
    created_at: datetime
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class OrganizationMember(BaseModel):
    """Organization member with user details."""
    user_id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: UserRole
    created_at: datetime


class OrganizationMembersList(BaseModel):
    """List of organization members."""
    total: int
    members: List[OrganizationMember]


# ============================================================================
# ORGANIZATION SETTINGS MODELS
# ============================================================================

class OrganizationSettingsBase(BaseModel):
    """Base organization settings fields."""
    billing_enabled: bool = True
    kyc_enabled: bool = False
    fiat_enabled: bool = False
    features: Dict[str, Any] = Field(default_factory=dict, description="Feature flags")
    limits: Dict[str, Any] = Field(default_factory=dict, description="Usage limits")
    branding: Dict[str, Any] = Field(default_factory=dict, description="White label branding")
    integrations: Dict[str, Any] = Field(default_factory=dict, description="External integrations")


class OrganizationSettingsUpdate(BaseModel):
    """Update organization settings (all fields optional)."""
    billing_enabled: Optional[bool] = None
    kyc_enabled: Optional[bool] = None
    fiat_enabled: Optional[bool] = None
    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None
    branding: Optional[Dict[str, Any]] = None
    integrations: Optional[Dict[str, Any]] = None


class OrganizationSettingsResponse(OrganizationSettingsBase):
    """Organization settings response."""
    organization_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# CONTEXT MODELS (for RLS)
# ============================================================================

class TenantContext(BaseModel):
    """Current tenant context (set via middleware)."""
    organization_id: UUID
    user_id: int
    is_super_admin: bool = False
    role: Optional[UserRole] = None


class OrganizationSwitchRequest(BaseModel):
    """Switch current organization request."""
    organization_id: UUID


# ============================================================================
# COMMON MODELS
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    limit: int = Field(50, ge=1, le=100, description="Max results per page")
    offset: int = Field(0, ge=0, description="Number of results to skip")


# ============================================================================
# EXAMPLES (for OpenAPI docs)
# ============================================================================

ORGANIZATION_CREATE_EXAMPLE = {
    "name": "Safina Exchange KG",
    "slug": "safina-kg",
    "email": "admin@safina.kg",
    "phone": "+996 555 123456",
    "city": "Bishkek",
    "country": "Kyrgyzstan",
    "license_type": "enterprise"
}

ORGANIZATION_RESPONSE_EXAMPLE = {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Safina Exchange KG",
    "slug": "safina-kg",
    "email": "admin@safina.kg",
    "phone": "+996 555 123456",
    "address": None,
    "city": "Bishkek",
    "country": "Kyrgyzstan",
    "license_type": "enterprise",
    "status": "active",
    "subscription_expires_at": "2027-02-10T00:00:00Z",
    "settings": {},
    "created_at": "2026-02-10T12:00:00Z",
    "updated_at": "2026-02-10T12:00:00Z",
    "created_by": "user-001"
}

ORGANIZATION_SETTINGS_EXAMPLE = {
    "organization_id": "123e4567-e89b-12d3-a456-426614174000",
    "billing_enabled": True,
    "kyc_enabled": True,
    "fiat_enabled": True,
    "features": {
        "auto_withdrawal": True,
        "2fa_required": True,
        "ip_whitelist": ["1.2.3.4"]
    },
    "limits": {
        "daily_withdrawal_usdt": 100000,
        "monthly_transactions": 10000,
        "max_wallets": 100
    },
    "branding": {
        "logo_url": "https://safina.kg/logo.png",
        "primary_color": "#1E40AF",
        "company_name": "Safina Exchange"
    },
    "integrations": {
        "safina_api_key": "sk_...",
        "webhook_url": "https://api.safina.kg/webhooks/orgon"
    },
    "created_at": "2026-02-10T12:00:00Z",
    "updated_at": "2026-02-10T12:00:00Z"
}
