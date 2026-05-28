"""B2B transaction send + signature flow for merchants.

Wraps the existing TransactionService / SignatureService with the
merchant-id tenancy filter and a simpler request shape (the merchant
gives us `wallet_id` and `to_address`, not Safina's token-string
format).

Status returned to merchant uses our own canonical names rather than
Safina's internal status field, so we can evolve the latter without
breaking integrators:

  pending     — created on Safina, awaiting signatures
  signed      — all signatures collected, queued for broadcast
  broadcasted — Safina pushed the tx, tx_hash present
  confirmed   — on-chain confirmation observed
  canceled    — Safina canceled (24h limit, slist mismatch, etc.)
  failed      — error during send/sign
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from backend.safina.factory import get_safina_client_for_org
from backend.safina.models import SendTransactionRequest
from backend.safina.tx_status import is_broadcast_hash, clean_tx_hash, looks_canceled

logger = logging.getLogger("orgon.merchant_tx")


def _status_from_row(row: dict) -> str:
    # Shared `tx`-field interpretation (backend.safina.tx_status) so this
    # surface can never diverge from the sync/webhook paths.
    h = row.get("tx_hash")
    if not (h and str(h).strip()):
        # Either pending or signed-but-not-broadcast — for V1 we
        # surface both as 'pending'. A future tweak can read the
        # signatures table to differentiate.
        return "pending"
    if looks_canceled(h):
        return "canceled"
    if is_broadcast_hash(h):
        return "broadcasted"
    # Unknown non-hash string — never claim a broadcast we can't prove.
    return "pending"


def _row_to_public(row, *, network: Optional[int] = None) -> dict:
    """Shape internal `transactions` row for the public API."""
    if not row:
        return {}
    return {
        "id": row.get("unid"),
        "wallet_name": row.get("wallet_name"),
        "to_address": row.get("to_addr"),
        "value": row.get("value"),
        "token": row.get("token"),
        "network": network or row.get("network"),
        "tx_hash": clean_tx_hash(row.get("tx_hash")),
        "status": _status_from_row(row),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


async def send_transaction(
    pool,
    *,
    merchant_id: str,
    wallet_id: str,
    to_address: str,
    amount: str,
    asset: str = "TRX",
    info: Optional[str] = None,
) -> dict:
    """Initiate a transfer from a merchant wallet.

    Steps:
      1. Resolve wallet — must belong to merchant.
      2. Build Safina token string `<network>:::<asset>###<wallet_name>`.
      3. Call Safina tenant client to create + sign.
      4. Persist locally with merchant_id tag.
    """
    async with pool.acquire() as conn:
        w = await conn.fetchrow(
            """
            SELECT id, name, network, end_user_id
              FROM wallets
             WHERE id = $1 AND organization_id = $2
               AND COALESCE(is_hidden, false) = false
            """,
            UUID(wallet_id),
            UUID(merchant_id),
        )
    if not w:
        raise ValueError(f"wallet {wallet_id} not found under merchant {merchant_id}")

    wallet_name = w["name"]
    network = int(w["network"])
    token = f"{network}:::{asset}###{wallet_name}"

    tenant = await get_safina_client_for_org(pool, merchant_id)
    try:
        # Build send → Safina returns tx_unid. We do not run our
        # local AML rules in this path yet (V1 punts to merchant
        # responsibility, per the product Q&A). Rules engine wiring
        # is sprint 5 territory.
        req = SendTransactionRequest(
            token=token,
            to_address=to_address,
            value=str(amount),
            info=info or "",
        )
        tx_unid = await tenant.send_transaction(
            token=req.token,
            to_address=req.to_address,
            value=req.value,
            info=req.info or "",
        )
    finally:
        await tenant.close()

    # Cache locally with merchant tag so list/show queries stay
    # tenancy-scoped without re-asking Safina.
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO transactions
              (token, to_addr, value, unid, status, wallet_name, network,
               organization_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $8)
            ON CONFLICT (unid) DO NOTHING
            """,
            token, to_address, str(amount), tx_unid,
            wallet_name, network, UUID(merchant_id), now,
        )

    # Bump billing counter — non-fatal if it errors.
    try:
        from backend.services.merchant_billing import record_tx
        await record_tx(pool, merchant_id)
    except Exception:
        pass

    return await get_transaction(
        pool, merchant_id=merchant_id, tx_id=tx_unid,
    )


