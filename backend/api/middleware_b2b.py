"""
B2B API Middleware
Authentication, rate limiting, and audit logging for Partner API
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from typing import Optional, Dict, Any, Callable
import time
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

# Import services (will be injected via dependency injection)
from backend.services.partner_service import PartnerService
from backend.services.audit_service import AuditService


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Authenticate Partner API requests using API Key + Secret.
    
    Expects headers:
        X-API-Key: <api_key>
        X-API-Secret: <api_secret>
    
    On success, adds partner context to request.state:
        request.state.partner_id
        request.state.partner_tier
        request.state.partner_name
    """
    
    def __init__(
        self,
        app,
        exempt_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/redoc", "/api/docs", "/api/openapi.json", "/api/redoc"]
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Allow CORS preflight requests through without auth
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip authentication for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Only authenticate Partner API routes
        if not request.url.path.startswith("/api/v1/partner"):
            return await call_next(request)
        
        # Get services from app.state
        if not hasattr(request.app.state, "partner_service") or not hasattr(request.app.state, "audit_service_b2b"):
            # B2B services not initialized (SQLite mode or not configured)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "service_unavailable",
                    "message": "B2B Platform services not available (requires PostgreSQL)"
                }
            )
        
        partner_service = request.app.state.partner_service
        audit_service = request.app.state.audit_service_b2b
        
        # Allow JWT Bearer token auth (for dashboard/frontend access to partner routes)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Extract API credentials from headers
        api_key = request.headers.get("X-API-Key")
        api_secret = request.headers.get("X-API-Secret")

        if not api_key or not api_secret:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "missing_credentials",
                    "message": "X-API-Key and X-API-Secret headers are required"
                }
            )
        
        # Authenticate partner
        partner = await partner_service.get_partner_by_api_key(api_key)
        
        if not partner:
            await audit_service.log_action(
                partner_id=None,
                user_id=None,
                action="auth.failed",
                result="failure",
                error_message="Invalid API key",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                metadata={"api_key_prefix": api_key[:8]}
            )
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "invalid_credentials",
                    "message": "Invalid API key or secret"
                }
            )
        
        # Verify API secret
        if not partner_service.verify_api_secret(api_secret, partner["api_secret_hash"]):
            await audit_service.log_action(
                partner_id=str(partner["id"]),
                user_id=partner["ec_address"],
                action="auth.failed",
                result="failure",
                error_message="Invalid API secret",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent")
            )
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "invalid_credentials",
                    "message": "Invalid API key or secret"
                }
            )
        
        # Check partner status
        if partner["status"] != "active":
            await audit_service.log_action(
                partner_id=str(partner["id"]),
                user_id=partner["ec_address"],
                action="auth.rejected",
                result="failure",
                error_message=f"Partner status: {partner['status']}",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent")
            )
            
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "account_suspended",
                    "message": f"Account is {partner['status']}"
                }
            )
        
        # ─── Replay protection ─────────────────────────────────────
        # Strict by default, can be turned off via ORGON_PARTNER_REPLAY_OFF=1
        # during incidents. Demands two extra headers:
        #   X-Nonce       — random per-request token, ≤128 chars
        #   X-Timestamp   — Unix seconds (server checks ±5 min drift)
        # The (partner_id, nonce) insert is what actually blocks replays —
        # the partial UNIQUE index in migration 023 is the source of truth.
        import os as _os
        if _os.getenv("ORGON_PARTNER_REPLAY_OFF", "").lower() not in {"1", "true", "yes"}:
            nonce = (request.headers.get("X-Nonce") or "").strip()
            ts_hdr = (request.headers.get("X-Timestamp") or "").strip()

            if not nonce or not ts_hdr:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "missing_replay_headers",
                        "message": "X-Nonce and X-Timestamp headers are required for replay protection",
                    },
                )
            if len(nonce) > 128:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "nonce_too_long", "message": "X-Nonce must be ≤128 chars"},
                )

            import time as _time
            try:
                client_ts = int(ts_hdr)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "bad_timestamp", "message": "X-Timestamp must be Unix seconds (integer)"},
                )

            drift = abs(int(_time.time()) - client_ts)
            if drift > 300:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "timestamp_drift",
                        "message": f"X-Timestamp is off by {drift}s — must be within 5 min of server time",
                    },
                )

            # Atomic insert — if (partner_id, nonce) already exists, this is a replay.
            # The DB-side PK is the canonical guarantee; in-memory checks would race.
            try:
                replayed = await _record_partner_nonce(
                    request.app, partner_id=str(partner["id"]), nonce=nonce
                )
            except Exception:
                # Don't block traffic on infra glitch — log and allow.
                # (Real prod: surface to Sentry, but never lock partners out
                # because of a transient asyncpg blip.)
                import logging as _logging
                _logging.getLogger("orgon.api.b2b").exception(
                    "Nonce check infra error — allowing through"
                )
                replayed = False

            if replayed:
                await audit_service.log_action(
                    partner_id=str(partner["id"]),
                    user_id=partner["ec_address"],
                    action="auth.replay",
                    result="failure",
                    error_message=f"nonce reused: {nonce[:16]}…",
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                )
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={
                        "error": "nonce_reused",
                        "message": "This X-Nonce has already been used for your account",
                    },
                )

        # Attach partner context to request
        request.state.partner_id = str(partner["id"])
        request.state.partner_tier = partner["tier"]
        request.state.partner_name = partner["name"]
        request.state.partner_ec_address = partner["ec_address"]
        request.state.rate_limit = partner["rate_limit_per_minute"]

        # Continue with request
        return await call_next(request)


