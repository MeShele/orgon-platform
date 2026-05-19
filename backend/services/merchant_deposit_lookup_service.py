"""Look up deposits by `tx_hash` for support / debug paths.

Primary use case: a merchant's support engineer gets a ticket
"deposit not detected", the user gave them a `tx_hash`. Today
that support engineer has to manually open tronscan / etherscan /
mempool.space, paste the hash, decode amounts, and tell the user
where the money actually went. With this service:

  GET /v1/deposits/lookup?tx_hash=…

returns every `deposits` row scoped to the caller's merchant — both
`pending` and `confirmed`, plus any orphaned rows (kept for audit).

Edge case the service intentionally does NOT handle today: deposits
made by users to an address on the **wrong network**. Those never
land in `deposits` (we never received a watcher event for them). The
endpoint returns `found: false` with a structured `hint` field so
the merchant's support tool can render a "your tx is probably on
another chain; check the explorer manually" message. Cross-chain
discovery via Safina or chain explorers is a separate epic — the
contract here reserves a place for it (`include_offchain` param) but
the implementation is deferred to avoid pulling in rate-limited
explorer APIs in a single sprint.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID


async def lookup_by_tx_hash(
    pool,
    *,
    merchant_id: str,
    tx_hash: str,
) -> list[dict[str, Any]]:
    """Return every `deposits` row matching `tx_hash` and merchant.

    Empty list when nothing matches — caller surfaces a 200 with
    `found: false` (NOT a 404, because the lookup is a successful
    search that just returned no rows; 404 would imply the endpoint
    itself doesn't exist).
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text                AS id,
                   merchant_id::text       AS merchant_id,
                   wallet_id::text         AS wallet_id,
                   end_user_id::text       AS end_user_id,
                   network,
                   tx_hash,
                   log_index,
                   from_address,
                   to_address,
                   asset,
                   amount,
                   confirmations,
                   block_number,
                   block_timestamp,
                   discovered_at,
                   status
              FROM deposits
             WHERE merchant_id = $1
               AND tx_hash     = $2
             ORDER BY log_index ASC
            """,
            UUID(merchant_id),
            tx_hash,
        )
    return [_row_to_public(r) for r in rows]


def _row_to_public(row) -> dict[str, Any]:
    """Same shape as `_deposit_to_public` in routes_public_v1 — kept
    in sync by repetition rather than import, so the response model
    contract isn't accidentally narrowed by a refactor of the listing
    endpoint."""
    return {
        "id": row["id"],
        "merchant_id": row["merchant_id"],
        "wallet_id": row["wallet_id"],
        "end_user_id": row.get("end_user_id"),
        "network": row["network"],
        "tx_hash": row["tx_hash"],
        "log_index": row.get("log_index", 0),
        "from_address": row.get("from_address"),
        "to_address": row["to_address"],
        "asset": row["asset"],
        "amount": str(row["amount"]),
        "confirmations": row.get("confirmations", 0),
        "block_number": row.get("block_number"),
        "block_timestamp": (
            row["block_timestamp"].isoformat() if row.get("block_timestamp") else None
        ),
        "discovered_at": (
            row["discovered_at"].isoformat() if row.get("discovered_at") else None
        ),
        "status": row["status"],
    }


def build_lookup_response(
    *,
    tx_hash: str,
    deposits: list[dict[str, Any]],
    include_offchain: bool,
) -> dict[str, Any]:
    """Compose the canonical response.

    Centralised so the `/v1/*` route and the JWT-admin mirror return
    the same shape — important because the support workflow is one of
    the two main consumers and the response is also documented in the
    integration playbook §7.
    """
    found = len(deposits) > 0
    if found:
        hint: Optional[str] = None
    else:
        hint = (
            "No deposit with that tx_hash found in your wallets. "
            "If the user sent crypto, the most common cause is a "
            "wrong-network transfer (e.g. USDT-TRC20 sent to your "
            "Ethereum wallet) — we never see those because our "
            "watcher only listens on the network you registered the "
            "wallet for. Verify the destination address + network "
            "on the relevant explorer (tronscan / etherscan / "
            "mempool.space) before promising the user a refund."
        )

    out: dict[str, Any] = {
        "tx_hash": tx_hash,
        "found": found,
        "deposits": deposits,
        "hint": hint,
    }

    if include_offchain:
        # Contract placeholder — when cross-network discovery via
        # Safina/explorers lands, this dict gets a real `lookups: [...]`
        # array. Today it's an explicit "we don't yet, sorry" so the
        # caller's UI can render a sensible message instead of
        # silently treating offchain as supported.
        out["offchain_lookup"] = {
            "supported": False,
            "hint": (
                "Cross-network on-chain discovery is on the roadmap. "
                "For now, paste the tx_hash into the explorer for the "
                "network you suspect (tronscan / etherscan / "
                "mempool.space). If the user genuinely landed funds at "
                "a Safina-owned address on another network, contact "
                "support@orgon.asystem.kg — we can recover from "
                "Safina-side hot wallet balances case by case."
            ),
        }

    return out
