"""
Prometheus Metrics Service
Exposes metrics for monitoring and alerting
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time


# ============================================================================
# HTTP REQUEST METRICS
# ============================================================================

# Total HTTP requests by method, endpoint, and status
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# HTTP request duration (histogram for percentiles)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

# Active database connections
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

# Database query duration
db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# ============================================================================
# WEBHOOK METRICS
# ============================================================================

# Webhook queue size (pending deliveries)
webhook_queue_size = Gauge(
    'webhook_queue_size',
    'Number of webhooks in retry queue'
)

# Webhook delivery attempts
webhook_delivery_attempts_total = Counter(
    'webhook_delivery_attempts_total',
    'Total webhook delivery attempts',
    ['partner_id', 'event_type', 'status']
)

# Webhook delivery failures
webhook_delivery_failures_total = Counter(
    'webhook_delivery_failures_total',
    'Total webhook delivery failures',
    ['partner_id', 'event_type']
)

# ============================================================================
# PARTNER API METRICS
# ============================================================================

# Partner API requests
partner_api_requests_total = Counter(
    'partner_api_requests_total',
    'Total Partner API requests',
    ['partner_id', 'endpoint', 'status']
)

# Partner API errors
partner_api_errors_total = Counter(
    'partner_api_errors_total',
    'Total Partner API errors',
    ['partner_id', 'endpoint', 'error_type']
)

# Rate limit hits
rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['partner_id', 'tier']
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# Total wallets created
wallets_created_total = Counter(
    'wallets_created_total',
    'Total wallets created',
    ['partner_id', 'network_id']
)

# Total transactions processed
transactions_processed_total = Counter(
    'transactions_processed_total',
    'Total transactions processed',
    ['partner_id', 'network_id', 'status']
)

# Active wallets (gauge)
active_wallets_total = Gauge(
    'active_wallets_total',
    'Total active wallets',
    ['partner_id']
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def track_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track HTTP request metrics."""
    http_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status=status_code
    ).inc()
    
    http_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def track_partner_request(partner_id: str, endpoint: str, status_code: int):
    """Track Partner API request."""
    partner_api_requests_total.labels(
        partner_id=partner_id,
        endpoint=endpoint,
        status=status_code
    ).inc()


def track_partner_error(partner_id: str, endpoint: str, error_type: str):
    """Track Partner API error."""
    partner_api_errors_total.labels(
        partner_id=partner_id,
        endpoint=endpoint,
        error_type=error_type
    ).inc()


def track_rate_limit_hit(partner_id: str, tier: str):
    """Track rate limit hit."""
    rate_limit_hits_total.labels(
        partner_id=partner_id,
        tier=tier
    ).inc()


def track_wallet_created(partner_id: str, network_id: int):
    """Track wallet creation."""
    wallets_created_total.labels(
        partner_id=partner_id,
        network_id=network_id
    ).inc()


def track_transaction(partner_id: str, network_id: int, status: str):
    """Track transaction processing."""
    transactions_processed_total.labels(
        partner_id=partner_id,
        network_id=network_id,
        status=status
    ).inc()


def update_db_connections(count: int):
    """Update active database connections gauge."""
    db_connections_active.set(count)


def update_webhook_queue_size(count: int):
    """Update webhook queue size gauge."""
    webhook_queue_size.set(count)


def track_webhook_delivery(partner_id: str, event_type: str, status: str):
    """Track webhook delivery attempt."""
    webhook_delivery_attempts_total.labels(
        partner_id=partner_id,
        event_type=event_type,
        status=status
    ).inc()
    
    if status == "failed":
        webhook_delivery_failures_total.labels(
            partner_id=partner_id,
            event_type=event_type
        ).inc()


def get_metrics() -> Response:
    """
    Generate Prometheus metrics response.
    
    Returns:
        Response with metrics in Prometheus format
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# MIDDLEWARE HELPER
# ============================================================================

class MetricsMiddleware:
    """
    FastAPI middleware to track HTTP request metrics.
    
    Usage:
        app.add_middleware(MetricsMiddleware)
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        
        # Track request
        method = scope["method"]
        path = scope["path"]
        
        # Call next middleware/route
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code = message["status"]
                duration = time.time() - start_time
                
                # Track metrics
                track_http_request(method, path, status_code, duration)
            
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
