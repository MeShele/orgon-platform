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
        
        # Attach partner context to request
        request.state.partner_id = str(partner["id"])
        request.state.partner_tier = partner["tier"]
        request.state.partner_name = partner["name"]
        request.state.partner_ec_address = partner["ec_address"]
        request.state.rate_limit = partner["rate_limit_per_minute"]
        
        # Continue with request
        return await call_next(request)


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
