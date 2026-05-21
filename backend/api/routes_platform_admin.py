"""Platform-master-key routes (`/platform/*`).

These endpoints exist so asystem-core's control plane (or any future
trusted automation) can provision Orgon merchants WITHOUT a human
issuing keys via Telegram. Auth gate is the
`PlatformMasterAuthMiddleware` in `middleware_platform_master.py`.

Audit: every successful mutation writes an `audit_log` row with
`user_id=NULL` and `details.source='platform_api'` so reviewers see
machine-driven provisioning as a distinct class from human flows.

Idempotency note: callers should generate a stable `slug` per
asystem-core operator and use it consistently — `organizations.slug`
has a UNIQUE index, so a retried POST with the same slug returns 409
rather than creating a duplicate merchant. No explicit
`Idempotency-Key` header is needed; the slug IS the natural key.
"""

from __future__ import annotations

import json
import logging
import secrets
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.dependencies import get_db_pool
from backend.services import merchant_api_keys as keysvc

logger = logging.getLogger("orgon.api.platform_admin")

router = APIRouter(prefix="/platform", tags=["platform-admin"])


# ---------------------------------------------------------------------
# POST /platform/merchants — create merchant + first API key in one trip
# ---------------------------------------------------------------------

class ProvisionMerchantBody(BaseModel):
    """Same field set as `CreateMerchantBody` in `routes_merchant_admin`,
    minus things only relevant to a UI flow (webhook_url comes via
    `PUT /v1/webhooks/config` later in the integration handshake)."""

    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(
        ...,
        min_length=2,
        max_length=60,
        pattern=r"^[a-z0-9][a-z0-9\-]*$",
        description="Stable URL-safe identifier. Use a value tied to your tenant ID — "
        "this is the idempotency key for retries.",
    )
    merchant_kind: str = Field(
        default="exchanger",
        pattern=r"^(exchanger|bank|exchange|internal)$",
    )
    pricing_plan: str = Field(
        default="sandbox",
        pattern=r"^(sandbox|starter|growth|enterprise)$",
    )
    sandbox: bool = Field(
        default=True,
        description="If true, the issued key pair has `okt_*`/`okst_*` prefix and is "
        "restricted to testnet networks (5010, 3040, etc.).",
    )
    label: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Free-text label attached to the issued API key (visible in admin UI).",
    )


class ProvisionedKey(BaseModel):
    """Returned ONCE — `secret_once` is plaintext, never recoverable later.

    Caller MUST persist `secret_once` in their own vault immediately.
    """

    id: str
    key_pub: str
    secret_once: str
    label: Optional[str]


class ProvisionedMerchant(BaseModel):
    id: str
    name: str
    slug: str
    merchant_kind: Optional[str]
    pricing_plan: Optional[str]
    sandbox: bool
    status: str
    provisioning_source: str
    created_at: str


class ProvisionMerchantResponse(BaseModel):
    merchant: ProvisionedMerchant
    api_key: ProvisionedKey


@router.post("/merchants", response_model=ProvisionMerchantResponse, status_code=201)
async def provision_merchant(
    body: ProvisionMerchantBody,
    http_request: Request,
) -> ProvisionMerchantResponse:
    """Provision a merchant + first API-key pair in a single trip.

    Retries with the same `slug` get a 409 with a clear "already
    taken" message — the caller should treat that as a successful
    earlier provisioning and look up the merchant via their own
    records.
    """
    pool = get_db_pool(http_request)

    async with pool.acquire() as conn:
        # Slug uniqueness pre-check for a clearer error than ON CONFLICT.
        dup = await conn.fetchrow(
            "SELECT id::text FROM organizations WHERE slug = $1",
            body.slug,
        )
        if dup is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Slug '{body.slug}' already taken (merchant_id={dup['id']})",
            )

        # Fresh per-merchant Safina EC private key — must NOT share with
        # other tenants. Mirrors `routes_merchant_admin.create_merchant`.
        safina_ec = "0x" + secrets.token_hex(32)

        row = await conn.fetchrow(
            """
            INSERT INTO organizations
                (name, slug, merchant_kind, pricing_plan, sandbox,
                 safina_ec_private_key,
                 license_type, status, provisioning_source)
            VALUES ($1, $2, $3, $4, $5, $6, 'free', 'active', 'api')
            RETURNING id::text, name, slug, merchant_kind, pricing_plan,
                      sandbox, status, provisioning_source, created_at
            """,
            body.name,
            body.slug,
            body.merchant_kind,
            body.pricing_plan,
            body.sandbox,
            safina_ec,
        )

    merchant_id = row["id"]

    # Issue the first key pair. Scopes default to ["read", "write"] —
    # the merchant can mint scoped sub-keys later via the regular admin
    # UI if they want narrower surfaces.
    try:
        issued = await keysvc.issue_key(
            pool,
            merchant_id=merchant_id,
            label=body.label or "platform-provisioned",
            scopes=["read", "write"],
            sandbox=body.sandbox,
            created_by=None,
        )
    except Exception as e:
        # If key issuance fails, we still have a half-onboarded merchant
        # with no keys. Log loudly — caller should retry the key issuance
        # via /api/admin/merchants/{id}/api-keys (JWT).
        logger.exception(
            "platform: merchant %s created but key issuance failed: %s",
            merchant_id, e,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Merchant {merchant_id} created but key issuance failed. "
            f"Retry via JWT admin: POST /api/admin/merchants/{merchant_id}/api-keys",
        )

    # Audit trail — separate write so a failure here doesn't roll back
    # the merchant. We deliberately log even when audit_log is misbehaving
    # (network blip, etc.) by demoting to a warning — never raise.
    try:
        async with pool.acquire() as conn:
            # TD-1 Phase A — tag the row with the new merchant's org id
            # so future merchant-facing audit endpoints can return
            # "your provisioning event" without cross-tenant exposure.
            await conn.execute(
                """
                INSERT INTO audit_log
                    (user_id, action, resource_type, resource_id, details, organization_id)
                VALUES (NULL, 'merchant_self_provisioned', 'organization', $1, $2, $3)
                """,
                merchant_id,
                json.dumps({
                    "source": "platform_api",
                    "slug": body.slug,
                    "name": body.name,
                    "sandbox": body.sandbox,
                    "merchant_kind": body.merchant_kind,
                    "pricing_plan": body.pricing_plan,
                    "key_pub": issued.key_pub,
                }),
                merchant_id,
            )
    except Exception as e:
        logger.warning(
            "platform: audit_log write failed for merchant %s: %s "
            "(merchant + key were created successfully)",
            merchant_id, e,
        )

    logger.info(
        "platform: provisioned merchant=%s slug=%s sandbox=%s key_pub=%s",
        merchant_id, body.slug, body.sandbox, issued.key_pub,
    )

    return ProvisionMerchantResponse(
        merchant=ProvisionedMerchant(
            id=row["id"],
            name=row["name"],
            slug=row["slug"],
            merchant_kind=row["merchant_kind"],
            pricing_plan=row["pricing_plan"],
            sandbox=row["sandbox"],
            status=row["status"],
            provisioning_source=row["provisioning_source"],
            created_at=row["created_at"].isoformat(),
        ),
        api_key=ProvisionedKey(
            id=issued.id,
            key_pub=issued.key_pub,
            secret_once=issued.secret_once,
            label=issued.label,
        ),
    )
