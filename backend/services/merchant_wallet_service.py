"""Lazy wallet provisioning for merchants and end-users.

dfns-style headless custodial model. A wallet always belongs to one
of two owners:
  * merchant treasury  — corporate hot/fee/cold wallet
  * end user           — per-customer custodial deposit address

Every wallet is created via `POST /ece/newWallet` with a slist
containing the merchant's per-org EC as the SOLE signatory:

    slist = {
      "0": {"type": "all", "ecaddress": merchant_ec},
      "min_signs": "1"
    }

Safina auto-activates within ~60s because the request is signed by
exactly that EC ("owner approves own application"). No email, no SMS,
no end-user interaction with Safina at all. This matches how
`www.safina.pro` creates wallets — every Safina-side flow uses a
single owning EC, with no second-party confirmation channel.

The user ↔ wallet binding lives only in ORGON DB (`wallets.end_user_id`).
Safina has no concept of the merchant's end-users; that abstraction
is ours. This is what makes ORGON a platform rather than a Safina UI:
the exchanger's customer never sees Safina, never registers there,
never confirms an email.

Historical note — empirically verified 2026-05-18: dropping slist
entirely (the obvious-looking "headless" path) leaves the wallet
pending indefinitely. The заявка never gets approved because Safina
has no concept of "approve by owner without a slist entry". A slist
of exactly `{ec_owner}` is the right minimum.

We create wallets on demand (lazy) — never eager. A merchant with 10
enabled networks but only Tron-active customers won't pay for 9
useless wallets per user.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from backend.safina.factory import get_safina_client_for_org

logger = logging.getLogger("orgon.merchant_wallets")

# Networks safina exposes that are testnet. A sandbox merchant is
# restricted to this set — they get a clear 400 if they try to create
# a wallet on a mainnet chain, instead of accidentally losing real
# funds while validating their integration.
TESTNET_NETWORKS = {1010, 3010, 3040, 5010, 5810}


class SandboxRestriction(ValueError):
    """Raised when a sandbox merchant tries to use a non-testnet network."""


async def _is_sandbox(pool, merchant_id: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT sandbox FROM organizations WHERE id = $1::uuid",
            merchant_id,
        )
    return bool(row["sandbox"]) if row else False


async def _enforce_sandbox(pool, *, merchant_id: str, network: str) -> None:
    if not await _is_sandbox(pool, merchant_id):
        return
    try:
        n = int(network)
    except (TypeError, ValueError):
        raise SandboxRestriction(f"Unknown network '{network}'")
    if n not in TESTNET_NETWORKS:
        raise SandboxRestriction(
            f"Network {n} is mainnet — sandbox merchants are restricted to {sorted(TESTNET_NETWORKS)}."
        )


async def provision_user_wallet(
    pool,
    *,
    merchant_id: str,
    end_user_id: str,
    network: str,
    info: Optional[str] = None,
) -> dict:
    """Create a per-user deposit wallet on `network`.

    Idempotent at the (end_user_id, network, purpose='user_deposit')
    level: if a wallet already exists for this triple, return it.
    """
    # Look up an existing wallet first — saves a Safina round-trip
    # and ensures the merchant can call this on every user-deposit
    # screen render without burning rate-limit on /newWallet.
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT * FROM wallets
             WHERE organization_id = $1
               AND end_user_id = $2
               AND network = $3
               AND COALESCE(purpose, '') = 'user_deposit'
               AND COALESCE(is_hidden, false) = false
             LIMIT 1
            """,
            UUID(merchant_id),
            UUID(end_user_id),
            int(network),
        )
        user_exists = await conn.fetchval(
            "SELECT 1 FROM end_users WHERE id = $1 AND merchant_id = $2",
            UUID(end_user_id),
            UUID(merchant_id),
        )

    if existing:
        return _row_to_public(existing, purpose="user_deposit")

    await _enforce_sandbox(pool, merchant_id=merchant_id, network=network)

    if not user_exists:
        raise ValueError(f"end_user {end_user_id} not found under merchant {merchant_id}")

    # Headless custodial: slist with the merchant's EC as the *only*
    # signatory. Safina auto-activates the wallet within ~60s because
    # the request is signed by exactly that EC ("owner approves own
    # application") — no email, no SMS, no end-user confirmation.
    # The end_user_id below is our own ORGON-side binding; Safina
    # neither knows nor needs to know who that user is.
    #
    # Empirically verified 2026-05-18: dropping slist entirely leaves
    # the wallet pending indefinitely (заявка never approved); a slist
    # of `{ec_owner}` activates within one polling cycle.
    wallet_info = info or f"deposit:{end_user_id}"
    tenant = await get_safina_client_for_org(pool, merchant_id)
    try:
        merchant_ec = tenant._signer.address.lower()
        slist = {
            "0": {"type": "all", "ecaddress": merchant_ec},
            "min_signs": "1",
        }
        unid = await tenant.create_wallet(
            network=str(network),
            info=wallet_info,
            slist=slist,
        )
    finally:
        await tenant.close()

    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO wallets
              (name, my_unid, network, info, organization_id, end_user_id,
               purpose, created_at, updated_at)
            VALUES ($1, $1, $2, $3, $4, $5, 'user_deposit', $6, $6)
            ON CONFLICT (name) DO NOTHING
            RETURNING *
            """,
            unid,
            int(network),
            wallet_info,
            UUID(merchant_id),
            UUID(end_user_id),
            now,
        )
        if row is None:
            # ON CONFLICT race — fetch the surviving row.
            row = await conn.fetchrow("SELECT * FROM wallets WHERE name = $1", unid)
    logger.info(
        "user wallet provisioned merchant=%s user=%s network=%s unid=%s",
        merchant_id, end_user_id, network, unid,
    )
    return _row_to_public(row, purpose="user_deposit")


async def provision_treasury_wallet(
    pool,
    *,
    merchant_id: str,
    network: str,
    purpose: str = "treasury",  # 'treasury' | 'fee' | 'hot' | 'cold'
    info: Optional[str] = None,
) -> dict:
    """Create a merchant-owned wallet (no end_user).

    Multiple treasury wallets per (merchant, network) are allowed —
    a merchant might want separate `hot` and `fee` rows. So we don't
    short-circuit on existing rows; the caller is explicit.

    Same headless model as user wallets — slist with the merchant's
    EC as the only signatory, auto-activated by Safina.
    """
    await _enforce_sandbox(pool, merchant_id=merchant_id, network=network)
    tenant = await get_safina_client_for_org(pool, merchant_id)
    try:
        merchant_ec = tenant._signer.address.lower()
        slist = {
            "0": {"type": "all", "ecaddress": merchant_ec},
            "min_signs": "1",
        }
        unid = await tenant.create_wallet(
            network=str(network),
            info=info or f"{purpose}:{merchant_id[:8]}",
            slist=slist,
        )
    finally:
        await tenant.close()

    now = datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO wallets
              (name, my_unid, network, info, organization_id,
               purpose, created_at, updated_at)
            VALUES ($1, $1, $2, $3, $4, $5, $6, $6)
            ON CONFLICT (name) DO NOTHING
            RETURNING *
            """,
            unid,
            int(network),
            info or "",
            UUID(merchant_id),
            purpose,
            now,
        )
        if row is None:
            row = await conn.fetchrow("SELECT * FROM wallets WHERE name = $1", unid)
    logger.info(
        "treasury wallet provisioned merchant=%s purpose=%s network=%s unid=%s",
        merchant_id, purpose, network, unid,
    )
    return _row_to_public(row, purpose=purpose)


