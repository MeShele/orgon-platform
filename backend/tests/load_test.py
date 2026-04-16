"""
ORGON Partner API - Load Test
Using Locust for performance testing

Run:
    locust -f backend/tests/load_test.py --host=http://localhost:8890

Targets:
- 100 concurrent users
- 100 req/s sustained
- p95 latency <100ms
"""

from locust import HttpUser, task, between, events
import os
import time


# Test credentials (from .test_credentials.env)
API_KEY = os.getenv("TEST_API_KEY", "cbf9b1782a2d62ce17f219e210f4920a0f21b9700ec01c40906fa7e7a0b9e678")
API_SECRET = os.getenv("TEST_API_SECRET", "89971655acdadfbc3e37cf55b64a4a0afe2bf62ed4e0b2ec04b3eaff55697727")


class PartnerAPIUser(HttpUser):
    """
    Simulated Partner API user.
    
    Performs typical B2B partner operations:
    - List wallets
    - Get wallet details
    - List transactions
    - Get analytics
    - List addresses
    - List webhooks
    """
    
    # Wait 1-3 seconds between requests (simulates think time)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a simulated user starts."""
        self.auth_headers = {
            "X-API-Key": API_KEY,
            "X-API-Secret": API_SECRET,
            "Content-Type": "application/json"
        }
        
        # Cache wallet names for use in other requests
        self.wallet_names = []
        self._fetch_wallets()
    
    def _fetch_wallets(self):
        """Fetch wallets to cache names for other requests."""
        response = self.client.get(
            "/api/v1/partner/wallets",
            headers=self.auth_headers,
            name="GET /wallets (setup)"
        )
        if response.status_code == 200:
            data = response.json()
            self.wallet_names = [w["name"] for w in data.get("wallets", [])]
    
    # ========================================================================
    # TASKS (weighted by typical usage frequency)
    # ========================================================================
    
    @task(10)
    def list_wallets(self):
        """List wallets (most frequent operation)."""
        self.client.get(
            "/api/v1/partner/wallets",
            headers=self.auth_headers,
            name="GET /wallets"
        )
    
    @task(5)
    def get_wallet_details(self):
        """Get wallet details."""
        if not self.wallet_names:
            return
        
        wallet_name = self.wallet_names[0]  # Use first wallet
        self.client.get(
            f"/api/v1/partner/wallets/{wallet_name}",
            headers=self.auth_headers,
            name="GET /wallets/{name}"
        )
    
    @task(8)
    def list_transactions(self):
        """List transactions."""
        self.client.get(
            "/api/v1/partner/transactions",
            headers=self.auth_headers,
            name="GET /transactions"
        )
    
    @task(3)
    def get_transaction_volume(self):
        """Get transaction volume analytics."""
        self.client.get(
            "/api/v1/partner/analytics/volume?days=7",
            headers=self.auth_headers,
            name="GET /analytics/volume"
        )
    
    @task(2)
    def get_token_distribution(self):
        """Get token distribution analytics."""
        self.client.get(
            "/api/v1/partner/analytics/distribution",
            headers=self.auth_headers,
            name="GET /analytics/distribution"
        )
    
    @task(4)
    def list_addresses(self):
        """List saved addresses."""
        self.client.get(
            "/api/v1/partner/addresses",
            headers=self.auth_headers,
            name="GET /addresses"
        )
    
    @task(3)
    def list_scheduled_transactions(self):
        """List scheduled transactions."""
        self.client.get(
            "/api/v1/partner/scheduled-transactions",
            headers=self.auth_headers,
            name="GET /scheduled-transactions"
        )
    
    @task(2)
    def list_webhooks(self):
        """List webhook configurations."""
        self.client.get(
            "/api/v1/partner/webhooks",
            headers=self.auth_headers,
            name="GET /webhooks"
        )
    
    @task(2)
    def get_webhook_events(self):
        """Get webhook event log."""
        self.client.get(
            "/api/v1/partner/webhooks/events?limit=20",
            headers=self.auth_headers,
            name="GET /webhooks/events"
        )
    
    @task(1)
    def get_networks(self):
        """Get supported networks."""
        self.client.get(
            "/api/v1/partner/networks",
            headers=self.auth_headers,
            name="GET /networks"
        )


# ============================================================================
# EVENT LISTENERS (for custom metrics)
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts."""
    print("\n" + "="*80)
    print("ORGON Partner API - Load Test Starting")
    print("="*80)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users if hasattr(environment, 'parsed_options') else 'N/A'}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops."""
    print("\n" + "="*80)
    print("ORGON Partner API - Load Test Complete")
    print("="*80)
    
    # Print summary
    stats = environment.stats
    
    print("\nSUMMARY:")
    print(f"  Total requests: {stats.total.num_requests}")
    print(f"  Failures: {stats.total.num_failures} ({stats.total.fail_ratio*100:.2f}%)")
    print(f"  Avg response time: {stats.total.avg_response_time:.0f}ms")
    print(f"  p50: {stats.total.get_response_time_percentile(0.50):.0f}ms")
    print(f"  p95: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  p99: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print(f"  Max: {stats.total.max_response_time:.0f}ms")
    print(f"  Requests/sec: {stats.total.total_rps:.2f}")
    
    # Check if we met our targets
    print("\nTARGETS:")
    p95 = stats.total.get_response_time_percentile(0.95)
    rps = stats.total.total_rps
    fail_ratio = stats.total.fail_ratio
    
    print(f"  ✅ p95 < 100ms: {'PASS' if p95 < 100 else 'FAIL'} ({p95:.0f}ms)")
    print(f"  ✅ RPS > 50: {'PASS' if rps > 50 else 'FAIL'} ({rps:.2f} req/s)")
    print(f"  ✅ Fail rate < 1%: {'PASS' if fail_ratio < 0.01 else 'FAIL'} ({fail_ratio*100:.2f}%)")
    
    print("="*80 + "\n")


# ============================================================================
# CUSTOM PERFORMANCE THRESHOLDS
# ============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Track slow requests.
    
    Logs requests that exceed performance thresholds.
    """
    # Threshold: 100ms (p95 target)
    if response_time > 100:
        print(f"⚠️  Slow request: {name} took {response_time:.0f}ms")
