"""End-user lifecycle for the merchant API.

An end-user belongs to exactly one merchant and is identified by:
* `id` — our UUID, returned to the merchant.
* `external_id` — the merchant's own user id; lets POST /v1/users be
  idempotent and lets merchants search without learning our UUIDs.
* `email` — the address we wire into Safina's slist for that user's
  wallets. This is what makes per-user balance tracking work on
  Safina's side.

All functions take `merchant_id` and enforce it in WHERE — never
trust caller-supplied tenancy.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

logger = logging.getLogger("orgon.end_users")


async def create_user(
    pool,
    *,
    merchant_id: str,
    external_id: str,
    email: str,
    kyc_status: Optional[str] = None,
    metadata: Optional[dict] = None,
    request_id: Optional[str] = None,
) -> dict:
    """Idempotent on (merchant_id, external_id).

    A repeat call with the same external_id refreshes mutable fields
    (email, kyc_status, metadata) — merchants do this to push KYC
    transitions through us — and returns the existing row.

    Emits the `user.created` webhook exactly once, on the very first
    INSERT — re-calls that hit ON CONFLICT DO UPDATE do NOT re-fire.
    The discriminator is Postgres's `xmax = 0` on the returned tuple
    (zero means a freshly inserted row; nonzero means an updated one).
    """
    import json
    md_json = json.dumps(metadata or {})
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO end_users (merchant_id, external_id, email, kyc_status, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (merchant_id, external_id) DO UPDATE
              SET email      = EXCLUDED.email,
                  kyc_status = EXCLUDED.kyc_status,
                  metadata   = EXCLUDED.metadata,
                  updated_at = now()
            RETURNING id::text, merchant_id::text, external_id, email,
                      kyc_status, metadata,
                      created_at, updated_at,
                      (xmax = 0) AS inserted
            """,
            UUID(merchant_id),
            external_id,
            email,
            kyc_status,
            md_json,
        )
    out = dict(row)
    inserted = bool(out.pop("inserted", False))
    if isinstance(out.get("metadata"), str):
        try:
            out["metadata"] = json.loads(out["metadata"])
        except Exception:
            out["metadata"] = {}

    if inserted:
        try:
            from backend.services.webhook_publisher import (
                publish_event,
                EV_USER_CREATED,
            )
            await publish_event(
                pool,
                merchant_id=merchant_id,
                event_type=EV_USER_CREATED,
                payload={
                    "id": out["id"],
                    "external_id": out["external_id"],
                    "email": out["email"],
                    "kyc_status": out.get("kyc_status"),
                },
                request_id=request_id,
            )
        except Exception as e:
            logger.warning(
                "user.created publish failed merchant=%s external_id=%s err=%s",
                merchant_id, external_id, e,
            )
    return out


async def get_user(pool, *, merchant_id: str, user_id: str) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, merchant_id::text, external_id, email,
                   kyc_status, metadata, created_at, updated_at
              FROM end_users
             WHERE merchant_id = $1 AND id = $2
            """,
            UUID(merchant_id),
            UUID(user_id),
        )
    return dict(row) if row else None


async def get_user_by_external_id(
    pool, *, merchant_id: str, external_id: str
) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text, merchant_id::text, external_id, email,
                   kyc_status, metadata, created_at, updated_at
              FROM end_users
             WHERE merchant_id = $1 AND external_id = $2
            """,
            UUID(merchant_id),
            external_id,
        )
    return dict(row) if row else None


async def list_users(
    pool,
    *,
    merchant_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> dict:
    """Cursor-based pagination. Cursor is the created_at iso of the
    last item on the previous page — predictable for clients, no
    surprises if rows get inserted between calls.
    """
    limit = max(1, min(limit, 200))
    args: list = [UUID(merchant_id)]
    where = "merchant_id = $1"
    if cursor:
        where += " AND created_at < $2"
        args.append(cursor)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id::text, merchant_id::text, external_id, email,
                   kyc_status, metadata, created_at, updated_at
              FROM end_users
             WHERE {where}
             ORDER BY created_at DESC
             LIMIT {limit + 1}
            """,
            *args,
        )
    items = [dict(r) for r in rows[:limit]]
    next_cursor = (
        items[-1]["created_at"].isoformat()
        if len(rows) > limit and items
        else None
    )
    return {"users": items, "next_cursor": next_cursor}


async def update_user(
    pool,
    *,
    merchant_id: str,
    user_id: str,
    email: Optional[str] = None,
    kyc_status: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[dict]:
    """Selective UPDATE — only fields the caller actually passed."""
    sets = []
    args: list = [UUID(merchant_id), UUID(user_id)]
    idx = 3
    if email is not None:
        sets.append(f"email = ${idx}")
        args.append(email)
        idx += 1
    if kyc_status is not None:
        sets.append(f"kyc_status = ${idx}")
        args.append(kyc_status)
        idx += 1
    if metadata is not None:
        import json
        sets.append(f"metadata = ${idx}::jsonb")
        args.append(json.dumps(metadata))
        idx += 1
    if not sets:
        return await get_user(pool, merchant_id=merchant_id, user_id=user_id)
    sets.append("updated_at = now()")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE end_users
               SET {', '.join(sets)}
             WHERE merchant_id = $1 AND id = $2
            RETURNING id::text, merchant_id::text, external_id, email,
                      kyc_status, metadata, created_at, updated_at
            """,
            *args,
        )
    return dict(row) if row else None
