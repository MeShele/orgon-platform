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

from typing import Literal, Optional
from uuid import UUID

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
        request_id=getattr(request.state, "request_id", None),
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
# Balance & treasury — read-only snapshots of locally-cached `token_balances`.
# The sync worker is the only path that talks to Safina; this read-path
# never does. `as_of` reflects when the cache was last refreshed (~5 min
# typical, longer if Safina is down).
# ---------------------------------------------------------------------

@router.get("/wallets/{wallet_id}/balance")
async def get_wallet_balance_endpoint(wallet_id: str, request: Request) -> dict:
    from backend.services import merchant_balance_service as bal
    pool = get_db_pool(request)
    out = await bal.get_wallet_balance(
        pool, merchant_id=_merchant_id_of(request), wallet_id=wallet_id,
    )
    if out is None:
        raise HTTPException(status_code=404, detail="wallet not found")
    return out


@router.get("/treasury")
async def get_merchant_treasury_endpoint(request: Request) -> dict:
    """Merchant-owned wallets only (`treasury` / `fee` / `hot` / `cold`).
    `user_deposit` wallets are intentionally excluded — those are
    per-end-user addresses, not treasury inventory."""
    from backend.services import merchant_balance_service as bal
    pool = get_db_pool(request)
    return await bal.get_merchant_treasury(
        pool, merchant_id=_merchant_id_of(request),
    )


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
# Deposit lookup — support / debug tool. Returns every `deposits` row
# matching a tx_hash, scoped to the caller's merchant. Handles the
# most common KG-crypto support ticket ("я отправил, где деньги")
# without making support hand-decode explorers.
#
# Deliberately stops at our DB: cross-network discovery (when a user
# sent USDT-TRC20 to your Ethereum wallet — those never land in our
# `deposits` table) is a separate epic. The `include_offchain=true`
# param reserves the response slot for it.
# ---------------------------------------------------------------------

@router.get("/deposits/lookup")
async def v1_deposit_lookup(
    request: Request,
    tx_hash: str = Query(..., min_length=1, max_length=200, description="Exact tx_hash to look up. No partial matches."),
    include_offchain: bool = Query(
        False,
        description="Reserved for future cross-network discovery via "
        "Safina / chain explorers. Today returns a structured "
        "'not yet supported' hint when true; the lookup itself only "
        "ever searches the local `deposits` cache.",
    ),
) -> dict:
    from backend.services import merchant_deposit_lookup_service as dlookup
    pool = get_db_pool(request)
    merchant_id = _merchant_id_of(request)
    rows = await dlookup.lookup_by_tx_hash(
        pool, merchant_id=merchant_id, tx_hash=tx_hash,
    )
    return dlookup.build_lookup_response(
        tx_hash=tx_hash, deposits=rows, include_offchain=include_offchain,
    )


# ---------------------------------------------------------------------
# Compliance rules — AML monitoring rule CRUD, scoped to the caller's
# merchant. Mirrors the JWT `/api/v1/compliance/rules` surface so an
# external orchestrator (e.g. asystem-core's admin) can manage AML
# config without round-tripping users through the Orgon dashboard.
#
# Rules created here get `source='api'` so the Orgon dashboard can
# show "API-managed" badges and operators understand the channel.
# ---------------------------------------------------------------------

# Full set including E-07 extensions — same vocabulary as
# `ComplianceService.SUPPORTED_RULE_TYPES`. The JWT route's Literal
# is narrower (3 legacy types) for back-compat with old clients; here
# we expose everything the engine actually evaluates because external
# orchestrators have no UI-side restraint to keep them on the legacy
# subset.
_V1_RULE_TYPES = Literal[
    "threshold",
    "velocity",
    "blacklist_address",
    "velocity_amount_usd",
    "recipient_whitelist",
    "time_window",
    "recipient_geo_block",
]
_V1_RULE_ACTIONS = Literal["alert", "hold", "block", "request_approval"]
_V1_RULE_SEVERITIES = Literal["low", "medium", "high", "critical"]


class V1MonitoringRuleCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=255)
    rule_type: _V1_RULE_TYPES
    description: Optional[str] = Field(default=None, max_length=2000)
    rule_config: dict
    action: _V1_RULE_ACTIONS = "alert"
    severity: _V1_RULE_SEVERITIES = "medium"
    is_active: bool = True


class V1MonitoringRuleUpdate(BaseModel):
    rule_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    rule_type: Optional[_V1_RULE_TYPES] = None
    description: Optional[str] = Field(default=None, max_length=2000)
    rule_config: Optional[dict] = None
    action: Optional[_V1_RULE_ACTIONS] = None
    severity: Optional[_V1_RULE_SEVERITIES] = None
    is_active: Optional[bool] = None


