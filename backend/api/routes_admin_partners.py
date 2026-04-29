"""Admin REST for B2B partner provisioning.

The customer-facing partner endpoints live in `routes_partner*.py` and are
authenticated by API key. This module is the **admin** side: create new
partner accounts, rotate / revoke their credentials, and list everything
visible to the caller.

Auth: super_admin sees every partner; company_admin sees only partners
linked to their organization (via `partners.organization_id`, migration
017). Both go through the standard JWT middleware.

Routes:
  POST    /api/v1/admin/partners               create
  GET     /api/v1/admin/partners               list (scoped)
  GET     /api/v1/admin/partners/{id}          single
  POST    /api/v1/admin/partners/{id}/rotate   new api_key + secret
  POST    /api/v1/admin/partners/{id}/revoke   suspend (soft-delete)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from backend.dependencies import get_current_user
from backend.rbac import require_roles

logger = logging.getLogger("orgon.api.admin.partners")

router = APIRouter(prefix="/api/v1/admin/partners", tags=["Admin · Partners"])


# ────────────────────────────────────────────────────────────────────
# Schemas
# ────────────────────────────────────────────────────────────────────

class PartnerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    ec_address: str = Field(..., pattern=r"^0x[0-9a-fA-F]{40}$",
                            description="Ethereum-style 0x-prefixed 40-hex address")
    tier: str = Field("free", pattern=r"^(free|starter|business|enterprise)$")
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    organization_id: Optional[UUID] = Field(
        None, description="Bind partner to this org. Required for company_admin callers; super_admin can omit.",
    )


class PartnerCreated(BaseModel):
    """One-time response — secret is only ever returned here."""
    partner_id: str
    name: str
    tier: str
    ec_address: str
    api_key: str       # ⚠️ shown once
    api_secret: str    # ⚠️ shown once
    rate_limit_per_minute: int
    webhook_url: Optional[str]
    created_at: str


class PartnerSummary(BaseModel):
    partner_id: str
    name: str
    tier: str
    status: str
    ec_address: str
    organization_id: Optional[str]
    rate_limit_per_minute: int
    api_key_prefix: str  # first 8 chars only — never the full key after creation
    webhook_url: Optional[str]
    created_at: str
    updated_at: Optional[str]


class RotateResponse(BaseModel):
    partner_id: str
    api_key: str
    api_secret: str
    rotated_at: str


# ────────────────────────────────────────────────────────────────────
# Internals
# ────────────────────────────────────────────────────────────────────

def _get_partner_service(request: Request):
    svc = getattr(request.app.state, "partner_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="B2B partner service not initialised on this deployment",
        )
    return svc


async def _user_org_ids(request: Request, user: dict) -> Optional[list]:
    """Return organization IDs visible to `user`.
    super_admin → None (sees everything).
    Other roles → list of orgs they're a member of.
    """
    if user.get("role") == "super_admin":
        return None
    from backend.main import get_database
    db = get_database()
    if db is None:
        return []
    rows = await db.fetch(
        "SELECT organization_id FROM user_organizations WHERE user_id = $1",
        params=(user["id"],),
    )
    return [r["organization_id"] for r in rows]


def _to_summary(row: dict) -> PartnerSummary:
    return PartnerSummary(
        partner_id=str(row["id"]) if "id" in row else str(row.get("partner_id")),
        name=row["name"],
        tier=row["tier"],
        status=row["status"],
        ec_address=row["ec_address"],
        organization_id=str(row["organization_id"]) if row.get("organization_id") else None,
        rate_limit_per_minute=row.get("rate_limit_per_minute", 0),
        api_key_prefix=row.get("api_key", "")[:8] + "…" if row.get("api_key") else "",
        webhook_url=row.get("webhook_url"),
        created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        updated_at=(row["updated_at"].isoformat() if row.get("updated_at") and hasattr(row["updated_at"], "isoformat") else None),
    )


# ────────────────────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────────────────────

@router.post("", response_model=PartnerCreated, status_code=status.HTTP_201_CREATED)
async def create_partner(
    request: Request,
    payload: PartnerCreate,
    user: dict = Depends(require_roles("super_admin", "company_admin", "platform_admin")),
):
    """Provision a new B2B partner. The api_secret is shown **only here** —
    if the customer loses it they need a rotation."""
    svc = _get_partner_service(request)

    # Permission check on organization_id
    if user.get("role") != "super_admin":
        if payload.organization_id is None:
            raise HTTPException(
                status_code=400,
                detail="organization_id is required for non-super-admin callers",
            )
        org_ids = await _user_org_ids(request, user)
        if payload.organization_id not in (org_ids or []):
            raise HTTPException(
                status_code=403,
                detail="You can only create partners inside organizations you belong to",
            )

    try:
        result = await svc.create_partner(
            name=payload.name,
            ec_address=payload.ec_address,
            tier=payload.tier,
            webhook_url=payload.webhook_url,
            webhook_secret=payload.webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Bind organization_id (the service helper doesn't accept it directly).
    if payload.organization_id:
        from backend.main import get_database
        db = get_database()
        if db is not None:
            await db.execute(
                "UPDATE partners SET organization_id = $1 WHERE id = $2",
                (payload.organization_id, UUID(result["partner_id"])),
            )

    logger.info(
        "Partner %s provisioned by user %s (org=%s, tier=%s)",
        result["partner_id"], user.get("id"),
        payload.organization_id, payload.tier,
    )
    return PartnerCreated(**result)


@router.get("", response_model=list[PartnerSummary])
async def list_partners(
    request: Request,
    user: dict = Depends(require_roles("super_admin", "company_admin", "platform_admin")),
    status_filter: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Paginated partner list, scoped to caller's orgs (super_admin sees all)."""
    svc = _get_partner_service(request)
    rows = await svc.list_partners(status=status_filter, tier=tier, limit=limit, offset=offset)

    if user.get("role") != "super_admin":
        org_ids = await _user_org_ids(request, user)
        org_set = set(org_ids or [])
        rows = [r for r in rows if r.get("organization_id") in org_set]

    return [_to_summary(r) for r in rows]


