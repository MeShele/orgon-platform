"""HMAC-signature auth middleware for the public /v1/* API.

Every public merchant call must carry four headers — without them
the request is rejected before any business logic runs:

    X-ORGON-Key:        <key_pub>          # from merchant_api_keys
    X-ORGON-Timestamp:  <unix ms>          # ±60s server clock drift
    X-ORGON-Nonce:      <uuid v4>          # unique per (key_pub)
    X-ORGON-Signature:  hex(HMAC-SHA256(secret, msg))

`msg` is the byte string:

    f"{ts}\\n{nonce}\\n{method}\\n{path}\\n".encode() + raw_body

Body is the exact bytes the client sent; we do NOT re-serialize JSON
or apply any normalization, so a one-page spec in any language is
enough to reproduce.

Replay protection: (key_pub, nonce) is stored in
merchant_request_nonces. A repeat insert raises and the request is
rejected. The scheduler prunes nonces older than the drift window
plus a safety margin (hourly).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.services import merchant_api_keys as keysvc

logger = logging.getLogger("orgon.middleware.merchant_hmac")

HMAC_TIMESTAMP_TOLERANCE_MS = 60_000  # ±60s drift accepted
PUBLIC_API_PREFIX = "/v1/"
# Paths exempt from HMAC — purely informational, no merchant state.
PUBLIC_EXEMPT_PATHS = {
    "/v1/health",
    "/v1/networks",
}


class MerchantHMACAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if not path.startswith(PUBLIC_API_PREFIX) or path in PUBLIC_EXEMPT_PATHS:
            return await call_next(request)

        # Read body once; stash on receive() so downstream handlers
        # can still consume it. Otherwise BaseHTTPMiddleware closes the
        # stream and FastAPI errors out.
        body_bytes = await request.body()

        async def _replay():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = _replay  # type: ignore[attr-defined]

        try:
            merchant_id, key_id, scopes = await _verify(request, body_bytes)
        except HTTPException as e:
            return _json_error(e.status_code, e.detail)
        except Exception:
            logger.exception("merchant hmac auth crashed")
            return _json_error(500, "internal auth error")

        request.state.merchant_id = merchant_id
        request.state.merchant_api_key_id = key_id
        request.state.merchant_scopes = scopes
        return await call_next(request)


def _json_error(code: int, detail) -> Response:
    payload = json.dumps(
        {"error": detail if isinstance(detail, str) else "unauthorized", "status": code}
    )
    return Response(payload, status_code=code, media_type="application/json")


def _const_eq(a: str, b: str) -> bool:
    """Constant-time hex compare. We treat both inputs as ascii."""
    try:
        return hmac.compare_digest(a.encode(), b.encode())
    except Exception:
        return False


def _get_pool(request: Request):
    pool = getattr(request.app.state, "db_pool", None)
    if pool is not None:
        return pool
    from backend.main import get_database
    db = get_database()
    return db.pool if db else None


async def _verify(request: Request, body_bytes: bytes) -> tuple[str, str, list[str]]:
    headers = request.headers
    key_pub = headers.get("x-orgon-key")
    ts_raw = headers.get("x-orgon-timestamp")
    nonce = headers.get("x-orgon-nonce")
    sig_hex = headers.get("x-orgon-signature")

    if not (key_pub and ts_raw and nonce and sig_hex):
        raise HTTPException(status_code=401, detail="Missing X-ORGON-* signature headers")

    # 1. Timestamp window.
    try:
        ts_ms = int(ts_raw)
    except ValueError:
        raise HTTPException(status_code=401, detail="X-ORGON-Timestamp must be unix ms integer")
    now_ms = int(time.time() * 1000)
    if abs(now_ms - ts_ms) > HMAC_TIMESTAMP_TOLERANCE_MS:
        raise HTTPException(status_code=401, detail="X-ORGON-Timestamp out of acceptable drift window")

    pool = _get_pool(request)
    if pool is None:
        raise HTTPException(status_code=503, detail="auth backend unavailable")

    # 2. Lookup key + decrypt secret. Includes only non-revoked, non-
    # expired rows; secret_encrypted IS NOT NULL is also checked there.
    key_row = await keysvc.lookup_active_by_pub(pool, key_pub)
    if not key_row:
        raise HTTPException(status_code=401, detail="Unknown or revoked API key")
    secret_plain = key_row.get("secret_plain")
    if not secret_plain:
        # Encrypted column present but decrypt returned NULL → master
        # key wrong or pre-encryption row. Fail closed.
        raise HTTPException(status_code=401, detail="API key secret unreadable; rotate the key")

    # 3. Replay protection: insert (key_pub, nonce) atomically. PRIMARY
    # KEY collision means we've seen this nonce before for that key.
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO merchant_request_nonces (key_pub, nonce) VALUES ($1, $2)",
                key_pub,
                nonce,
            )
        except Exception:
            raise HTTPException(status_code=401, detail="Replay detected (nonce reused)")

    # 4. Recompute HMAC and constant-time compare. msg shape is part
    # of the public spec — do not change without bumping the version
    # in /docs.
    method = request.method.upper()
    msg = f"{ts_ms}\n{nonce}\n{method}\n{request.url.path}\n".encode() + body_bytes
    expected = hmac.new(secret_plain.encode(), msg, hashlib.sha256).hexdigest()
    if not _const_eq(expected, sig_hex.lower()):
        raise HTTPException(status_code=401, detail="Bad signature")

    # 5. Quota enforcement — if today's api_calls is already at plan
    # ceiling, reject with 429 BEFORE we count this request. Pricing
    # plan is read from organizations.pricing_plan.
    try:
        async with pool.acquire() as conn:
            plan_row = await conn.fetchrow(
                "SELECT pricing_plan FROM organizations WHERE id = $1::uuid",
                key_row["merchant_id"],
            )
        plan = plan_row["pricing_plan"] if plan_row else None
        from backend.services.merchant_billing import is_over_quota, record_api_call
        if await is_over_quota(pool, merchant_id=key_row["merchant_id"], plan=plan, metric="api_calls"):
            raise HTTPException(status_code=429, detail="API daily limit exceeded for current plan")
        await record_api_call(pool, key_row["merchant_id"])
    except HTTPException:
        raise
    except Exception as e:
        logger.debug("quota/usage record failed (non-fatal): %s", e)

    # 6. Update last_used. Best-effort.
    try:
        await keysvc.touch_last_used(pool, key_pub)
    except Exception:
        logger.debug("touch_last_used failed for %s (non-fatal)", key_pub)

    return key_row["merchant_id"], key_row["id"], list(key_row.get("scopes") or [])
