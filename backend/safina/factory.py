"""Per-tenant SafinaPayClient factory.

Every mutation routes through `get_safina_client_for_org(org_id)`,
which pulls `organizations.safina_ec_private_key` for the tenant and
builds a fresh SafinaSigner + SafinaPayClient with that key. The
caller closes it via `await client.close()` when done.

There is intentionally no fallback to a global env key: the goal of
this factory is exactly tenant isolation. If an org row has no EC
configured we fail loud — silently signing on behalf of one tenant
with another tenant's key is the worst possible failure mode for a
custodial platform.

Onboarding (`POST /api/admin/merchants`) auto-generates a fresh
SECP256k1 key into `safina_ec_private_key` for every new merchant,
so production orgs always have one. The legacy global
`SAFINA_EC_PRIVATE_KEY` env var is still used by `signer_backends.py`
for the read-only `/api/*` sync flow, which is a separate concern
from per-tenant mutations.
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
    if not tenant_key:
        raise RuntimeError(
            f"Organization {org_id} has no safina_ec_private_key. "
            "Re-issue via POST /api/admin/merchants or backfill the column directly — "
            "this factory refuses to fall back to a shared key (tenant isolation)."
        )
    signer = SafinaSigner(private_key_hex=tenant_key)
    return SafinaPayClient(
        signer=signer,
        base_url=base_url or os.getenv("SAFINA_BASE_URL", "https://my.safina.pro/ece"),
    )
