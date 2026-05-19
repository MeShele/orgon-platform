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
from backend.services import merchant_tx_service as txs

router = APIRouter(
    prefix="/v1",
    tags=["B2B Merchant API"],
    responses={
        401: {"description": "HMAC signature missing, invalid, or replay detected"},
        429: {"description": "Daily plan quota exceeded or per-IP rate limit hit"},
    },
)


# ---------------------------------------------------------------------
# Health & meta
# ---------------------------------------------------------------------

@router.get("/health")
async def public_health() -> dict:
    """Liveness probe. Unauthenticated by middleware exempt list."""
    return {"status": "ok", "service": "orgon-public-v1"}


@router.get("/health/extended")
async def public_health_extended(request: Request) -> dict:
    """Operator-grade health: are our internal queues caught up?

    Unauthenticated (in the exempt list) so a status page can scrape
    it without an API key. Numbers come from a single DB query and
    are safe to expose: no merchant-specific data leaks here.
    """
    pool = get_db_pool(request)
    async with pool.acquire() as conn:
        webhook = await conn.fetchrow(
            """
            SELECT
              COUNT(*) FILTER (WHERE delivered_at IS NULL AND attempts < 6) AS pending,
              EXTRACT(EPOCH FROM (now() - MIN(created_at) FILTER (
                WHERE delivered_at IS NULL AND attempts < 6
              )))::int AS oldest_pending_age_seconds
              FROM webhook_deliveries
            """
        )
        deposit = await conn.fetchrow(
            """
            SELECT
              EXTRACT(EPOCH FROM (now() - MAX(last_polled_at)))::int AS lag_seconds,
              COUNT(*) FILTER (WHERE error_streak >= 3) AS errored_wallets
              FROM deposit_watch_cursors
            """
        )
    # Best-effort metric mirror so /metrics shows the same numbers.
    try:
        from backend.services.metrics_service import (
            b2b_webhook_pending,
            b2b_deposit_watcher_lag_seconds,
        )
        b2b_webhook_pending.set(int(webhook["pending"] or 0))
        b2b_deposit_watcher_lag_seconds.set(int(deposit["lag_seconds"] or 0))
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "orgon-public-v1",
        "webhook_queue": {
            "pending": int(webhook["pending"] or 0),
            "oldest_pending_age_seconds": int(webhook["oldest_pending_age_seconds"] or 0),
        },
        "deposit_watcher": {
            "lag_seconds": int(deposit["lag_seconds"] or 0),
            "errored_wallets": int(deposit["errored_wallets"] or 0),
        },
    }


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
    from backend.services.merchant_wallet_service import SandboxRestriction
    try:
        if body.end_user_id:
            return await wallets.provision_user_wallet(
                pool,
                merchant_id=mid,
                end_user_id=body.end_user_id,
                network=body.network,
                info=body.info,
            )
        assert body.treasury is not None
        return await wallets.provision_treasury_wallet(
            pool,
            merchant_id=mid,
            network=body.network,
            purpose=body.treasury,
            info=body.info,
        )
    except SandboxRestriction as e:
        # Distinct 400 with a sandbox_restricted code so the SDK can
        # surface it specifically (UI: "this is a sandbox key, switch
        # to a live key or pick a testnet network").
        raise HTTPException(
            status_code=400,
            detail={"error": "sandbox_restricted", "message": str(e)},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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
# Deposits (incoming on-chain transfers)
# ---------------------------------------------------------------------

def _deposit_to_public(row) -> dict:
    return {
        "id": str(row["id"]),
        "wallet_id": str(row["wallet_id"]),
        "end_user_id": str(row["end_user_id"]) if row.get("end_user_id") else None,
        "network": row["network"],
        "tx_hash": row["tx_hash"],
        "log_index": row.get("log_index", 0),
        "from_address": row.get("from_address"),
        "to_address": row["to_address"],
        "asset": row["asset"],
        "amount": str(row["amount"]),
        "confirmations": row.get("confirmations", 0),
        "block_number": row.get("block_number"),
        "block_timestamp": row["block_timestamp"].isoformat() if row.get("block_timestamp") else None,
        "discovered_at": row["discovered_at"].isoformat() if row.get("discovered_at") else None,
        "status": row["status"],
    }


@router.get("/wallets/{wallet_id}/deposits")
async def list_wallet_deposits(
    wallet_id: str,
    request: Request,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Inbound on-chain transfers seen by our watcher.

    Returns most-recent-first. Cursor is discovered_at iso of the
    last row on the previous page.
    """
    from uuid import UUID
    pool = get_db_pool(request)
    mid = _merchant_id_of(request)

    args: list = [UUID(mid), UUID(wallet_id)]
    where = "merchant_id = $1 AND wallet_id = $2"
    if cursor:
        args.append(cursor)
        where += f" AND discovered_at < ${len(args)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM deposits
             WHERE {where}
             ORDER BY discovered_at DESC
             LIMIT {limit + 1}
            """,
            *args,
        )
    items = [_deposit_to_public(r) for r in rows[:limit]]
    next_cursor = (
        rows[limit - 1]["discovered_at"].isoformat()
        if len(rows) > limit and items
        else None
    )
    return {"deposits": items, "next_cursor": next_cursor}


# ---------------------------------------------------------------------
# Usage & billing
# ---------------------------------------------------------------------

@router.get("/invoices")
async def list_invoices_endpoint(
    request: Request, limit: int = Query(default=24, ge=1, le=120),
) -> dict:
    from backend.services import invoice_service as inv
    pool = get_db_pool(request)
    items = await inv.list_invoices(pool, merchant_id=_merchant_id_of(request), limit=limit)
    return {"invoices": items}


@router.get("/usage")
async def usage_summary(request: Request, days: int = Query(default=30, ge=1, le=90)) -> dict:
    """Today's counters + N-day history + current plan limits.

    Lets the merchant see how close they are to their plan ceiling
    without polling our admin endpoints.
    """
    from backend.services import merchant_billing as billing
    pool = get_db_pool(request)
    mid = _merchant_id_of(request)
    async with pool.acquire() as conn:
        org = await conn.fetchrow(
            "SELECT pricing_plan, sandbox FROM organizations WHERE id = $1::uuid",
            mid,
        )
    plan = (org["pricing_plan"] if org else None) or "sandbox"
    today = await billing.today_counters(pool, mid)
    hist = await billing.history(pool, merchant_id=mid, days=days)
    return {
        "plan": plan,
        "sandbox": bool(org["sandbox"]) if org else False,
        "limits": billing.limits_for(plan),
        "today": today,
        "history": hist,
    }


# ---------------------------------------------------------------------
# Webhook configuration & log
# ---------------------------------------------------------------------

class WebhookConfigBody(BaseModel):
    url: Optional[str] = Field(default=None, max_length=500)
    secret: Optional[str] = Field(default=None, max_length=120)


@router.get("/webhooks/config")
async def get_webhook_config(request: Request) -> dict:
    """Returns the merchant's current webhook URL and whether a secret
    is set (the secret itself is never returned)."""
    from uuid import UUID
    pool = get_db_pool(request)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT webhook_url, webhook_secret FROM organizations WHERE id = $1",
            UUID(_merchant_id_of(request)),
        )
    if not row:
        raise HTTPException(status_code=404, detail="merchant not found")
    return {
        "url": row["webhook_url"],
        "secret_set": bool((row["webhook_secret"] or "").strip()),
    }


