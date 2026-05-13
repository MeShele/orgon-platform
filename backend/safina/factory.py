"""Per-tenant SafinaPayClient factory.

The legacy global `_safina_client` in main.py is initialised with
the single SAFINA_EC_PRIVATE_KEY env var — fine for read-only sync
jobs, but wrong for any user-driven mutation: every tenant would
sign with the same EC and collapse into one Safina-side customer.

Mutations route through `get_safina_client_for_org(org_id)`:
    1. Pull `organizations.safina_ec_private_key` for the tenant
    2. Build a fresh SafinaSigner + SafinaPayClient with that key
    3. Caller closes it via `await client.close()` when done

Falls back to the global env key if no per-tenant key is set (so
single-tenant / dev installs keep working unchanged).
"""

from __future__ import annotations

import os
from typing import Optional
from uuid import UUID

import asyncpg

from backend.safina.client import SafinaPayClient
from backend.safina.signer import SafinaSigner


async def _resolve_tenant_key(
    pool: asyncpg.Pool,
    org_id: Optional[str | UUID],
) -> Optional[str]:
    """Return EC private key hex string for org, or None."""
    if org_id is None:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT safina_ec_private_key FROM organizations WHERE id = $1",
            UUID(str(org_id)),
        )
    return row["safina_ec_private_key"] if row else None


async def get_safina_client_for_org(
    pool: asyncpg.Pool,
    org_id: Optional[str | UUID],
    *,
    base_url: Optional[str] = None,
) -> SafinaPayClient:
    """Build a request-scoped SafinaPayClient for the tenant.

    Caller is responsible for `await client.close()` after use.
    """
    tenant_key = await _resolve_tenant_key(pool, org_id)
    private_key = tenant_key or os.getenv("SAFINA_EC_PRIVATE_KEY", "")
    if not private_key:
        raise RuntimeError(
            "No Safina EC key available: organization has no safina_ec_private_key "
            "and SAFINA_EC_PRIVATE_KEY env var is unset."
        )
    signer = SafinaSigner(private_key_hex=private_key)
    return SafinaPayClient(
        signer=signer,
        base_url=base_url or os.getenv("SAFINA_BASE_URL", "https://my.safina.pro/ece"),
    )
