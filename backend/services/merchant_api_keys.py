"""Merchant API key issuance, lookup, verification, revocation.

dfns-style credentials: each pair is `key_pub` (sent in every request
header as `X-ORGON-Key`) and `secret` (used to HMAC-sign requests on
the merchant side; we never store it, only a bcrypt hash).

Format:
  okl_<hex>   live public key
  okt_<hex>   test (sandbox) public key
  oksl_<hex>  live secret  (shown once at issue, never persisted plain)
  okst_<hex>  test secret

The leading prefix on `key_pub` mirrors the merchant.sandbox flag, so
a misrouted "test" key against a live merchant — or vice versa — fails
fast at lookup time before any signature math even runs.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import bcrypt

logger = logging.getLogger("orgon.merchant_api_keys")

_PUB_BYTES = 16     # 32 hex chars after the prefix
_SECRET_BYTES = 32  # 64 hex chars after the prefix


@dataclass
class IssuedKey:
    """Returned only at issuance — the secret is plaintext exactly once."""
    id: str
    key_pub: str
    secret_once: str
    scopes: list[str]
    label: Optional[str]


def _prefix(pub_or_secret: str, *, sandbox: bool) -> str:
    base = "okt" if sandbox else "okl"
    return f"{base}_{pub_or_secret}" if pub_or_secret == "pub" else f"{base[:2]}s{base[2]}_{pub_or_secret}"


def _make_pub(sandbox: bool) -> str:
    body = secrets.token_hex(_PUB_BYTES)
    return f"{'okt' if sandbox else 'okl'}_{body}"


def _make_secret(sandbox: bool) -> str:
    body = secrets.token_hex(_SECRET_BYTES)
    return f"{'okst' if sandbox else 'oksl'}_{body}"


def hash_secret(secret_plain: str) -> str:
    return bcrypt.hashpw(secret_plain.encode(), bcrypt.gensalt()).decode()


def verify_secret(secret_plain: str, secret_hash: str) -> bool:
    try:
        return bcrypt.checkpw(secret_plain.encode(), secret_hash.encode())
    except (ValueError, TypeError):
        return False


async def issue_key(
    pool,
    *,
    merchant_id: UUID | str,
    label: Optional[str],
    scopes: list[str],
    sandbox: bool,
    created_by: Optional[int] = None,
) -> IssuedKey:
    """Generate a fresh (pub, secret) pair, persist hash, return secret once.

    Caller must take care to surface `secret_once` exactly once to the
    merchant (e.g. modal). After this function returns, the secret
    cannot be recovered.
    """
    key_pub = _make_pub(sandbox)
    secret_plain = _make_secret(sandbox)
    secret_hash = hash_secret(secret_plain)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO merchant_api_keys (merchant_id, key_pub, secret_hash, label, scopes, created_by)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id::text, scopes
            """,
            UUID(str(merchant_id)),
            key_pub,
            secret_hash,
            label,
            scopes,
            created_by,
        )
    logger.info("merchant api key issued merchant=%s key_pub=%s label=%s scopes=%s", merchant_id, key_pub, label, scopes)
    return IssuedKey(
        id=row["id"],
        key_pub=key_pub,
        secret_once=secret_plain,
        scopes=list(row["scopes"] or []),
        label=label,
    )


async def list_keys(pool, *, merchant_id: UUID | str) -> list[dict]:
    """Public-side metadata for the dashboard. Never returns the hash."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, key_pub, label, scopes, last_used_at, expires_at, revoked_at, created_at
              FROM merchant_api_keys
             WHERE merchant_id = $1
             ORDER BY created_at DESC
            """,
            UUID(str(merchant_id)),
        )
    return [dict(r) for r in rows]


async def revoke_key(pool, *, merchant_id: UUID | str, key_id: UUID | str) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE merchant_api_keys
               SET revoked_at = now()
             WHERE id = $1 AND merchant_id = $2 AND revoked_at IS NULL
            """,
            UUID(str(key_id)),
            UUID(str(merchant_id)),
        )
    # asyncpg execute returns string like "UPDATE 1"
    return result.endswith(" 1")


async def lookup_active_by_pub(pool, key_pub: str) -> Optional[dict]:
    """Active = not revoked and not expired. Used by HMAC middleware."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id::text,
                   merchant_id::text AS merchant_id,
                   key_pub,
                   secret_hash,
                   scopes
              FROM merchant_api_keys
             WHERE key_pub = $1
               AND revoked_at IS NULL
               AND (expires_at IS NULL OR expires_at > now())
            """,
            key_pub,
        )
    return dict(row) if row else None


async def touch_last_used(pool, key_pub: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE merchant_api_keys SET last_used_at = now() WHERE key_pub = $1",
            key_pub,
        )