@router.put("/webhooks/config")
async def put_webhook_config(body: WebhookConfigBody, request: Request) -> dict:
    """Partial update — only fields the caller passed.

    Setting `url` to empty string clears it (delivery worker will
    treat unconfigured rows as permanent skips).
    """
    from uuid import UUID
    pool = get_db_pool(request)
    sets = []
    args: list = [UUID(_merchant_id_of(request))]
    if body.url is not None:
        sets.append(f"webhook_url = ${len(args) + 1}")
        args.append(body.url)
    if body.secret is not None:
        sets.append(f"webhook_secret = ${len(args) + 1}")
        args.append(body.secret)
    if not sets:
        return await get_webhook_config(request)
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE organizations SET {', '.join(sets)}, updated_at = now() WHERE id = $1",
            *args,
        )
    return await get_webhook_config(request)


class WebhookTestBody(BaseModel):
    event_type: str = Field(default="webhook.test", max_length=80)
    payload: Optional[dict] = None


@router.post("/webhooks/test", status_code=202)
async def test_webhook(body: WebhookTestBody, request: Request) -> dict:
    """Queue a synthetic event for the merchant's configured URL.

    Useful for integration testing: lets a merchant verify HMAC
    parsing on their side without waiting for a real deposit. The
    event flows through the same delivery worker as any other —
    retries, signing, log, all consistent.
    """
    from backend.services.webhook_publisher import publish_event
    pool = get_db_pool(request)
    mid = _merchant_id_of(request)
    payload = body.payload if body.payload is not None else {
        "note": "Synthetic event from /v1/webhooks/test",
        "timestamp": int(__import__('time').time() * 1000),
    }
    delivery_id = await publish_event(
        pool,
        merchant_id=mid,
        event_type=body.event_type,
        payload=payload,
        request_id=getattr(request.state, "request_id", None),
    )
    return {"delivery_id": delivery_id, "queued": True}


