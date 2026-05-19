"""Platform master-key auth for `/platform/*` routes.

A second, strictly separate auth-mechanism from the merchant HMAC
(`/v1/*`) and the operator JWT (`/api/*`). This exists so asystem-core's
control plane can provision new merchants (and other platform-level
operations) without us hand-rolling keys via Telegram.

Why a separate channel?

* Blast radius is fundamentally different. Merchant HMAC compromise
  affects ONE merchant. JWT compromise affects ONE operator session.
  Platform master compromise affects the ABILITY TO CREATE merchants
  — which is recoverable: rotate the env var, drop any unexpected
  merchants, no in-flight money is at risk.
* Audit story is fundamentally different. HMAC events tie to a known
  merchant_id; JWT events tie to a user_id. Platform-master events
  tie to "the caller proved knowledge of a shared secret" — we log
  to audit_log with `user_id=NULL` and `details.source='platform_api'`
  so reviewers see them as a distinct class instead of mixed with
  human actions.
* Rotation procedure is fundamentally different. To rotate the master
  key, flip the env var (`ORGON_PLATFORM_MASTER_KEY`) in Coolify and
  reissue to asystem-core. No DB migration, no merchant downtime.

Header shape: `Authorization: Bearer <key>`. NOT the `X-ORGON-*`
headers (those are merchant HMAC). NOT a JWT. The token is opaque
random bytes — we compare with `hmac.compare_digest` to keep
constant-time comparison guarantees.

Failure modes are explicit:
* env var missing → 503 with a hint (not 500 — operator clearly sees
  this is a deploy config issue, not a code bug)
* Authorization header missing or malformed → 401
* Bearer token doesn't match → 401 (no hint about which side is wrong)
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("orgon.middleware.platform_master")

PLATFORM_PREFIX = "/platform/"
ENV_KEY = "ORGON_PLATFORM_MASTER_KEY"


def _resolve_master_key() -> str:
    """Read the master key from env. Empty string when unconfigured —
    callers must handle (we surface 503 to the client)."""
    return os.environ.get(ENV_KEY, "").strip()


class PlatformMasterAuthMiddleware(BaseHTTPMiddleware):
    """Gate `/platform/*` routes behind a process-level shared secret.

    Pass-through for every other URL prefix — this middleware is a
    no-op for `/api/*`, `/v1/*`, static, docs, etc.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        if not path.startswith(PLATFORM_PREFIX):
            return await call_next(request)

        master = _resolve_master_key()
        if not master:
            return _json_error(
                503,
                "Platform API is disabled on this deployment. "
                f"Set the {ENV_KEY} env var to enable.",
            )

        auth = request.headers.get("authorization") or ""
        if not auth.lower().startswith("bearer "):
            return _json_error(401, "Bearer token required")

        token = auth[len("Bearer "):].strip()
        if not token:
            return _json_error(401, "Empty Bearer token")

        if not hmac.compare_digest(token.encode(), master.encode()):
            # Deliberately vague — don't leak which side is wrong.
            logger.warning("platform-master auth rejected for %s", path)
            return _json_error(401, "Unauthorized")

        # Pass through. Downstream handlers can read
        # `request.state.platform_master = True` if they ever need
        # to distinguish (they shouldn't — anything mounted under
        # /platform/* is master-gated by definition).
        request.state.platform_master = True
        return await call_next(request)


def _json_error(code: int, detail: str) -> Response:
    import json
    payload = json.dumps({"error": detail, "status": code})
    return Response(payload, status_code=code, media_type="application/json")
