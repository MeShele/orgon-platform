"""Auth, CORS, and logging middleware."""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.config import get_config

logger = logging.getLogger("orgon.middleware")


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication for admin endpoints.

    Returns JSONResponse instead of raising HTTPException to avoid
    bypassing outer CORS middleware (known Starlette issue).
    """

    EXEMPT_PATHS = {
        "/api/health", "/docs", "/openapi.json", "/redoc",
        "/api/docs", "/api/openapi.json", "/api/redoc",  # Documentation redirects
        "/api/auth",  # All auth endpoints (login, register, refresh, reset-password, me, roles, users)
        "/api/v1/auth",  # V1 API auth
        "/api/v1/partner",  # Partner API (uses API key auth via separate middleware)
        "/api/debug",  # Debug endpoints (development)
        "/api/v1/billing/plans",  # Public plans listing
        "/api/monitoring",  # Monitoring & metrics (Prometheus)
        "/test/",  # Test endpoints (development only)
        # All API endpoints use JWT auth at route level
        "/api/organizations",  # Organizations - JWT AUTH
        "/api/wallets",  # Wallets - JWT AUTH
        "/api/transactions",  # Transactions - JWT AUTH
        "/api/dashboard",  # Dashboard - JWT AUTH
        "/api/networks",  # Networks - JWT AUTH
        "/api/tokens",  # Tokens - JWT AUTH
        "/api/signatures",  # Signatures - JWT AUTH
        "/api/analytics",  # Analytics - JWT AUTH
        "/api/audit",  # Audit - JWT AUTH
        "/api/billing",  # Billing - JWT AUTH
        "/api/compliance",  # Compliance - JWT AUTH
        "/api/whitelabel",  # White Label - JWT AUTH
        "/api/fiat",  # Fiat - JWT AUTH
        "/api/contacts",  # Contacts - JWT AUTH
        "/api/scheduled",  # Scheduled transactions - JWT AUTH
        "/api/users",  # Users - JWT AUTH
        "/api/2fa",  # 2FA - JWT AUTH
        "/api/export",  # Export - JWT AUTH
        "/export",  # Export (actual prefix) - JWT AUTH
        "/api/webhooks",  # Webhooks - JWT AUTH
        "/api/events",  # Events - JWT AUTH
        "/api/rates",  # Rates - JWT AUTH
        "/api/addresses",  # Address validation - JWT AUTH
        "/api/cache",  # Cache - JWT AUTH
        "/api/v1/billing",  # Billing v1 - JWT AUTH
        "/api/v1/compliance",  # Compliance v1 - JWT AUTH
        "/api/v1/whitelabel",  # White Label v1 - JWT AUTH
        "/api/v1/fiat",  # Fiat v1 - JWT AUTH
        "/api/reports",  # Reports - JWT AUTH
        "/api/support",  # Support tickets - JWT AUTH
        "/api/documents",  # Documents - JWT AUTH
        "/api/v1/kyc-kyb",  # KYC/KYB - JWT AUTH
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        logger.info(f"[AuthMiddleware] Processing path: {path}")

        # Skip auth for CORS preflight
        if request.method == "OPTIONS":
            logger.info(f"[AuthMiddleware] CORS preflight - skipping")
            return await call_next(request)
        
        # DEBUG: Always allow /api/debug
        if path.startswith("/api/debug"):
            logger.info(f"[AuthMiddleware] /api/debug detected - ALLOWING WITHOUT AUTH")
            return await call_next(request)

        # Skip auth for health/docs endpoints
        if any(path.startswith(p) for p in self.EXEMPT_PATHS):
            return await call_next(request)

        # Skip auth for WebSocket (handled separately)
        if path.startswith("/ws"):
            return await call_next(request)

        config = get_config()
        admin_token = config["auth"].get("token", "")

        if not admin_token:
            # No token configured = no auth required (dev mode)
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.error(f"[AuthMiddleware] Missing Bearer token for path: {path}")
            return JSONResponse(
                status_code=401, content={"detail": "Missing Bearer token (AuthMiddleware v2)", "path": path}
            )

        token = auth_header[7:]
        if token != admin_token:
            return JSONResponse(
                status_code=403, content={"detail": "Invalid token"}
            )

        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request timing and status."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        import traceback
        start = time.time()
        try:
            response = await call_next(request)
            duration = (time.time() - start) * 1000

            logger.info(
                "%s %s -> %d (%.1fms)",
                request.method, request.url.path, response.status_code, duration,
            )
            return response
        except Exception as e:
            duration = (time.time() - start) * 1000
            logger.error(f"Exception in {request.method} {request.url.path}: {e}")
            logger.error(traceback.format_exc())
            raise


class RLSMiddleware(BaseHTTPMiddleware):
    """
    Row-Level Security (RLS) Middleware
    Sets tenant context (organization_id, is_super_admin) for PostgreSQL RLS policies
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Extract organization_id from JWT token/session and set tenant context.
        
        Note: This is a placeholder implementation.
        In production, extract organization_id from:
        1. JWT token (preferred)
        2. Session cookie
        3. Request header (X-Organization-ID)
        """
        # TODO: Extract from JWT token
        # For now, use default organization from env or header
        organization_id = request.headers.get("X-Organization-ID")
        is_super_admin = request.headers.get("X-Is-Super-Admin", "false").lower() == "true"
        
        if organization_id:
            # Set tenant context in database connection
            try:
                from backend.main import get_database
                db = get_database()
                
                # Set RLS context for this request
                await db.execute(
                    "SELECT set_tenant_context($1, $2)",
                    params=(organization_id, is_super_admin)
                )
                
                logger.debug(f"RLS context set: org={organization_id}, admin={is_super_admin}")
                
            except Exception as e:
                logger.error(f"Failed to set RLS context: {e}")
        
        # Process request
        response = await call_next(request)
        
        # Clear tenant context after request
        if organization_id:
            try:
                from backend.main import get_database
                db = get_database()
                await db.execute("SELECT clear_tenant_context()")
                logger.debug("RLS context cleared")
            except Exception as e:
                logger.error(f"Failed to clear RLS context: {e}")
        
        return response


def setup_middleware(app):
    """Configure all middleware on the FastAPI app.

    Note: Starlette executes middleware in reverse order of add_middleware calls.
    Last added = outermost (runs first). CORS must be outermost to handle
    preflight and add headers to error responses.
    """
    config = get_config()
    # Safe fallback: explicit known prod / preview / dev origins.
    # Override via CORS_ORIGINS env / config to extend.
    DEFAULT_ORIGINS = [
        "https://orgon.asystem.kg",
        "https://orgon-preview.asystem.kg",
        "http://localhost:3000",
        "http://localhost:3100",
        "http://localhost:3200",
    ]
    origins = config["server"].get("cors_origins") or DEFAULT_ORIGINS
    if origins == ["*"]:
        # Refuse to keep wildcard with credentials — collapse to safe default.
        logger.warning("CORS_ORIGINS=['*'] is unsafe with credentials; falling back to whitelist")
        origins = DEFAULT_ORIGINS

    # Global exception handler: log full stacktrace server-side, return only
    # generic error to client (no stacktrace, no exception type leak).
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback, uuid
        error_id = uuid.uuid4().hex[:12]
        logger.error("Unhandled [%s] on %s %s: %s", error_id, request.method, request.url.path, exc)
        logger.error(traceback.format_exc())
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_id": error_id},
        )
        origin = request.headers.get("origin", "")
        if origin and origin in origins:
            response.headers["access-control-allow-origin"] = origin
            response.headers["access-control-allow-credentials"] = "true"
        return response

    # Request logging (innermost)
    app.add_middleware(RequestLoggingMiddleware)

    # RLS tenant context (after logging, before auth)
    app.add_middleware(RLSMiddleware)

    # Auth (middle)
    app.add_middleware(AuthMiddleware)

    # CORS (outermost — added last so it wraps everything)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