@router.get("/webhooks/deliveries")
async def list_webhook_deliveries(
    request: Request,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Deliverability log for the merchant — useful for debugging
    integration. Newest first."""
    from uuid import UUID
    pool = get_db_pool(request)
    args: list = [UUID(_merchant_id_of(request))]
    where = "merchant_id = $1"
    if cursor:
        args.append(cursor)
        where += f" AND created_at < ${len(args)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id::text, event_type, attempts, last_status, last_error,
                   next_retry_at, delivered_at, created_at
              FROM webhook_deliveries
             WHERE {where}
             ORDER BY created_at DESC
             LIMIT {limit + 1}
            """,
            *args,
        )
    items = [
        {
            "id": r["id"],
            "event_type": r["event_type"],
            "attempts": r["attempts"],
            "last_status": r["last_status"],
            "last_error": r["last_error"],
            "next_retry_at": r["next_retry_at"].isoformat() if r["next_retry_at"] else None,
            "delivered_at": r["delivered_at"].isoformat() if r["delivered_at"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows[:limit]
    ]
    next_cursor = (
        rows[limit - 1]["created_at"].isoformat()
        if len(rows) > limit and items
        else None
    )
    return {"deliveries": items, "next_cursor": next_cursor}


@router.get("/users/{user_id}/deposits")
async def list_user_deposits(
    user_id: str,
    request: Request,
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """All inbound transfers across all of the user's wallets."""
    from uuid import UUID
    pool = get_db_pool(request)
    mid = _merchant_id_of(request)

    args: list = [UUID(mid), UUID(user_id)]
    where = "merchant_id = $1 AND end_user_id = $2"
    if cursor:
        args.append(cursor)
        where += f" AND discovered_at < ${len(args)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM deposits
             WHERE {where}
             ORDER BY discovered_at DESC
             LIMIT {limit + 1}
            """,
            *args,
        )
    items = [_deposit_to_public(r) for r in rows[:limit]]
    next_cursor = (
        rows[limit - 1]["discovered_at"].isoformat()
        if len(rows) > limit and items
        else None
    )
    return {"deposits": items, "next_cursor": next_cursor}


# ---------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------

class SendTxBody(BaseModel):
    wallet_id: str = Field(..., min_length=1)
    to_address: str = Field(..., min_length=1)
    amount: str = Field(..., min_length=1, description="Decimal string, e.g. '1.05'")
    asset: str = Field(default="TRX", min_length=1, max_length=20)
    info: Optional[str] = Field(default=None, max_length=200)


@router.post("/transactions", status_code=201)
async def send_transaction(body: SendTxBody, request: Request) -> dict:
    """Initiate an outbound transfer.

    Returns the tx record in `pending` state. If the wallet's slist
    requires the merchant's EC to sign (the default), call
    POST /v1/transactions/{tx_id}/sign next. Once signed, Safina
    broadcasts to the chain and `status` flips to `broadcasted` /
    `confirmed` (poll the GET endpoint).
    """
    pool = get_db_pool(request)
    try:
        return await txs.send_transaction(
            pool,
            merchant_id=_merchant_id_of(request),
            wallet_id=body.wallet_id,
            to_address=body.to_address,
            amount=body.amount,
            asset=body.asset,
            info=body.info,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/transactions/{tx_id}/sign")
async def sign_transaction_endpoint(tx_id: str, request: Request) -> dict:
    pool = get_db_pool(request)
    out = await txs.sign_transaction(
        pool, merchant_id=_merchant_id_of(request), tx_id=tx_id,
    )
    if not out:
        raise HTTPException(status_code=404, detail="transaction not found")
    return out


@router.get("/transactions/{tx_id}")
async def get_transaction_endpoint(tx_id: str, request: Request) -> dict:
    pool = get_db_pool(request)
    out = await txs.get_transaction(
        pool, merchant_id=_merchant_id_of(request), tx_id=tx_id,
    )
    if not out:
        raise HTTPException(status_code=404, detail="transaction not found")
    return out


@router.get("/transactions")
async def list_transactions_endpoint(
    request: Request,
    wallet_id: Optional[str] = Query(default=None),
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    pool = get_db_pool(request)
    return await txs.list_transactions(
        pool,
        merchant_id=_merchant_id_of(request),
        wallet_id=wallet_id,
        cursor=cursor,
        limit=limit,
    )


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