def _row_to_public(row, *, purpose: str) -> dict:
    """Shape internal wallets row into the public API contract.

    Hides internal columns the merchant doesn't need (organization_id,
    wallet_id from Safina, sync timestamps).
    """
    addr = (row.get("addr") or "").strip() if row else ""
    return {
        "id": str(row["id"]) if row.get("id") else None,
        "name": row.get("name"),
        "network": row.get("network"),
        "address": addr or None,
        "status": "active" if addr else "pending",
        "purpose": purpose,
        "end_user_id": str(row["end_user_id"]) if row.get("end_user_id") else None,
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }


async def get_wallet(
    pool, *, merchant_id: str, wallet_id: str
) -> Optional[dict]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM wallets
             WHERE organization_id = $1
               AND id = $2
               AND COALESCE(is_hidden, false) = false
            """,
            UUID(merchant_id),
            UUID(wallet_id),
        )
    if not row:
        return None
    return _row_to_public(row, purpose=row.get("purpose") or "user_deposit")


async def list_user_wallets(
    pool, *, merchant_id: str, end_user_id: str
) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM wallets
             WHERE organization_id = $1
               AND end_user_id = $2
               AND COALESCE(is_hidden, false) = false
             ORDER BY created_at DESC
            """,
            UUID(merchant_id),
            UUID(end_user_id),
        )
    return [_row_to_public(r, purpose=r.get("purpose") or "user_deposit") for r in rows]
