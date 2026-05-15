"""Webhook event publishing — INSERT side of the delivery pipeline.

Business code calls `publish_event(...)` whenever something
merchant-observable happens (new deposit, tx confirmed, …). We
persist the event into `webhook_deliveries` with attempts=0 and
next_retry_at=now() so the delivery worker (separate module) picks
it up on the next tick.

Decoupling publish from delivery keeps the hot path fast — `publish`
is a single INSERT — and survives backend restarts because the queue
is the DB, not in-process memory.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("orgon.webhook_publisher")

# Canonical event type strings — keep stable, merchants build
# subscriptions on these. New types append; never rename.
EV_WALLET_ACTIVATED = "wallet.activated"
EV_WALLET_DEPOSIT = "wallet.deposit.detected"
EV_TX_BROADCASTED = "transaction.broadcasted"
EV_TX_CONFIRMED = "transaction.confirmed"
EV_TX_FAILED = "transaction.failed"
EV_USER_CREATED = "user.created"


async def publish_event(
    pool,
    *,
    merchant_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    """Persist event for delivery. Returns the delivery id.

    Caller must have already ensured `merchant_id` is the right
    tenant. We deliberately don't include the row's `secret` here —
    the delivery worker reads merchant.webhook_secret at send time,
    so rotating the secret doesn't desync in-flight events.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO webhook_deliveries
                (merchant_id, event_type, payload, next_retry_at, created_at)
            VALUES ($1, $2, $3::jsonb, now(), now())
            RETURNING id::text
            """,
            UUID(merchant_id),
            event_type,
            json.dumps(payload),
        )
    logger.info(
        "webhook queued merchant=%s event=%s delivery=%s",
        merchant_id, event_type, row["id"],
    )
    return row["id"]