async def sign_transaction(
    pool, *, merchant_id: str, tx_id: str, request_id: Optional[str] = None,
) -> dict:
    """Sign a pending tx under the merchant's EC. Used when slist
    requires the merchant key to confirm (which is the default for
    our auto-injected slist).

    `request_id` — X-Request-Id of the merchant's API call, threaded
    into `signature_history.request_id` (TD-2 audit unification).
    """
    # Pull cached tx fields so the Wave-22 ec_sign scaffold (gated by
    # SAFINA_CANONICAL_VARIANT) can build the canonical signature body.
    # When the env flag is unset, the client ignores tx_payload and
    # keeps the legacy empty-body call — no behavioural change.
    async with pool.acquire() as conn:
        tx_row = await conn.fetchrow(
            "SELECT network, value, to_addr FROM transactions WHERE unid = $1",
            tx_id,
        )
    tx_payload: Optional[dict] = None
    if tx_row and tx_row.get("network") is not None and tx_row.get("to_addr"):
        tx_payload = {
            "network": tx_row["network"],
            "value": tx_row.get("value") or "0",
            "to_address": tx_row["to_addr"],
        }

    tenant = await get_safina_client_for_org(pool, merchant_id)
    signer_address = tenant._signer.address
    try:
        await tenant.sign_transaction(tx_unid=tx_id, tx_payload=tx_payload)
    finally:
        await tenant.close()

    # TD-2: write to signature_history so /v1/* signs land in the same
    # audit trail as /api/signatures/*. UNIQUE violation is treated as
    # idempotent (caller re-submitted) — return the current tx state
    # instead of bubbling 500.
    try:
        from backend.services.signature_service import record_signature_history
        async with pool.acquire() as conn:
            await record_signature_history(
                conn,
                tx_unid=tx_id,
                signer_address=signer_address,
                action="signed",
                request_id=request_id,
            )
    except Exception as exc:  # noqa: BLE001 — audit miss must not break sign
        # Importing asyncpg lazily — if we're in the unique-violation
        # branch the sign was idempotent and audit is already present.
        import asyncpg
        if isinstance(exc, asyncpg.UniqueViolationError):
            pass
        else:
            logger.warning(
                "signature_history insert failed merchant=%s tx=%s err=%s",
                merchant_id, tx_id, exc,
            )

    return await get_transaction(pool, merchant_id=merchant_id, tx_id=tx_id)


async def get_transaction(
    pool, *, merchant_id: str, tx_id: str,
) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM transactions
             WHERE unid = $1 AND organization_id = $2
            """,
            tx_id, UUID(merchant_id),
        )
    return _row_to_public(row) if row else None


async def list_transactions(
    pool,
    *,
    merchant_id: str,
    wallet_id: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> dict:
    """List merchant's transactions, optionally filtered by wallet.

    Cursor is the created_at iso of the last row on the previous page.
    """
    limit = max(1, min(limit, 200))
    args: list = [UUID(merchant_id)]
    where = "organization_id = $1"
    if wallet_id:
        async with pool.acquire() as conn:
            w = await conn.fetchrow(
                "SELECT name FROM wallets WHERE id = $1 AND organization_id = $2",
                UUID(wallet_id), UUID(merchant_id),
            )
        if not w:
            return {"transactions": [], "next_cursor": None}
        args.append(w["name"])
        where += f" AND wallet_name = ${len(args)}"
    if cursor:
        args.append(cursor)
        where += f" AND created_at < ${len(args)}"
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT * FROM transactions
             WHERE {where}
             ORDER BY created_at DESC
             LIMIT {limit + 1}
            """,
            *args,
        )
    items = [_row_to_public(r) for r in rows[:limit]]
    next_cursor = (
        rows[limit - 1]["created_at"].isoformat()
        if len(rows) > limit and items
        else None
    )
    return {"transactions": items, "next_cursor": next_cursor}
