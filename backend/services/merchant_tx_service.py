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

logger = logging.getLogger("orgon.merchant_tx")


def _status_from_row(row: dict) -> str:
    h = (row.get("tx_hash") or "").strip()
    if not h:
        # Either pending or signed-but-not-broadcast — for V1 we
        # surface both as 'pending'. A future tweak can read the
        # signatures table to differentiate.
        return "pending"
    low = h.lower()
    if "canceled" in low or "limit" in low or "failed" in low:
        return "canceled"
    return "broadcasted"


def _row_to_public(row, *, network: Optional[int] = None) -> dict:
    """Shape internal `transactions` row for the public API."""
    if not row:
        return {}
    h = (row.get("tx_hash") or "").strip()
    return {
        "id": row.get("unid"),
        "wallet_name": row.get("wallet_name"),
        "to_address": row.get("to_addr"),
        "value": row.get("value"),
        "token": row.get("token"),
        "network": network or row.get("network"),
        "tx_hash": h if (h and "canceled" not in h.lower() and "limit" not in h.lower()) else None,
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

    return await get_transaction(
        pool, merchant_id=merchant_id, tx_id=tx_unid,
    )


async def sign_transaction(
    pool, *, merchant_id: str, tx_id: str,
) -> dict:
    """Sign a pending tx under the merchant's EC. Used when slist
    requires the merchant key to confirm (which is the default for
    our auto-injected slist)."""
    tenant = await get_safina_client_for_org(pool, merchant_id)
    try:
        await tenant.sign_transaction(tx_unid=tx_id)
    finally:
        await tenant.close()
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
