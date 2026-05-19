"""Treasury and per-wallet balance views for the merchant `/v1/*` API.

Source-of-truth: locally-cached `token_balances`, populated by the
`sync_balances` worker every ~5 min (env-tunable). We never call
Safina from this read-path — if Safina is down, `as_of` ages but the
endpoint keeps serving the last-known snapshot with the honest
timestamp; that's strictly better than a 503 for the operator's
admin UI.

Scope: every query filters on `wallets.organization_id` = caller's
merchant_id from the HMAC middleware. A cross-merchant lookup gets
the same 404 as a non-existent wallet — never a 403 — to avoid
leaking existence.

Join shape gotcha: `wallets.wallet_id` is an integer assigned by
Safina post-activation; `token_balances.wallet_id` is varchar storing
that integer as text. A wallet that exists locally but doesn't yet
have a Safina-side `wallet_id` (the activation race window) returns
an empty `balances` list with `as_of=null` — not a 500, not silent.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID


async def get_wallet_balance(
    pool, *, merchant_id: str, wallet_id: str,
) -> Optional[dict]:
    """Single-wallet balance snapshot. Returns None if the wallet
    doesn't exist OR doesn't belong to this merchant (caller treats
    both as 404).
    """
    async with pool.acquire() as conn:
        wallet = await conn.fetchrow(
            """
            SELECT id::text                AS id,
                   name,
                   network,
                   COALESCE(addr, '')       AS addr,
                   purpose,
                   end_user_id::text        AS end_user_id,
                   wallet_id                AS safina_wallet_id,
                   created_at
              FROM wallets
             WHERE organization_id = $1
               AND id = $2
               AND COALESCE(is_hidden, false) = false
            """,
            UUID(merchant_id),
            UUID(wallet_id),
        )
        if wallet is None:
            return None

        balances, as_of = await _load_balances_for(conn, wallet["safina_wallet_id"])
    return _shape_wallet(wallet, balances=balances, as_of=as_of)


async def get_merchant_treasury(pool, *, merchant_id: str) -> dict:
    """All merchant-owned wallets (`purpose IN treasury / fee / hot /
    cold`) with current balances. Excludes `user_deposit` — those are
    per-end-user deposit addresses, not treasury inventory.
    """
    async with pool.acquire() as conn:
        wallets = await conn.fetch(
            """
            SELECT id::text                AS id,
                   name,
                   network,
                   COALESCE(addr, '')       AS addr,
                   purpose,
                   end_user_id::text        AS end_user_id,
                   wallet_id                AS safina_wallet_id,
                   created_at
              FROM wallets
             WHERE organization_id = $1
               AND COALESCE(is_hidden, false) = false
               AND purpose IN ('treasury', 'fee', 'hot', 'cold')
             ORDER BY network ASC, created_at ASC
            """,
            UUID(merchant_id),
        )

        out: list[dict] = []
        for w in wallets:
            balances, as_of = await _load_balances_for(conn, w["safina_wallet_id"])
            out.append(_shape_wallet(w, balances=balances, as_of=as_of))

    return {"wallets": out}


async def _load_balances_for(conn, safina_wallet_id):
    """Helper — returns (balances_list, as_of_iso_or_None). Empty list
    when the wallet doesn't yet have a Safina-side wallet_id (activation
    race) or when no token rows have been synced.
    """
    if safina_wallet_id is None:
        return [], None

    # token_balances.wallet_id stores Safina's int as varchar
    wid_text = str(safina_wallet_id)

    rows = await conn.fetch(
        """
        SELECT token, value, decimals, network, updated_at
          FROM token_balances
         WHERE wallet_id = $1
         ORDER BY token ASC
        """,
        wid_text,
    )
    if not rows:
        return [], None

    as_of = max(r["updated_at"] for r in rows if r["updated_at"] is not None) if rows else None
    balances = [
        {
            "token": r["token"],
            "value": r["value"],
            "decimals": r["decimals"],
        }
        for r in rows
    ]
    return balances, as_of


def _shape_wallet(wallet, *, balances: list, as_of) -> dict:
    addr = (wallet.get("addr") or "").strip() or None
    return {
        "wallet_id": wallet["id"],
        "name": wallet.get("name"),
        "network": wallet.get("network"),
        "address": addr,
        "status": "active" if addr else "pending",
        "purpose": wallet.get("purpose"),
        "end_user_id": wallet.get("end_user_id"),
        "as_of": as_of.isoformat() if as_of is not None else None,
        "balances": balances,
    }
