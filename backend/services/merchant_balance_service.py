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

from .network_reference import NETWORK_REFERENCE


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


# ---------------------------------------------------------------------
# DFNS-compatible `/assets` projection.
#
# asystem-core's `/admin/custody-wallets` UI (and any other consumer
# already wired to the DFNS shape) expects:
#   { assets: [{ kind, symbol, decimals, balance, contract, verified }] }
# instead of our legacy `{ balances: [{token, value, decimals}] }`.
#
# We DON'T deprecate `/v1/wallets/{id}/balance` — existing merchants
# may already read that key. The new `/assets` endpoint is an
# additive surface that mirrors DFNS shape exactly so a single
# frontend component works against either custody provider.
#
# Caveat: Safina never reports a token's on-chain contract address
# through the balance feed (`token_balances` columns), so `contract`
# is always null. asystem-core's `dfnsAssetKind` util can fall back
# to symbol-only matching when contract is missing.
# ---------------------------------------------------------------------

# Native symbol per chain_id comes from the single source of truth
# (`network_reference.NETWORK_REFERENCE`) — NOT a second hardcoded map.
# A duplicated table here had drifted (ORGON mislabeled as "ORG"), which
# made `_classify_kind` treat native ORGON balances as tokens. Deriving
# from the authoritative map closes that drift permanently.
def _native_symbol(network: str | None) -> Optional[str]:
    if not network:
        return None
    try:
        cid = int(network)
    except (TypeError, ValueError):
        return None
    entry = NETWORK_REFERENCE.get(cid)
    return entry[1] if entry else None

# chain_id → asset-kind suffix used by DFNS for non-native tokens on
# that chain. We only emit these when the symbol differs from the
# chain's native (e.g. USDT on Tron → kind=Trc20).
_TOKEN_KIND_BY_CHAIN_ID: dict[str, str] = {
    "1000": "Token",   # BTC chain — no standard token kind name
    "3000": "Erc20",
    "3040": "Erc20",
    "5000": "Trc20",
    "5010": "Trc20",
    "5800": "Token",   # ORG chain — placeholder until mainnet token semantics fixed
    "5810": "Token",
}


def _classify_kind(network: str | None, symbol: str | None) -> str:
    """Return DFNS-compatible `kind` for an asset.

    Heuristic: if symbol equals the chain's native — `Native`. Else
    the chain-family token kind (`Erc20`, `Trc20`, …). Unknown
    chain → `Token` (generic) — keeps the consumer working without
    panic when we add a new network before this map is updated.
    """
    if not network:
        return "Token"
    native = _native_symbol(network)
    if native and symbol and symbol.upper() == native.upper():
        return "Native"
    return _TOKEN_KIND_BY_CHAIN_ID.get(network, "Token")


def _balance_to_asset(row: dict, *, network: str | None) -> dict:
    """Map one `token_balances` row to a DFNS-shape asset entry."""
    raw_decimals = row.get("decimals")
    try:
        decimals_int = int(raw_decimals) if raw_decimals is not None else 0
    except (TypeError, ValueError):
        decimals_int = 0
    symbol = row.get("token")
    return {
        "kind": _classify_kind(network, symbol),
        "symbol": symbol,
        "decimals": decimals_int,
        "balance": str(row.get("value") or "0"),
        "contract": None,
        "verified": True,
    }


async def get_wallet_assets(
    pool, *, merchant_id: str, wallet_id: str,
) -> Optional[dict]:
    """DFNS-compatible balance projection.

    Returns None on the same conditions as `get_wallet_balance`
    (wallet not found or cross-merchant lookup). The response shape
    intentionally tracks `dfns-wallet-balance`:
        { ok, wallet_id, address, network, role, assets, as_of }
    so a single asystem-core edge function (`orgon-wallet-balance`)
    can pipe the body straight to the existing PoolBalanceTile
    without per-provider branching.
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

    network = wallet.get("network")
    network_str = str(network) if network is not None else None
    assets = [_balance_to_asset(b, network=network_str) for b in balances]
    addr = (wallet.get("addr") or "").strip() or None
    return {
        "ok": True,
        "wallet_id": wallet["id"],
        "address": addr,
        "network": network,
        "role": wallet.get("purpose"),
        "as_of": as_of.isoformat() if as_of is not None else None,
        "assets": assets,
    }
