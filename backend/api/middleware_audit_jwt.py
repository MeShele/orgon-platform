"""JWT-side audit middleware.

Captures dashboard mutations (POST/PATCH/PUT/DELETE) made by
JWT-authenticated users and writes one row per request into
`audit_log_b2b` — the same table that `/api/audit/logs` reads
from. This is the only place where UI actions become visible to
auditors; without it the audit endpoint stays empty no matter how
much real activity happens.

Extracted into its own module after we removed the B2B partner
stack (HMAC API, billing, partner CRUD). Audit is the only piece
of that subsystem that's part of the Safina-flow operating layer,
so it survives independently.
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class JwtAuditMiddleware(BaseHTTPMiddleware):
    """Audit JWT-authenticated UI actions into `audit_log_b2b`."""

    # Methods worth logging — read-only requests are excluded.
    _MUTATION_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

    # Paths we intentionally exclude.
    _EXEMPT_PREFIXES = (
        "/api/health",
        "/api/docs",
        "/api/openapi.json",
        "/api/redoc",
        "/api/auth/login",   # logging credentials would be a leak
        "/api/auth/refresh",
        "/api/monitoring",
    )

    def __init__(self, app) -> None:
        super().__init__(app)

    @staticmethod
    def _derive_action(method: str, path: str) -> str:
        """Build an action string like `wallets.post` or `compliance.rules.patch`."""
        clean = path.lstrip("/")
        if clean.startswith("api/v1/"):
            clean = clean[len("api/v1/"):]
        elif clean.startswith("api/"):
            clean = clean[len("api/"):]
        parts = [p for p in clean.split("/") if p and not p.startswith("{")]
        # Drop UUID-ish trailing segments to keep action stable across IDs.
        if parts and (len(parts[-1]) >= 16 or parts[-1].count("-") == 4):
            parts = parts[:-1]
        return ".".join([*parts, method.lower()]) if parts else method.lower()

    @staticmethod
    def _derive_resource_type(path: str) -> Optional[str]:
        """Take the first meaningful path segment as the resource type."""
        clean = path.lstrip("/")
        for prefix in ("api/v1/", "api/"):
            if clean.startswith(prefix):
                clean = clean[len(prefix):]
                break
        parts = clean.split("/")
        return parts[0] if parts and parts[0] else None

    @staticmethod
    def _extract_user_id(request: Request) -> Optional[str]:
        """Pull `user_id` out of the bearer token without raising."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        try:
            from backend.services.auth_service import AuthService
            payload = AuthService.decode_token(token)
            if not payload:
                return None
            uid = payload.get("user_id") or payload.get("sub")
            return str(uid) if uid is not None else None
        except Exception:
            return None

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        method = request.method.upper()

        if method not in self._MUTATION_METHODS:
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        if any(path.startswith(p) for p in self._EXEMPT_PREFIXES):
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)

        # Audit is best-effort — never block or fail the actual response.
        try:
            audit_service = getattr(request.app.state, "audit_service", None)
            if audit_service is None:
                return response

            user_id = self._extract_user_id(request)
            if not user_id:
                return response

            await audit_service.log_action(
                partner_id=None,
                user_id=user_id,
                action=self._derive_action(method, path),
                resource_type=self._derive_resource_type(path),
                resource_id=None,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                request_id=None,
                result="success" if response.status_code < 400 else "failure",
                error_message=None,
                metadata={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "source": "jwt",
                },
            )
        except Exception:
            pass

        return response
