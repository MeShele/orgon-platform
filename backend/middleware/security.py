"""
Security Middleware
Phase 4.1: Security Hardening
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime, timedelta
from collections import defaultdict
import time


# ============================================
# RATE LIMITING
# ============================================

class RateLimiter:
    """
    Simple in-memory rate limiter
    Production: Use Redis for distributed rate limiting
    """
    
    def __init__(self):
        self.requests = defaultdict(list)  # {ip: [timestamp1, timestamp2, ...]}
    
    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if key has exceeded rate limit
        
        Args:
            key: Client identifier (IP address, user ID, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            True if rate limited, False otherwise
        """
        now = time.time()
        cutoff = now - window_seconds
        
        # Remove old requests outside window
        self.requests[key] = [ts for ts in self.requests[key] if ts > cutoff]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= max_requests:
            return True
        
        # Record this request
        self.requests[key].append(now)
        return False
    
    def cleanup_old_entries(self, max_age_seconds: int = 3600):
        """Remove entries older than max_age to prevent memory growth"""
        now = time.time()
        cutoff = now - max_age_seconds
        
        # Remove keys with no recent requests
        keys_to_remove = [
            key for key, timestamps in self.requests.items()
            if not timestamps or max(timestamps) < cutoff
        ]
        
        for key in keys_to_remove:
            del self.requests[key]


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for API endpoints
    
    Limits:
    - 100 requests/minute per IP (general)
    - 5 login attempts/minute per IP (auth endpoints)
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Different limits for different endpoints
        if request.url.path.startswith("/api/v1/auth/login"):
            # Strict limit for login (prevent brute force)
            if rate_limiter.is_rate_limited(f"login:{client_ip}", max_requests=5, window_seconds=60):
                return Response(
                    content='{"error": "Too many login attempts. Try again in 1 minute."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"}
                )
        
        elif request.url.path.startswith("/api/"):
            # General API limit
            if rate_limiter.is_rate_limited(f"api:{client_ip}", max_requests=100, window_seconds=60):
                return Response(
                    content='{"error": "Rate limit exceeded. Maximum 100 requests per minute."}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"}
                )
        
        # Continue to endpoint
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = "100"
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response


# ============================================
# SECURITY HEADERS
# ============================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    
    Headers:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Strict-Transport-Security: Enforce HTTPS
    - Content-Security-Policy: Restrict resource loading
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS (only if HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # CSP (allow same origin + CDN for assets)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self';"
        )
        
        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(self)"
        )
        
        return response


# ============================================
# HTTPS REDIRECT
# ============================================

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect HTTP to HTTPS in production
    
    Note: Only enable when SSL certificate is configured
    """
    
    def __init__(self, app, enabled: bool = False):
        super().__init__(app)
        self.enabled = enabled
    
    async def dispatch(self, request: Request, call_next):
        if self.enabled and request.url.scheme == "http":
            # Redirect to HTTPS
            url = request.url.replace(scheme="https")
            return Response(
                status_code=307,  # Temporary redirect
                headers={"Location": str(url)}
            )
        
        return await call_next(request)


# ============================================
# FAILED LOGIN TRACKING
# ============================================

class LoginAttemptTracker:
    """
    Track failed login attempts per email/IP
    Lock account after 5 failures (15 min cooldown)
    """
    
    def __init__(self):
        self.attempts = defaultdict(list)  # {email: [(timestamp, ip), ...]}
        self.locked = {}  # {email: unlock_timestamp}
    
    def is_locked(self, email: str) -> bool:
        """Check if account is locked"""
        if email in self.locked:
            unlock_time = self.locked[email]
            if datetime.now() < unlock_time:
                return True
            else:
                # Unlock expired
                del self.locked[email]
                return False
        return False
    
    def record_failure(self, email: str, ip: str):
        """Record failed login attempt"""
        now = datetime.now()
        
        # Add attempt
        self.attempts[email].append((now, ip))
        
        # Remove attempts older than 15 minutes
        cutoff = now - timedelta(minutes=15)
        self.attempts[email] = [
            (ts, ip) for ts, ip in self.attempts[email]
            if ts > cutoff
        ]
        
        # Lock if 5+ failures
        if len(self.attempts[email]) >= 5:
            self.locked[email] = now + timedelta(minutes=15)
    
    def record_success(self, email: str):
        """Clear failed attempts on successful login"""
        if email in self.attempts:
            del self.attempts[email]
        if email in self.locked:
            del self.locked[email]
    
    def get_remaining_cooldown(self, email: str) -> int:
        """Get remaining cooldown seconds"""
        if email in self.locked:
            remaining = (self.locked[email] - datetime.now()).total_seconds()
            return max(0, int(remaining))
        return 0


# Global login tracker
login_tracker = LoginAttemptTracker()


# ============================================
# IP WHITELIST (for withdrawals)
# ============================================

async def check_ip_whitelist(org_id: str, user_ip: str, action: str = "withdrawal") -> bool:
    """
    Check if IP is whitelisted for sensitive actions
    
    Args:
        org_id: Organization ID
        user_ip: User's IP address
        action: Action type (withdrawal, admin, etc.)
    
    Returns:
        True if allowed, False if blocked
    
    Note: Whitelist stored in organization_settings.security_settings JSONB
    Example: {"whitelisted_ips": ["192.168.1.100", "10.0.0.0/24"]}
    """
    # TODO: Implement when withdrawal features added
    # For now, accept all IPs (to be restricted later)
    return True


# ============================================
# AUDIT LOGGING
# ============================================

async def log_security_event(
    event_type: str,
    user_id: str = None,
    org_id: str = None,
    ip_address: str = None,
    user_agent: str = None,
    details: dict = None
):
    """
    Log security-related events
    
    Events:
    - login_success
    - login_failure
    - account_locked
    - withdrawal_request
    - kyc_approval
    - subscription_change
    - suspicious_activity
    
    Note: Logs to audit_logs table (already exists)
    """
    # TODO: Implement when audit logging service added
    # For now, just print to console (development)
    print(f"[SECURITY] {event_type}: user={user_id}, org={org_id}, ip={ip_address}")


# ============================================
# EXPORT
# ============================================

__all__ = [
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "HTTPSRedirectMiddleware",
    "login_tracker",
    "check_ip_whitelist",
    "log_security_event",
]
