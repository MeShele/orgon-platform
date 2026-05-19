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


# ---------------------------------------------------------------------
# Merchant CRUD — super_admin / platform_admin only.
# ---------------------------------------------------------------------

class MerchantSummary(BaseModel):
    id: str
    name: str
    slug: str
    merchant_kind: Optional[str]
    pricing_plan: Optional[str]
    sandbox: bool
    status: str
    webhook_url: Optional[str]
    api_keys_active: int
    end_users_count: int
    created_at: str
    # 'manual' for /api/admin/merchants (UI), 'api' for /platform/merchants.
    # Defaults to 'manual' for legacy rows (per migration 053 default).
    provisioning_source: str = "manual"


class CreateMerchantBody(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=60, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    merchant_kind: str = Field(..., pattern=r"^(exchanger|bank|exchange|internal)$")
    pricing_plan: str = Field(default="sandbox", pattern=r"^(sandbox|starter|growth|enterprise)$")
    sandbox: bool = False
    webhook_url: Optional[str] = Field(default=None, max_length=500)


class UpdateMerchantBody(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    merchant_kind: Optional[str] = Field(default=None, pattern=r"^(exchanger|bank|exchange|internal)$")
    pricing_plan: Optional[str] = Field(default=None, pattern=r"^(sandbox|starter|growth|enterprise)$")
    sandbox: Optional[bool] = None
    webhook_url: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = Field(default=None, pattern=r"^(active|suspended)$")


def _ensure_platform(user: dict) -> None:
    role = user.get("role")
    if role not in ("super_admin", "platform_admin"):
        raise HTTPException(status_code=403, detail="Only platform admins can manage merchants")


@router.get("", response_model=list[MerchantSummary])
async def list_merchants(
    http_request: Request,
    user: dict = Depends(require_roles("super_admin", "platform_admin", "admin")),
) -> list[MerchantSummary]:
    """Super-admin list of every merchant in the platform.

    Includes counts (api_keys_active / end_users) so the dashboard
    can show at a glance which tenants are onboarded vs dormant.
    """
    _ensure_platform(user)
    pool = get_db_pool(http_request)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT o.id::text, o.name, o.slug, o.merchant_kind, o.pricing_plan,
                   o.sandbox, o.status, o.webhook_url, o.created_at,
                   COALESCE(o.provisioning_source, 'manual') AS provisioning_source,
                   (SELECT count(*) FROM merchant_api_keys k
                     WHERE k.merchant_id = o.id AND k.revoked_at IS NULL) AS api_keys_active,
                   (SELECT count(*) FROM end_users u WHERE u.merchant_id = o.id) AS end_users_count
              FROM organizations o
             ORDER BY o.created_at DESC
            """
        )
    return [
        MerchantSummary(
            id=r["id"],
            name=r["name"],
            slug=r["slug"],
            merchant_kind=r["merchant_kind"],
            pricing_plan=r["pricing_plan"],
            sandbox=r["sandbox"],
            status=r["status"],
            webhook_url=r["webhook_url"],
            api_keys_active=int(r["api_keys_active"]),
            end_users_count=int(r["end_users_count"]),
            created_at=r["created_at"].isoformat(),
            provisioning_source=r["provisioning_source"],
        )
        for r in rows
    ]


@router.post("", response_model=MerchantSummary, status_code=201)
async def create_merchant(
    body: CreateMerchantBody,
    http_request: Request,
    user: dict = Depends(require_roles("super_admin", "platform_admin", "admin")),
) -> MerchantSummary:
    """Onboard a new merchant tenant.

    Creates an `organizations` row with merchant fields populated.
    Note: this does NOT generate API keys — admin issues them from
    the merchant's settings page after creation. Slug must be unique
    across the platform.
    """
    _ensure_platform(user)
    pool = get_db_pool(http_request)
    # Every merchant MUST have its own Safina EC private key — otherwise
    # /v1/wallets falls back to the global env signer and tenants share
    # one Safina-side identity (silent tenancy leak). Generate a fresh
    # SECP256k1 key right here so the merchant is correctly isolated
    # from the moment they're created. Stored encrypted-at-rest by the
    # pgcrypto envelope wrapping the column (see signer backend docs).
    import secrets as _secrets
    safina_ec = "0x" + _secrets.token_hex(32)
    async with pool.acquire() as conn:
        # Slug uniqueness check (clearer error than ON CONFLICT)
        dup = await conn.fetchrow("SELECT 1 FROM organizations WHERE slug = $1", body.slug)
        if dup:
            raise HTTPException(status_code=409, detail=f"Slug '{body.slug}' already taken")
        row = await conn.fetchrow(
            """
            INSERT INTO organizations
              (name, slug, merchant_kind, pricing_plan, sandbox, webhook_url,
               safina_ec_private_key,
               license_type, status, created_by, provisioning_source)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'free', 'active', $8, 'manual')
            RETURNING id::text, name, slug, merchant_kind, pricing_plan, sandbox,
                      status, webhook_url, created_at, provisioning_source
            """,
            body.name,
            body.slug,
            body.merchant_kind,
            body.pricing_plan,
            body.sandbox,
            body.webhook_url,
            safina_ec,
            user.get("id") if isinstance(user.get("id"), int) else None,
        )
    return MerchantSummary(
        id=row["id"],
        name=row["name"],
        slug=row["slug"],
        merchant_kind=row["merchant_kind"],
        pricing_plan=row["pricing_plan"],
        sandbox=row["sandbox"],
        status=row["status"],
        webhook_url=row["webhook_url"],
        api_keys_active=0,
        end_users_count=0,
        created_at=row["created_at"].isoformat(),
        provisioning_source=row["provisioning_source"],
    )


@router.get("/{merchant_id}", response_model=MerchantSummary)
async def get_merchant(
    merchant_id: str,
    http_request: Request,
    user: dict = Depends(require_roles("super_admin", "platform_admin", "admin")),
) -> MerchantSummary:
    _ensure_platform(user)
    pool = get_db_pool(http_request)
    try:
        UUID(merchant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="merchant_id must be uuid")
    async with pool.acquire() as conn:
        r = await conn.fetchrow(
            """
            SELECT o.id::text, o.name, o.slug, o.merchant_kind, o.pricing_plan,
                   o.sandbox, o.status, o.webhook_url, o.created_at,
                   COALESCE(o.provisioning_source, 'manual') AS provisioning_source,
                   (SELECT count(*) FROM merchant_api_keys k
                     WHERE k.merchant_id = o.id AND k.revoked_at IS NULL) AS api_keys_active,
                   (SELECT count(*) FROM end_users u WHERE u.merchant_id = o.id) AS end_users_count
              FROM organizations o
             WHERE o.id = $1
            """,
            UUID(merchant_id),
        )
    if not r:
        raise HTTPException(status_code=404, detail="merchant not found")
    return MerchantSummary(
        id=r["id"],
        name=r["name"],
        slug=r["slug"],
        merchant_kind=r["merchant_kind"],
        pricing_plan=r["pricing_plan"],
        sandbox=r["sandbox"],
        status=r["status"],
        webhook_url=r["webhook_url"],
        api_keys_active=int(r["api_keys_active"]),
        end_users_count=int(r["end_users_count"]),
        created_at=r["created_at"].isoformat(),
        provisioning_source=r["provisioning_source"],
    )


@router.patch("/{merchant_id}", response_model=MerchantSummary)
async def update_merchant(
    merchant_id: str,
    body: UpdateMerchantBody,
    http_request: Request,
    user: dict = Depends(require_roles("super_admin", "platform_admin", "admin")),
) -> MerchantSummary:
    _ensure_platform(user)
    try:
        UUID(merchant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="merchant_id must be uuid")
    sets: list[str] = []
    args: list = [UUID(merchant_id)]
    fields = {
        "name": body.name,
        "merchant_kind": body.merchant_kind,
        "pricing_plan": body.pricing_plan,
        "sandbox": body.sandbox,
        "webhook_url": body.webhook_url,
        "status": body.status,
    }
    for col, val in fields.items():
        if val is not None:
            sets.append(f"{col} = ${len(args) + 1}")
            args.append(val)
    if not sets:
        return await get_merchant(merchant_id, http_request, user)
    sets.append("updated_at = now()")
    pool = get_db_pool(http_request)
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE organizations SET {', '.join(sets)} WHERE id = $1",
            *args,
        )
    return await get_merchant(merchant_id, http_request, user)


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


@router.get("/{merchant_id}/usage")
async def get_merchant_usage(
    merchant_id: str,
    http_request: Request,
    days: int = 30,
    user: dict = Depends(require_roles("company_admin", "company_auditor", "super_admin", "platform_admin", "admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Today's counters + N-day history + plan limits, admin-side.

    Same shape as /v1/usage so the dashboard can render the merchant
    panel from either endpoint.
    """
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    from backend.services import merchant_billing as billing
    pool = get_db_pool(http_request)
    async with pool.acquire() as conn:
        org = await conn.fetchrow(
            "SELECT pricing_plan, sandbox FROM organizations WHERE id = $1::uuid",
            merchant_id,
        )
    plan = (org["pricing_plan"] if org else None) or "sandbox"
    today = await billing.today_counters(pool, merchant_id)
    hist = await billing.history(pool, merchant_id=merchant_id, days=days)
    return {
        "plan": plan,
        "sandbox": bool(org["sandbox"]) if org else False,
        "limits": billing.limits_for(plan),
        "today": today,
        "history": hist,
    }


@router.get("/{merchant_id}/deposits/lookup")
async def lookup_merchant_deposit(
    merchant_id: str,
    http_request: Request,
    tx_hash: str,
    include_offchain: bool = False,
    user: dict = Depends(require_roles("company_admin", "company_auditor", "super_admin", "platform_admin", "admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Find deposits by tx_hash within this merchant's wallets.

    Same shape as `/v1/deposits/lookup` so the admin UI and the
    external orchestrator render from one contract. Used by support
    operators when a user reports "I sent crypto, where is it" — we
    surface either the deposit row(s) or a structured hint about
    likely wrong-network transfers.
    """
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    try:
        UUID(merchant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="merchant_id must be uuid")
    from backend.services import merchant_deposit_lookup_service as dlookup
    pool = get_db_pool(http_request)
    rows = await dlookup.lookup_by_tx_hash(
        pool, merchant_id=merchant_id, tx_hash=tx_hash,
    )
    return dlookup.build_lookup_response(
        tx_hash=tx_hash, deposits=rows, include_offchain=include_offchain,
    )


@router.get("/{merchant_id}/treasury")
async def get_merchant_treasury_admin(
    merchant_id: str,
    http_request: Request,
    user: dict = Depends(require_roles("company_admin", "company_auditor", "super_admin", "platform_admin", "admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Treasury wallets snapshot (merchant-owned, excludes user_deposit).

    Same shape as `/v1/treasury` so the admin panel can render from
    either endpoint. Read-only — does not call Safina; reads the
    locally-cached `token_balances` populated by sync_balances.
    """
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    from backend.services import merchant_balance_service as bal
    pool = get_db_pool(http_request)
    return await bal.get_merchant_treasury(pool, merchant_id=merchant_id)


@router.get("/{merchant_id}/invoices")
async def get_merchant_invoices(
    merchant_id: str,
    http_request: Request,
    limit: int = 24,
    user: dict = Depends(require_roles("company_admin", "company_auditor", "super_admin", "platform_admin", "admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    _ensure_caller_can_admin(merchant_id, user, org_ids)
    from backend.services import invoice_service as inv
    pool = get_db_pool(http_request)
    items = await inv.list_invoices(pool, merchant_id=merchant_id, limit=limit)
    return {"invoices": items}


@router.post("/{merchant_id}/invoices/{invoice_id}/paid", status_code=200)
async def mark_invoice_paid(
    merchant_id: str,
    invoice_id: str,
    http_request: Request,
    user: dict = Depends(require_roles("super_admin", "platform_admin", "admin")),
    org_ids: list = Depends(get_user_org_ids),
):
    """Mark invoice as paid. Platform-side only (not merchant-self).

    We don't expose this on /v1/* because merchants shouldn't be able
    to flip their own invoice status — that's a back-office action.
    """
    _ensure_platform(user)
    from backend.services import invoice_service as inv
    pool = get_db_pool(http_request)
    row = await inv.mark_paid(pool, invoice_id=invoice_id)
    if not row:
        raise HTTPException(status_code=404, detail="invoice not found or already paid")
    if row["merchant_id"] != merchant_id:
        raise HTTPException(status_code=404, detail="invoice not found")
    return {"ok": True}


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
