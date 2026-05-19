"""Timeout-based `transaction.uncertain` preview signal.

The 24h `transaction.failed` sweep (Wave 31) tells merchants when
a payout is overwhelmingly dead. But 24h is too long for a user-
facing exchange — the end-user sees a silent spinner for hours,
loses patience, files a chargeback / opens a support ticket.

This sweep fires earlier (default 10 minutes), with a **non-terminal**
event. It signals: "this tx is taking longer than expected, but it
might still land — show your end-user a 'проверяем' message and
expose a contact-support CTA, don't declare anything failed yet."

Behaviour:
* Scope: `status='signed'` AND `(tx_hash IS NULL OR tx_hash='')`
  AND `updated_at < now() - $timeout_minutes` AND
  `organization_id IS NOT NULL` (multi-tenant safety)
  AND `uncertain_emitted_at IS NULL` (at-most-once gate).
* UPDATE…RETURNING in one SQL trip — atomic SET
  `uncertain_emitted_at=now()` with row-level lock so two parallel
  ticks never both emit. **Does NOT change `status`** — the row
  stays in `signed`; the 24h failure sweep will eventually flip it
  to `failed` if Safina never broadcasts.
* False-positive risk: identical to the failure sweep but smaller
  blast radius. If Safina catches up at minute 12, the next polling
  sync emits `transaction.broadcasted` + `confirmed` for the same
  tx_id. Merchant's webhook handler should treat `broadcasted`
  arriving after `uncertain` as "false alarm resolved" and clear
  the UI warning. Documented in WEBHOOKS.md.
* Threshold env: `TX_UNCERTAIN_TIMEOUT_MINUTES` (default 10).

When the long-term right-path source-of-truth lands (chain watcher
or Safina-side `pending` signal), `uncertain` retires. The contract
on the wire is forward-compatible — consumers who treated it as
"informational, may be superseded" will simply stop receiving it.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("orgon.transaction_uncertain_sweep")

DEFAULT_TIMEOUT_MINUTES = 10
SWEEP_BATCH_LIMIT = 500


def _resolve_timeout_minutes(explicit: Optional[int]) -> int:
    """Threshold for declaring a stuck-signed tx 'uncertain'.

    Resolution: explicit arg > env > default. Garbage env falls back
    to the default — never crashes the scheduler tick.
    """
    if explicit is not None:
        return explicit
    raw = os.environ.get("TX_UNCERTAIN_TIMEOUT_MINUTES", "")
    try:
        v = int(raw)
        if v > 0:
            return v
    except (TypeError, ValueError):
        pass
    return DEFAULT_TIMEOUT_MINUTES


async def run_tick(pool, *, timeout_minutes: Optional[int] = None) -> dict:
    """Flip eligible stuck-signed txs from "not yet warned" to
    "warned at now()" and emit `transaction.uncertain` for each.

    Returns stats `{candidates_swept: N, events_emitted: M}` — M
    may be < N if `publish_event` raises for some rows (queue blip).
    Row's `uncertain_emitted_at` is already set, so a retry-tick
    won't re-fire. That's the deliberate trade-off: one webhook
    queue blip = one missed warning, never duplicate warnings.
    """
    minutes = _resolve_timeout_minutes(timeout_minutes)
    stats = {"candidates_swept": 0, "events_emitted": 0}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            UPDATE transactions
               SET uncertain_emitted_at = now()
             WHERE id IN (
                 SELECT id FROM transactions
                  WHERE status = 'signed'
                    AND (tx_hash IS NULL OR tx_hash = '')
                    AND updated_at < now() - ($1 || ' minutes')::interval
                    AND organization_id IS NOT NULL
                    AND uncertain_emitted_at IS NULL
                  ORDER BY updated_at ASC
                  LIMIT $2
                  FOR UPDATE SKIP LOCKED
             )
         RETURNING id::text,
                   unid,
                   organization_id::text AS merchant_id,
                   wallet_name,
                   to_addr,
                   value,
                   token,
                   updated_at
            """,
            str(minutes),
            SWEEP_BATCH_LIMIT,
        )

    if not rows:
        return stats

    stats["candidates_swept"] = len(rows)

    try:
        from backend.services.webhook_publisher import (
            publish_event,
            EV_TX_UNCERTAIN,
        )
    except Exception as e:
        logger.error(
            "tx_uncertain_sweep: cannot import webhook_publisher (%s); "
            "rows were marked uncertain but no events emitted: %d",
            e, len(rows),
        )
        return stats

    for r in rows:
        try:
            stuck_seconds = None
            if r["updated_at"] is not None:
                # `updated_at` is the moment the row last changed; for a
                # signed-but-not-broadcast tx that's the moment Safina
                # accepted the signature. Surfacing how long it's been
                # stuck helps merchant UI render a useful timer.
                from datetime import datetime, timezone
                delta = datetime.now(timezone.utc) - r["updated_at"]
                stuck_seconds = int(delta.total_seconds())

            await publish_event(
                pool,
                merchant_id=r["merchant_id"],
                event_type=EV_TX_UNCERTAIN,
                payload={
                    "tx_id": r["id"],
                    "tx_unid": r["unid"],
                    "tx_hash": None,
                    "wallet_name": r["wallet_name"],
                    "to_address": r["to_addr"],
                    "amount": r["value"],
                    "token": r["token"],
                    "stuck_seconds": stuck_seconds,
                    "next_check_in": "transaction.failed will fire at the 24h mark if not broadcast by then",
                },
            )
            stats["events_emitted"] += 1
        except Exception as e:
            logger.warning(
                "tx_uncertain_sweep: publish failed tx_id=%s err=%s",
                r["id"], e,
            )
    return stats