@router.get("/{partner_id}", response_model=PartnerSummary)
async def get_partner(
    partner_id: UUID,
    request: Request,
    user: dict = Depends(require_roles("super_admin", "company_admin", "platform_admin")),
):
    svc = _get_partner_service(request)
    row = await svc.get_partner(str(partner_id))
    if not row:
        raise HTTPException(status_code=404, detail="Partner not found")

    if user.get("role") != "super_admin":
        org_ids = await _user_org_ids(request, user)
        if row.get("organization_id") not in (org_ids or []):
            # 404 instead of 403 — don't leak existence across tenants.
            raise HTTPException(status_code=404, detail="Partner not found")

    return _to_summary(row)


@router.post("/{partner_id}/rotate", response_model=RotateResponse)
async def rotate_partner_key(
    partner_id: UUID,
    request: Request,
    user: dict = Depends(require_roles("super_admin", "company_admin", "platform_admin")),
):
    """Generate a new api_key + api_secret pair and invalidate the old one.
    Use case: secret leaked / employee left."""
    svc = _get_partner_service(request)
    existing = await svc.get_partner(str(partner_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Partner not found")

    if user.get("role") != "super_admin":
        org_ids = await _user_org_ids(request, user)
        if existing.get("organization_id") not in (org_ids or []):
            raise HTTPException(status_code=404, detail="Partner not found")

    rotated = await svc.rotate_api_key(str(partner_id))
    logger.info("Partner %s api key rotated by user %s", partner_id, user.get("id"))
    return RotateResponse(
        partner_id=str(partner_id),
        api_key=rotated["api_key"],
        api_secret=rotated["api_secret"],
        rotated_at=rotated.get("rotated_at") or rotated.get("created_at") or "",
    )


@router.post("/{partner_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_partner(
    partner_id: UUID,
    request: Request,
    reason: Optional[str] = None,
    user: dict = Depends(require_roles("super_admin", "company_admin", "platform_admin")),
):
    """Suspend the partner (status=suspended). Doesn't delete history;
    audit log + signature_history rows stay for forensics."""
    svc = _get_partner_service(request)
    existing = await svc.get_partner(str(partner_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Partner not found")

    if user.get("role") != "super_admin":
        org_ids = await _user_org_ids(request, user)
        if existing.get("organization_id") not in (org_ids or []):
            raise HTTPException(status_code=404, detail="Partner not found")

    await svc.suspend_partner(str(partner_id), reason or "Revoked by admin")
    logger.info(
        "Partner %s suspended by user %s (reason=%s)",
        partner_id, user.get("id"), reason,
    )
    return None
