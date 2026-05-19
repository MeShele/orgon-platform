"""Timeout-based `transaction.failed` source-of-truth.

Today ORGON has no positive failure signal from Safina's polling API
(it returns rejected txs the same way as in-flight ones — without a
`tx_hash`) and the Safina-side webhook callback path is gone (deleted
in Wave 30: it was SQLite-era code against a Postgres-only table).
The smallest honest detector for "this payout is never landing" is a
timeout sweep: a tx that has been `status='signed'` without a
`tx_hash` for more than N hours is, with overwhelming probability,
dead — Safina would have broadcast it within seconds otherwise.

Behavior:
* Scope of rows considered: `status = 'signed'` AND `(tx_hash IS NULL
  OR tx_hash = '')` AND `updated_at < now() - $timeout` AND
  `organization_id IS NOT NULL` (multi-tenant safety — rows without
  tenancy never go out as merchant events).
* UPDATE...RETURNING in one SQL trip per match, atomically flipping
  status to `'failed'` and capturing the row data needed for the
  webhook payload. A subsequent tick sees `status='failed'` and won't
  match again — natural at-most-once emit per row.
* False-positive risk: if Safina ever takes longer than the threshold
  to broadcast (>24h by default), we'd emit `failed` prematurely and
  then, if Safina later returns a real `tx_hash`, the polling sync
  in `transaction_service.sync_transactions` would flip status to
  `'confirmed'` and re-emit `broadcasted` + `confirmed`. Net result:
  the merchant sees `failed` then `broadcasted`/`confirmed` for the
  same `tx_id`. Document downstream that `failed` is NOT terminal
  while `broadcasted`/`confirmed` for the same tx_id can supersede
  it. The threshold defaults conservatively (24h) but can be raised
  via `TX_FAILED_TIMEOUT_HOURS` if false positives surface in prod.

The right long-term source-of-truth (chain watcher polling tx_hash
status, or an honest Safina-side rejected indicator) supersedes this
sweep; until then this is the only `transaction.failed` emitter and
it gives merchants a bounded window in which to consider the payout
dead.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("orgon.transaction_failure_sweep")

DEFAULT_TIMEOUT_HOURS = 24
FAILURE_REASON = "timeout_no_broadcast"


def _resolve_timeout_hours(explicit: Optional[int]) -> int:
    if explicit is not None:
        return explicit
    raw = os.environ.get("TX_FAILED_TIMEOUT_HOURS", "")
    try:
        v = int(raw)
        if v > 0:
            return v
    except (TypeError, ValueError):
        pass
    return DEFAULT_TIMEOUT_HOURS


async def run_tick(pool, *, timeout_hours: Optional[int] = None) -> dict:
    """Mark all eligible stuck `signed` txs as `failed` and emit
    `transaction.failed` for each.

    Returns stats: `{candidates_swept: N, events_emitted: M}`. M may
    be < N if `publish_event` raises for some rows — the status
    transition still landed (it's atomic with the SELECT) but the
    webhook didn't queue. We log a warning per failure but never
    raise — the scheduler should keep ticking.
    """
    hours = _resolve_timeout_hours(timeout_hours)
    stats = {"candidates_swept": 0, "events_emitted": 0}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE transactions
               SET status     = 'failed',
                   updated_at = now()
             WHERE id IN (
                 SELECT id FROM transactions
                  WHERE status = 'signed'
                    AND (tx_hash IS NULL OR tx_hash = '')
                    AND updated_at < now() - ($1 || ' hours')::interval
                    AND organization_id IS NOT NULL
                  ORDER BY updated_at ASC
                  LIMIT 500
                  FOR UPDATE SKIP LOCKED
             )
         RETURNING id::text,
                   unid,
                   organization_id::text AS merchant_id,
                   wallet_name,
                   to_addr,
                   value,
                   token
            """,
            str(hours),
        )

    if not rows:
        return stats

    stats["candidates_swept"] = len(rows)

    try:
        from backend.services.webhook_publisher import (
            publish_event,
            EV_TX_FAILED,
        )
    except Exception as e:
        logger.error(
            "tx_failure_sweep: cannot import webhook_publisher (%s); "
            "rows were marked failed but no events emitted: %d",
            e, len(rows),
        )
        return stats

    for r in rows:
        try:
            await publish_event(
                pool,
                merchant_id=r["merchant_id"],
                event_type=EV_TX_FAILED,
                payload={
                    "tx_id": r["id"],
                    "tx_unid": r["unid"],
                    "tx_hash": None,
                    "wallet_name": r["wallet_name"],
                    "to_address": r["to_addr"],
                    "amount": r["value"],
                    "token": r["token"],
                    "reason": FAILURE_REASON,
                },
            )
            stats["events_emitted"] += 1
        except Exception as e:
            logger.warning(
                "tx_failure_sweep: publish failed tx_id=%s err=%s",
                r["id"], e,
            )
    return stats