async def _record_partner_nonce(app, partner_id: str, nonce: str) -> bool:
    """Insert (partner_id, nonce, now). Returns True if it was a replay
    (PK conflict), False if accepted."""
    from backend.main import get_database
    db = get_database()
    if db is None:
        # No DB wired (test harness?) — don't lock partners out.
        return False
    try:
        await db.execute(
            "INSERT INTO partner_request_nonces (partner_id, nonce) VALUES ($1, $2)",
            (partner_id, nonce),
        )
        return False
    except Exception as exc:
        # asyncpg.UniqueViolationError stringifies to a message containing
        # "duplicate key" — match without importing the exception class
        # (the pool wraps in our own AsyncDatabase facade).
        if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
            return True
        raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit Partner API requests based on tier limits.
    
    Uses sliding window algorithm with in-memory tracking.
    For production, consider Redis for distributed rate limiting.
    """
    
    def __init__(
        self,
        app,
        window_seconds: int = 60,
        exempt_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/redoc", "/api/docs", "/api/openapi.json", "/api/redoc"]
        
        # In-memory request tracking: {partner_id: [(timestamp, endpoint), ...]}
        self.request_log: Dict[str, list] = defaultdict(list)
        
        # Cleanup task
        self.cleanup_task = None
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Only rate limit Partner API routes
        if not request.url.path.startswith("/api/v1/partner"):
            return await call_next(request)
        
        # Partner context must be set by APIKeyAuthMiddleware
        if not hasattr(request.state, "partner_id"):
            # Auth middleware should have rejected already, but double-check
            return await call_next(request)
        
        partner_id = request.state.partner_id
        rate_limit = request.state.rate_limit
        endpoint = request.url.path
        now = time.time()
        
        # Clean old requests outside window
        cutoff = now - self.window_seconds
        self.request_log[partner_id] = [
            (ts, ep) for ts, ep in self.request_log[partner_id]
            if ts > cutoff
        ]
        
        # Count requests in current window
        current_count = len(self.request_log[partner_id])
        
        # Check if over limit
        if current_count >= rate_limit:
            # Calculate retry-after time
            oldest_timestamp = min(ts for ts, _ in self.request_log[partner_id])
            retry_after = int(oldest_timestamp + self.window_seconds - now) + 1
            
            # Get audit service from app.state
            if hasattr(request.app.state, "audit_service_b2b"):
                audit_service = request.app.state.audit_service_b2b
                
                # Log rate limit exceeded
                await audit_service.log_action(
                    partner_id=partner_id,
                    user_id=request.state.partner_ec_address,
                    action="rate_limit.exceeded",
                    result="failure",
                    error_message=f"Rate limit {rate_limit}/min exceeded",
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    metadata={
                        "endpoint": endpoint,
                        "current_count": current_count,
                        "limit": rate_limit
                    }
                )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded: {rate_limit} requests per minute",
                    "retry_after_seconds": retry_after,
                    "tier": request.state.partner_tier
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add current request to log
        self.request_log[partner_id].append((now, endpoint))
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Calculate remaining requests
        remaining = rate_limit - current_count - 1
        
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))
        
        return response
    
    def start_cleanup_task(self):
        """Start background task to clean old request logs."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def _periodic_cleanup(self):
        """Periodically clean old entries from request log."""
        while True:
            await asyncio.sleep(60)  # Clean every minute
            now = time.time()
            cutoff = now - self.window_seconds * 2  # Keep 2x window for safety
            
            for partner_id in list(self.request_log.keys()):
                self.request_log[partner_id] = [
                    (ts, ep) for ts, ep in self.request_log[partner_id]
                    if ts > cutoff
                ]
                
                # Remove empty logs
                if not self.request_log[partner_id]:
                    del self.request_log[partner_id]


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all Partner API requests to audit trail.
    
    Captures request details and response status for compliance.
    """
    
    def __init__(
        self,
        app,
        exempt_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/redoc", "/api/docs", "/api/openapi.json", "/api/redoc"]
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip audit for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Only audit Partner API routes
        if not request.url.path.startswith("/api/v1/partner"):
            return await call_next(request)
        
        # Generate request ID for correlation
        request_id = f"{int(time.time() * 1000)}-{id(request)}"
        
        # Capture request start time
        start_time = time.time()
        
        # Get audit service from app.state
        audit_service = None
        if hasattr(request.app.state, "audit_service_b2b"):
            audit_service = request.app.state.audit_service_b2b
        
        # Process request
        try:
            response = await call_next(request)
            
            # Determine result based on status code
            result = "success" if response.status_code < 400 else "failure"
            error_message = None
            
            # Log to audit trail
            if audit_service and hasattr(request.state, "partner_id"):
                await audit_service.log_action(
                    partner_id=request.state.partner_id,
                    user_id=request.state.partner_ec_address,
                    action=f"api.{request.method.lower()}.{request.url.path.split('/')[-1]}",
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    request_id=request_id,
                    result=result,
                    error_message=error_message,
                    metadata={
                        "method": request.method,
                        "path": str(request.url.path),
                        "query": str(request.url.query),
                        "status_code": response.status_code,
                        "duration_ms": int((time.time() - start_time) * 1000)
                    }
                )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            # Log exception to audit trail
            if audit_service and hasattr(request.state, "partner_id"):
                await audit_service.log_action(
                    partner_id=request.state.partner_id,
                    user_id=request.state.partner_ec_address,
                    action=f"api.{request.method.lower()}.{request.url.path.split('/')[-1]}",
                    ip_address=request.client.host,
                    user_agent=request.headers.get("user-agent"),
                    request_id=request_id,
                    result="failure",
                    error_message=str(e),
                    metadata={
                        "method": request.method,
                        "path": str(request.url.path),
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "exception_type": type(e).__name__
                    }
                )
            
            raise  # Re-raise exception for FastAPI error handling


# ============================================================================
# JWT AUDIT MIDDLEWARE
# ============================================================================


class JwtAuditMiddleware(BaseHTTPMiddleware):
    """Audit JWT-authenticated UI actions into `audit_log_b2b`.

    The B2B `AuditLoggingMiddleware` only captures `/api/v1/partner/*`
    routes (HMAC-signed partner API). UI endpoints used by the
    dashboard (JWT bearer auth) had no audit trail — meaning
    `/api/audit/logs` returned 0 even after login + wallet create +
    send transaction. This middleware closes that gap by inspecting
    the bearer token after the response is produced and writing one
    audit row per mutation (POST/PATCH/PUT/DELETE) to the same table
    `/api/audit/logs` reads from.

    Conservative scope:
    - Only mutation methods are logged. GETs are noisy and would
      drown the log without telling auditors anything new.
    - Read errors / decode failures are swallowed — auditing must
      never break the actual request.
    - Skipped: B2B partner paths (have their own audit), health/docs.
    """

    # Methods worth logging — read-only requests are excluded.
    _MUTATION_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

    # Paths we intentionally exclude.
    _EXEMPT_PREFIXES = (
        "/api/health",
        "/api/docs",
        "/api/openapi.json",
        "/api/redoc",
        "/api/v1/partner",  # has its own AuditLoggingMiddleware
        "/api/auth/login",  # logging credentials would be a leak
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
            # Local import to avoid pulling auth_service at module-init time.
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

        # Fast-paths: only audit mutations on /api/* (UI) and skip exempts.
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
            audit_service = getattr(request.app.state, "audit_service", None) \
                or getattr(request.app.state, "audit_service_b2b", None)
            if audit_service is None:
                return response

            user_id = self._extract_user_id(request)
            # Skip anonymous mutations entirely — they will already 401/403
            # at the route layer, and "anon" rows in audit add noise.
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
            # Last-resort: never let audit failure surface to the client.
            pass

        return response


# ============================================================================
# DEPENDENCY INJECTION HELPERS
# ============================================================================

def get_partner_from_request(request: Request) -> Dict[str, Any]:
    """
    Extract partner context from request state (set by auth middleware).
    Falls back to JWT user context if no partner auth.
    """
    if not hasattr(request.state, "partner_id"):
        # Check if JWT auth was used (frontend dashboard access)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return {
                "partner_id": None,
                "partner_tier": "internal",
                "partner_name": "Dashboard User",
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Partner authentication required"
        )

    return {
        "partner_id": request.state.partner_id,
        "partner_tier": request.state.partner_tier,
        "partner_name": request.state.partner_name,
        "ec_address": request.state.partner_ec_address,
        "rate_limit": request.state.rate_limit
    }
