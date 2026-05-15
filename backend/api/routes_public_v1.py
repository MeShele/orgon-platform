"""Public /v1/* API — merchant-facing endpoints.

All routes here are guarded by `MerchantHMACAuthMiddleware`. On
authenticated requests, the middleware writes:

    request.state.merchant_id          : str (uuid)
    request.state.merchant_api_key_id  : str
    request.state.merchant_scopes      : list[str]

Subsequent endpoints scope DB queries by `merchant_id` — never trust
client-supplied tenant ids.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field

from backend.dependencies import get_db_pool
from backend.services import end_user_service as users
from backend.services import merchant_wallet_service as wallets

router = APIRouter(prefix="/v1", tags=["public-v1"])


# ---------------------------------------------------------------------
# Health & meta
# ---------------------------------------------------------------------

@router.get("/health")
async def public_health() -> dict:
    """Liveness probe. Unauthenticated by middleware exempt list."""
    return {"status": "ok", "service": "orgon-public-v1"}


@router.get("/ping")
async def public_ping(request: Request) -> dict:
    """Authenticated ping. Echoes back caller identity so an integrator
    can verify HMAC signing end-to-end before wiring real flows."""
    return {
        "ok": True,
        "merchant_id": getattr(request.state, "merchant_id", None),
        "scopes": getattr(request.state, "merchant_scopes", []),
        "api_key_id": getattr(request.state, "merchant_api_key_id", None),
    }


# ---------------------------------------------------------------------
# End-users
# ---------------------------------------------------------------------

class UserUpsertBody(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=200)
    kyc_status: Optional[str] = Field(default=None, max_length=40)
    metadata: Optional[dict] = None


class UserPatchBody(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3, max_length=200)
    kyc_status: Optional[str] = Field(default=None, max_length=40)
    metadata: Optional[dict] = None


def _merchant_id_of(request: Request) -> str:
    mid = getattr(request.state, "merchant_id", None)
    if not mid:
        # Should never happen — middleware would have rejected — but
        # belt-and-suspenders.
        raise HTTPException(status_code=401, detail="No merchant context")
    return mid


@router.post("/users", status_code=201)
async def upsert_user(body: UserUpsertBody, request: Request) -> dict:
    """Idempotent on (merchant_id, external_id).

    Sending the same external_id twice updates email/kyc_status/metadata
    rather than erroring out. This makes it safe for the merchant's
    onboarding code to call us on every login if they want.
    """
    pool = get_db_pool(request)
    row = await users.create_user(
        pool,
        merchant_id=_merchant_id_of(request),
        external_id=body.external_id,
        email=body.email,
        kyc_status=body.kyc_status,
        metadata=body.metadata,
    )
    return _user_to_public(row)


@router.get("/users/{user_id}")
async def get_user_endpoint(user_id: str, request: Request) -> dict:
    pool = get_db_pool(request)
    row = await users.get_user(
        pool, merchant_id=_merchant_id_of(request), user_id=user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_to_public(row)


@router.get("/users")
async def list_users_endpoint(
    request: Request,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    pool = get_db_pool(request)
    page = await users.list_users(
        pool,
        merchant_id=_merchant_id_of(request),
        limit=limit,
        cursor=cursor,
    )
    return {
        "users": [_user_to_public(u) for u in page["users"]],
        "next_cursor": page["next_cursor"],
    }


@router.patch("/users/{user_id}")
async def patch_user(user_id: str, body: UserPatchBody, request: Request) -> dict:
    pool = get_db_pool(request)
    row = await users.update_user(
        pool,
        merchant_id=_merchant_id_of(request),
        user_id=user_id,
        email=body.email,
        kyc_status=body.kyc_status,
        metadata=body.metadata,
    )
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return _user_to_public(row)


# ---------------------------------------------------------------------
# Wallets — lazy provisioning
# ---------------------------------------------------------------------

class CreateWalletBody(BaseModel):
    network: str = Field(..., min_length=1)
    # Exactly one of these must be set:
    end_user_id: Optional[str] = None
    treasury: Optional[str] = Field(
        default=None,
        description="If set, provisions a merchant-owned wallet. "
        "Values: 'treasury'|'fee'|'hot'|'cold'.",
        pattern="^(treasury|fee|hot|cold)$",
    )
    info: Optional[str] = Field(default=None, max_length=200)


@router.post("/wallets", status_code=201)
async def create_wallet(body: CreateWalletBody, request: Request) -> dict:
    pool = get_db_pool(request)
    if bool(body.end_user_id) == bool(body.treasury):
        raise HTTPException(
            status_code=400,
            detail="Specify exactly one of end_user_id, treasury",
        )
    mid = _merchant_id_of(request)
    if body.end_user_id:
        try:
            return await wallets.provision_user_wallet(
                pool,
                merchant_id=mid,
                end_user_id=body.end_user_id,
                network=body.network,
                info=body.info,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    assert body.treasury is not None
    return await wallets.provision_treasury_wallet(
        pool,
        merchant_id=mid,
        network=body.network,
        purpose=body.treasury,
        info=body.info,
    )


@router.get("/wallets/{wallet_id}")
async def get_wallet_endpoint(wallet_id: str, request: Request) -> dict:
    pool = get_db_pool(request)
    row = await wallets.get_wallet(
        pool, merchant_id=_merchant_id_of(request), wallet_id=wallet_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="wallet not found")
    return row


@router.get("/users/{user_id}/wallets")
async def list_user_wallets(user_id: str, request: Request) -> dict:
    pool = get_db_pool(request)
    rows = await wallets.list_user_wallets(
        pool, merchant_id=_merchant_id_of(request), end_user_id=user_id,
    )
    return {"wallets": rows}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _user_to_public(row: dict) -> dict:
    return {
        "id": row["id"],
        "external_id": row["external_id"],
        "email": row["email"],
        "kyc_status": row.get("kyc_status"),
        "metadata": row.get("metadata") or {},
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }
