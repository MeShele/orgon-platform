"""Idempotency cache for the public /v1/* surface.

A merchant retrying a half-broken request — dropped connection, 504
from an intermediate proxy, k8s pod cycle on our side — must not end
up creating two transactions, two end-users, two wallets. The contract
is dfns-style:

  POST /v1/transactions
  X-ORGON-Idempotency-Key: 8c1d4f0e-4af3-…

  → first call returns 201 with body B
  → any subsequent call within 24h replays B verbatim,
    regardless of network outcome of the first call

We freeze the response (status + body bytes + selected headers) keyed
by (merchant_id, idem_key). Subsequent lookups return the frozen row
without invoking the route handler.

`request_hash` is recorded but never enforced. If the second call's
body bytes drift (json key reordering, whitespace, encoding round-trip
through a proxy) we log it and replay the original anyway. The
alternative — 409 on mismatch — punishes correct retry semantics.

TTL: 24 hours, set by the row's `expires_at` (server-side default).
Cleanup runs hourly via the scheduler.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("orgon.idempotency")

# Mutating methods we cache. GET/HEAD/OPTIONS are already idempotent
# server-side so caching them via this layer adds no safety.
MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

# Only cache successful responses. 4xx is the caller's bug — let them
# fix it and retry; 5xx is ours, let them retry against a healed server.
def _cacheable_status(status: int) -> bool:
    return 200 <= status < 300


def compute_request_hash(method: str, path: str, body: bytes) -> str:
    """sha256 over the same logical surface the HMAC signs."""
    h = hashlib.sha256()
    h.update(method.upper().encode())
    h.update(b"\n")
    h.update(path.encode())
    h.update(b"\n")
    h.update(body or b"")
    return h.hexdigest()


@dataclass
class CachedResponse:
    status: int
    body: bytes
    headers: dict[str, str]


async def lookup(
    pool,
    *,
    merchant_id: str,
    idem_key: str,
    request_hash: str,
) -> Optional[CachedResponse]:
    """Return the previously frozen response for this key, or None.

    Expired rows are treated as a miss. `request_hash` is compared to
    the one stored at save time — on mismatch we WARN-log and still
    return the cached response (intentional; see module docstring).
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT request_hash, response_status, response_body, response_headers
              FROM merchant_idempotency_keys
             WHERE merchant_id = $1::uuid
               AND idem_key    = $2
               AND expires_at  > now()
            """,
            merchant_id,
            idem_key,
        )
    if not row:
        return None
    if row["request_hash"] != request_hash:
        logger.warning(
            "idempotency request_hash drift merchant=%s key=%s "
            "(replaying original — see idempotency_service docstring)",
            merchant_id,
            idem_key,
        )
    headers = row["response_headers"]
    if isinstance(headers, str):
        try:
            headers = json.loads(headers)
        except Exception:
            headers = {}
    return CachedResponse(
        status=int(row["response_status"]),
        body=bytes(row["response_body"]),
        headers=dict(headers or {}),
    )


async def save(
    pool,
    *,
    merchant_id: str,
    idem_key: str,
    request_hash: str,
    status: int,
    body: bytes,
    headers: dict[str, str],
) -> None:
    """Freeze the response. No-op for non-cacheable statuses.

    If two concurrent first-time calls race, ON CONFLICT DO NOTHING
    means the first writer wins; the loser silently keeps its own
    in-flight response (the caller still gets a valid 2xx, just not
    necessarily byte-equal to a later retry). This is acceptable —
    pathological races are vanishingly rare in practice.
    """
    if not _cacheable_status(status):
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO merchant_idempotency_keys
                (merchant_id, idem_key, request_hash,
                 response_status, response_body, response_headers)
            VALUES ($1::uuid, $2, $3, $4, $5, $6::jsonb)
            ON CONFLICT (merchant_id, idem_key) DO NOTHING
            """,
            merchant_id,
            idem_key,
            request_hash,
            int(status),
            body,
            json.dumps(headers or {}),
        )


async def prune_expired(pool) -> int:
    """Hourly cleanup. Returns count of deleted rows for logging."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM merchant_idempotency_keys WHERE expires_at < now()"
        )
    # asyncpg returns "DELETE <n>"
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0
