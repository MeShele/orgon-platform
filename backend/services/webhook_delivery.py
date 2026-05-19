"""Webhook delivery worker.

Per tick:
  1. Pick up `webhook_deliveries` rows with delivered_at IS NULL and
     next_retry_at <= now(), oldest first.
  2. For each, look up the merchant's webhook_url + webhook_secret.
     Skip with a permanent error if the merchant has no URL set.
  3. POST the payload signed with HMAC-SHA256(webhook_secret, body),
     headers `X-ORGON-Webhook-Signature` + `X-ORGON-Webhook-Timestamp`.
  4. 2xx → mark delivered_at; non-2xx or exception → bump attempts
     and schedule next_retry_at with exponential backoff (capped).

Retry schedules — both run six attempts then give up. v2 stretches the
tail so a partner with a 6h outage still has the burst-friendly first
two retries plus a wide enough window to recover before we abandon.

  v1 (default; legacy):  30s   2m   10m    1h    6h   6h
  v2 (WEBHOOK_RETRY_V2=1):  1m  12m   2h    8h   24h  24h

We pick at most 50 events per tick so a slow merchant endpoint
can't starve the rest of the queue.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger("orgon.webhook_delivery")

BATCH_SIZE = 50
HTTP_TIMEOUT_S = 8.0
GIVE_UP_ATTEMPTS = 6

# Public, stable. Either schedule MUST sum-tail to <= 31d (retention
# horizon set in 049_webhook_retention.sql) so we never give up on
# a row that will then be reaped before any operator sees the failure.
_RETRY_V1 = {1: 30, 2: 120, 3: 600, 4: 3600, 5: 21_600}            # 30s/2m/10m/1h/6h
_RETRY_V2 = {1: 60, 2: 720, 3: 7200, 4: 28_800, 5: 86_400}         # 1m/12m/2h/8h/24h


def _use_retry_v2() -> bool:
    """Env-flagged so we can roll v2 out per environment without a redeploy."""
    return os.environ.get("WEBHOOK_RETRY_V2", "").lower() in ("1", "true", "yes", "on")


def _backoff_seconds(attempt: int) -> int:
    schedule = _RETRY_V2 if _use_retry_v2() else _RETRY_V1
    return schedule.get(attempt, schedule[5])


async def run_tick(pool) -> dict:
    stats = {"sent_ok": 0, "sent_err": 0, "skipped_no_url": 0, "given_up": 0}

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.id::text, d.merchant_id::text AS merchant_id,
                   d.event_type, d.payload, d.attempts,
                   o.webhook_url, o.webhook_secret
              FROM webhook_deliveries d
              JOIN organizations o ON o.id = d.merchant_id
             WHERE d.delivered_at IS NULL
               AND (d.next_retry_at IS NULL OR d.next_retry_at <= now())
               AND d.attempts < $1
             ORDER BY d.created_at ASC
             LIMIT $2
            """,
            GIVE_UP_ATTEMPTS,
            BATCH_SIZE,
        )

    if not rows:
        return stats

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
        for r in rows:
            await _deliver_one(pool, client, r, stats)
    return stats


async def _deliver_one(pool, client: httpx.AsyncClient, r, stats: dict) -> None:
    merchant_id = r["merchant_id"]
    delivery_id = r["id"]
    url = (r["webhook_url"] or "").strip()
    secret = r["webhook_secret"] or ""

    if not url:
        # Permanent skip — merchant hasn't configured a URL yet.
        # Mark as given-up so we stop polling this row.
        await _give_up(pool, delivery_id, reason="No webhook_url configured")
        stats["skipped_no_url"] += 1
        return

    body_obj = {
        "id": delivery_id,
        "type": r["event_type"],
        "merchant_id": merchant_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": _parse_payload(r["payload"]),
    }
    body = json.dumps(body_obj, separators=(",", ":"), sort_keys=True).encode()
    ts_ms = int(time.time() * 1000)
    sig = hmac.new(
        secret.encode() if secret else b"",
        f"{ts_ms}\n".encode() + body,
        hashlib.sha256,
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-ORGON-Webhook-Timestamp": str(ts_ms),
        "X-ORGON-Webhook-Signature": sig,
        # Stable identifier of this *delivery attempt sequence*. Same
        # value across retries — consumer dedupes on it for exactly-once.
        # Both header names emit the same value; -Event-Id is the
        # public name going forward, -Id stays as a legacy alias.
        "X-ORGON-Webhook-Event-Id": delivery_id,
        "X-ORGON-Webhook-Id": delivery_id,
        "X-ORGON-Webhook-Event": r["event_type"],
        "User-Agent": "Orgon-Webhook/1.0",
    }

    try:
        resp = await client.post(url, headers=headers, content=body)
        status = resp.status_code
        ok = 200 <= status < 300
    except Exception as e:
        status = 0
        ok = False
        err = str(e)[:300]
    else:
        err = None if ok else (resp.text[:300] if resp.text else f"http {status}")

    if ok:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE webhook_deliveries
                   SET delivered_at = now(),
                       attempts     = attempts + 1,
                       last_status  = $2,
                       last_error   = NULL,
                       next_retry_at = NULL
                 WHERE id = $1
                """,
                _uuid(delivery_id),
                status,
            )
        stats["sent_ok"] += 1
        return

    next_attempt = (r["attempts"] or 0) + 1
    if next_attempt >= GIVE_UP_ATTEMPTS:
        await _give_up(pool, delivery_id, reason=err or "max attempts reached", last_status=status)
        stats["given_up"] += 1
        return

    next_retry = datetime.now(timezone.utc) + timedelta(seconds=_backoff_seconds(next_attempt))
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE webhook_deliveries
               SET attempts      = $2,
                   last_status   = $3,
                   last_error    = $4,
                   next_retry_at = $5
             WHERE id = $1
            """,
            _uuid(delivery_id),
            next_attempt,
            status,
            err,
            next_retry,
        )
    stats["sent_err"] += 1


def _parse_payload(p):
    if isinstance(p, dict):
        return p
    if isinstance(p, (bytes, str)):
        try:
            return json.loads(p)
        except Exception:
            return {}
    return {}


def _uuid(s: str):
    from uuid import UUID
    return UUID(s)


async def _give_up(pool, delivery_id: str, *, reason: str, last_status: int = 0) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE webhook_deliveries
               SET attempts      = $2,
                   last_status   = $3,
                   last_error    = $4,
                   next_retry_at = NULL
             WHERE id = $1
            """,
            _uuid(delivery_id),
            GIVE_UP_ATTEMPTS,
            last_status,
            reason,
        )
