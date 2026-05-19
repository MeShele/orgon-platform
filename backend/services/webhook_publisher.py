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
EV_POLICY_TRIGGERED = "policy.triggered"   # rule engine hit with action != 'alert'


async def publish_event(
    pool,
    *,
    merchant_id: str,
    event_type: str,
    payload: dict[str, Any],
    request_id: str | None = None,
) -> str:
    """Persist event for delivery. Returns the delivery id.

    Caller must have already ensured `merchant_id` is the right
    tenant. We deliberately don't include the row's `secret` here —
    the delivery worker reads merchant.webhook_secret at send time,
    so rotating the secret doesn't desync in-flight events.

    `request_id` is the originating `X-Request-Id` of the /v1/* call
    that triggered this event (see RequestIdAndErrorMiddleware). Pass
    None for system-originated events (cron-driven deposits, manual
    admin actions, retries).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO webhook_deliveries
                (merchant_id, event_type, payload,
                 next_retry_at, created_at, originating_request_id)
            VALUES ($1, $2, $3::jsonb, now(), now(), $4)
            RETURNING id::text
            """,
            UUID(merchant_id),
            event_type,
            json.dumps(payload),
            request_id,
        )
    logger.info(
        "webhook queued merchant=%s event=%s delivery=%s req_id=%s",
        merchant_id, event_type, row["id"], request_id or "-",
    )
    return row["id"]