def _rule_to_public(row: dict) -> dict:
    """Same shape as the JWT-side `MonitoringRule` model, minus
    `created_by` (an internal int the merchant can't act on)."""
    return {
        "id": str(row["id"]),
        "organization_id": str(row["organization_id"]) if row.get("organization_id") else None,
        "rule_name": row["rule_name"],
        "rule_type": row["rule_type"],
        "description": row.get("description"),
        "rule_config": row.get("rule_config") or {},
        "action": row["action"],
        "severity": row["severity"],
        "is_active": row["is_active"],
        "source": row.get("source") or "ui",
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _compliance_service(request: Request):
    """Cheap inline service factory. Avoids dragging the JWT-side
    `get_compliance_service` (which depends on FastAPI's `Depends`
    machinery) into the HMAC-route world."""
    from backend.services.compliance_service import ComplianceService
    return ComplianceService(get_db_pool(request))


@router.get("/compliance/rules")
async def v1_list_rules(request: Request) -> dict:
    """List rules belonging to this merchant. Global rules
    (`organization_id IS NULL`) are NOT visible on the `/v1/*`
    surface — those are platform-wide policies set by the ORGON team
    and shouldn't appear in an external orchestrator's admin UI."""
    svc = _compliance_service(request)
    merchant_id = UUID(_merchant_id_of(request))
    rows = await svc.list_monitoring_rules(
        org_ids=[merchant_id],
        include_global=False,
    )
    return {"rules": [_rule_to_public(r) for r in rows]}


@router.get("/compliance/rules/{rule_id}")
async def v1_get_rule(rule_id: str, request: Request) -> dict:
    svc = _compliance_service(request)
    merchant_id = UUID(_merchant_id_of(request))
    try:
        rid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="rule_id must be uuid")
    row = await svc.get_monitoring_rule(rid, org_ids=[merchant_id])
    # Hide global rules: even if the merchant happens to know a global
    # rule's id, /v1/* shouldn't surface it.
    if row is None or row.get("organization_id") is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return _rule_to_public(row)


@router.post("/compliance/rules", status_code=201)
async def v1_create_rule(body: V1MonitoringRuleCreate, request: Request) -> dict:
    svc = _compliance_service(request)
    merchant_id = UUID(_merchant_id_of(request))
    _validate_v1_rule_config(body.rule_type, body.rule_config)
    row = await svc.create_monitoring_rule(
        organization_id=merchant_id,
        rule_name=body.rule_name,
        rule_type=body.rule_type,
        description=body.description,
        rule_config=body.rule_config,
        action=body.action,
        severity=body.severity,
        is_active=body.is_active,
        actor_user_id=None,  # HMAC route — no human user
        source="api",
    )
    return _rule_to_public(row)


@router.patch("/compliance/rules/{rule_id}")
async def v1_update_rule(
    rule_id: str, body: V1MonitoringRuleUpdate, request: Request,
) -> dict:
    svc = _compliance_service(request)
    merchant_id = UUID(_merchant_id_of(request))
    try:
        rid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="rule_id must be uuid")

    # Pre-check existence + scope so the validation error below
    # doesn't leak "rule of another merchant exists at this id".
    existing = await svc.get_monitoring_rule(rid, org_ids=[merchant_id])
    if existing is None or existing.get("organization_id") is None:
        raise HTTPException(status_code=404, detail="rule not found")

    # Validate config against the resulting `rule_type` (caller's new
    # type if passed, otherwise the existing one).
    if body.rule_config is not None:
        effective_type = body.rule_type or existing["rule_type"]
        _validate_v1_rule_config(effective_type, body.rule_config)

    row = await svc.update_monitoring_rule(
        rid,
        org_ids=[merchant_id],
        actor_user_id=None,
        rule_name=body.rule_name,
        rule_type=body.rule_type,
        description=body.description,
        rule_config=body.rule_config,
        action=body.action,
        severity=body.severity,
        is_active=body.is_active,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return _rule_to_public(row)


@router.delete("/compliance/rules/{rule_id}", status_code=204)
async def v1_delete_rule(rule_id: str, request: Request):
    svc = _compliance_service(request)
    merchant_id = UUID(_merchant_id_of(request))
    try:
        rid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="rule_id must be uuid")

    existing = await svc.get_monitoring_rule(rid, org_ids=[merchant_id])
    if existing is None or existing.get("organization_id") is None:
        raise HTTPException(status_code=404, detail="rule not found")

    deleted = await svc.delete_monitoring_rule(
        rid, org_ids=[merchant_id], actor_user_id=None,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="rule not found")
    # FastAPI auto-converts None to 204 with empty body


def _validate_v1_rule_config(rule_type: str, config: dict) -> None:
    """Per-type config schema. Mirrors `_validate_rule_config` in
    `routes_compliance.py` for the 3 legacy types; accepts opaque
    config for the E-07 extensions (the engine validates them at
    evaluation time, not insert time)."""
    if rule_type == "threshold":
        if "threshold_usd" not in config and "threshold" not in config:
            raise HTTPException(
                status_code=422,
                detail="threshold rules require rule_config.threshold_usd",
            )
        try:
            float(str(config.get("threshold_usd", config.get("threshold"))))
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422,
                detail="threshold_usd must be a number",
            )
    elif rule_type == "velocity":
        for k in ("count", "window_hours"):
            if k not in config:
                raise HTTPException(
                    status_code=422,
                    detail=f"velocity rules require rule_config.{k}",
                )
            if not isinstance(config[k], int) or config[k] <= 0:
                raise HTTPException(
                    status_code=422,
                    detail=f"velocity rule_config.{k} must be a positive integer",
                )
    elif rule_type == "blacklist_address":
        addrs = config.get("addresses")
        if not isinstance(addrs, list) or not addrs:
            raise HTTPException(
                status_code=422,
                detail="blacklist_address rules require non-empty rule_config.addresses[]",
            )
        for a in addrs:
            if not isinstance(a, str):
                raise HTTPException(
                    status_code=422,
                    detail="blacklist_address rule_config.addresses must contain strings",
                )
    # E-07 types (`velocity_amount_usd`, `recipient_whitelist`,
    # `time_window`, `recipient_geo_block`): opaque config — Pydantic
    # only enforces dict shape, engine validates at evaluation time.


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
