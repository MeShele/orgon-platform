"""Outbound on-chain confirmation sweep — the real source of
`transaction.confirmed`.

The lifecycle emit (`TransactionService._emit_tx_lifecycle_events`) now
fires ONLY `transaction.broadcasted` when a tx_hash first appears. This
sweep polls the public explorer for each broadcasted-but-not-yet-confirmed
tx and fires `transaction.confirmed` (with `block_number`) once the tx is
actually included in a block — the DFNS-parity signal asystem-core uses to
mark an order completed.

Gate (at-most-once): `tx_hash` is a real hash, `confirmed_emitted_at IS
NULL`, `organization_id` present. The confirming tick atomically flips
`confirmed_emitted_at` (RETURNING) so only it emits. Not-yet-confirmed
txs are simply retried next tick; we stop polling after 7 days so a
dropped/never-confirmed tx eventually falls out of the scan.

Never raises out of the tick — a publish/network blip is logged and the
scheduler keeps going.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from backend.safina.tx_status import is_broadcast_hash
from backend.services.tx_confirmation import (
    get_onchain_confirmation,
    supports_confirmation,
)

logger = logging.getLogger("orgon.transaction_confirmation_sweep")


def _network_of(row) -> Optional[int]:
    """Network chain_id for the tx — from the column, else parsed from the
    Safina token string `network:::ASSET###wallet`."""
    n = row.get("network")
    if n is not None:
        try:
            return int(n)
        except (TypeError, ValueError):
            pass
    head = (row.get("token") or "").split(":::", 1)[0]
    try:
        return int(head)
    except (TypeError, ValueError):
        return None


async def run_tick(pool, *, limit: int = 200) -> dict:
    """Poll explorers for broadcasted txs; emit `transaction.confirmed`
    on real confirmation. Returns `{candidates, confirmed, events_emitted}`."""
    stats = {"candidates": 0, "confirmed": 0, "events_emitted": 0}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, unid, organization_id::text AS merchant_id,
                   wallet_name, to_addr, value, token, tx_hash, network
              FROM transactions
             WHERE tx_hash IS NOT NULL
               AND confirmed_emitted_at IS NULL
               AND organization_id IS NOT NULL
               AND updated_at > now() - interval '7 days'
             ORDER BY updated_at ASC
             LIMIT $1
            """,
            limit,
        )

    if not rows:
        return stats
    stats["candidates"] = len(rows)

    from backend.services.webhook_publisher import publish_event, EV_TX_CONFIRMED

    async with httpx.AsyncClient(timeout=15.0) as client:
        for r in rows:
            tx_hash = r["tx_hash"]
            # Defensive: never treat a Safina status/error string as a hash.
            if not is_broadcast_hash(tx_hash):
                continue
            network = _network_of(r)
            if not supports_confirmation(network):
                continue

            res = await get_onchain_confirmation(client, network, tx_hash)
            if not (res.found and res.confirmed):
                continue  # not yet — retry next tick
            stats["confirmed"] += 1

            # Atomic at-most-once: only the tick that flips
            # confirmed_emitted_at emits the webhook. We deliberately do
            # NOT touch `status` — it already reads 'confirmed' the moment
            # a hash appears (operator-cosmetic); the webhook is the
            # integration contract and is what we're making accurate.
            async with pool.acquire() as conn:
                claimed = await conn.fetchval(
                    """
                    UPDATE transactions
                       SET confirmed_emitted_at = now(),
                           block_number = COALESCE($2, block_number),
                           updated_at = now()
                     WHERE id = $1::uuid AND confirmed_emitted_at IS NULL
                     RETURNING id
                    """,
                    r["id"],
                    res.block_number,
                )
            if not claimed:
                continue  # another worker beat us to it

            try:
                await publish_event(
                    pool,
                    merchant_id=r["merchant_id"],
                    event_type=EV_TX_CONFIRMED,
                    payload={
                        "tx_id": r["id"],
                        "tx_unid": r["unid"],
                        "tx_hash": tx_hash,
                        "wallet_name": r["wallet_name"],
                        "to_address": r["to_addr"],
                        "amount": str(r["value"]) if r["value"] is not None else None,
                        "token": r["token"],
                        "block_number": res.block_number,
                    },
                )
                stats["events_emitted"] += 1
            except Exception as e:
                logger.warning(
                    "transaction.confirmed publish failed tx=%s: %s", r["unid"], e
                )

    return stats
