"""Admin endpoints for managing a merchant's API keys.

These endpoints are scoped to the ORGON-side dashboard. They are NOT
the public /v1/* surface — those will come in a later step and will
authenticate via HMAC signed requests using the keys issued here.

Authorization:
* `company_admin` of the target merchant can issue/list/revoke their
  own keys.
* `super_admin` can do the same for any merchant.

The full secret is returned exactly once at issuance (in the POST
response) — never persisted, never recoverable. Frontend must render
a one-time-reveal modal.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.dependencies import get_db_pool, get_user_org_ids
from backend.rbac import require_roles
from backend.services import merchant_api_keys as keysvc

router = APIRouter(prefix="/api/admin/merchants", tags=["merchant-admin"])


class IssueKeyRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=80)
    scopes: list[str] = Field(default_factory=list)
    sandbox: bool = False


class IssuedKeyResponse(BaseModel):
    id: str
    key_pub: str
    secret_once: str
    scopes: list[str]
    label: Optional[str]
    warning: str = (
        "Сохраните secret сейчас — мы его не показываем повторно. "
        "Если потеряете, отзовите этот ключ и выпустите новый."
    )


class KeyRow(BaseModel):
    id: str
    key_pub: str
    label: Optional[str]
    scopes: list[str]
    last_used_at: Optional[str]
    expires_at: Optional[str]
    revoked_at: Optional[str]
    created_at: str


def _ensure_caller_can_admin(merchant_id: str, user: dict, org_ids: list) -> None:
    """Either super_admin, or the merchant's own admin."""
    if user.get("role") == "super_admin":
        return
    if not org_ids or merchant_id not in [str(o) for o in org_ids]:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/{merchant_id}/api-keys", response_model=IssuedKeyResponse, status_code=201)
async def issue_api_key(
    merchant_id: str,
    body: IssueKeyRequest,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin", "super_admin", "platform_admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    try:
        UUID(merchant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="merchant_id must be uuid")

    pool = get_db_pool(http_request)
    issued = await keysvc.issue_key(
        pool,
        merchant_id=merchant_id,
        label=body.label,
        scopes=body.scopes,
        sandbox=body.sandbox,
        created_by=user.get("id") if isinstance(user.get("id"), int) else None,
    )
    return IssuedKeyResponse(
        id=issued.id,
        key_pub=issued.key_pub,
        secret_once=issued.secret_once,
        scopes=issued.scopes,
        label=issued.label,
    )


@router.get("/{merchant_id}/api-keys", response_model=list[KeyRow])
async def list_api_keys(
    merchant_id: str,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin", "company_auditor", "super_admin", "platform_admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    pool = get_db_pool(http_request)
    rows = await keysvc.list_keys(pool, merchant_id=merchant_id)
    return [
        KeyRow(
            id=r["id"],
            key_pub=r["key_pub"],
            label=r.get("label"),
            scopes=list(r.get("scopes") or []),
            last_used_at=r["last_used_at"].isoformat() if r.get("last_used_at") else None,
            expires_at=r["expires_at"].isoformat() if r.get("expires_at") else None,
            revoked_at=r["revoked_at"].isoformat() if r.get("revoked_at") else None,
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post("/{merchant_id}/api-keys/{key_id}/revoke", status_code=200)
async def revoke_api_key(
    merchant_id: str,
    key_id: str,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin", "super_admin", "platform_admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    pool = get_db_pool(http_request)
    ok = await keysvc.revoke_key(pool, merchant_id=merchant_id, key_id=key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found or already revoked")
    return {"ok": True}
