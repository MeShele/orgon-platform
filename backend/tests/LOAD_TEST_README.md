# ORGON Partner API - Load Testing

Performance testing for B2B Partner API using Locust.

## Installation

```bash
pip install locust
```

## Quick Start

### 1. Start Backend

```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8890
```

### 2. Run Load Test

**Web UI (Recommended):**
```bash
locust -f backend/tests/load_test.py --host=http://localhost:8890
```

Then open http://localhost:8089 in your browser.

**Command Line:**
```bash
locust -f backend/tests/load_test.py \
  --host=http://localhost:8890 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless
```

## Test Scenarios

The load test simulates realistic Partner API usage:

| Endpoint | Weight | Description |
|----------|--------|-------------|
| GET /wallets | 10 | List wallets (most frequent) |
| GET /transactions | 8 | List transactions |
| GET /wallets/{name} | 5 | Get wallet details |
| GET /addresses | 4 | List saved addresses |
| GET /analytics/volume | 3 | Transaction volume |
| GET /scheduled-transactions | 3 | List scheduled TX |
| GET /webhooks | 2 | List webhooks |
| GET /webhooks/events | 2 | Webhook event log |
| GET /analytics/distribution | 2 | Token distribution |
| GET /networks | 1 | Supported networks |

## Performance Targets

| Metric | Target | Rationale |
|--------|--------|-----------|
| p95 latency | <100ms | Industry standard for API responsiveness |
| Throughput | >50 req/s | Sufficient for 10+ active partners |
| Error rate | <1% | High availability requirement |
| Concurrent users | 100 | Simulates 10-20 active partners (5-10 req/user) |

## Test Configuration

**Users:** 100 concurrent  
**Spawn rate:** 10 users/sec (ramp-up over 10s)  
**Duration:** 5 minutes  
**Think time:** 1-3 seconds between requests

## Running Different Test Scenarios

### Light Load (Development)
```bash
locust -f backend/tests/load_test.py \
  --host=http://localhost:8890 \
  --users 10 \
  --spawn-rate 2 \
  --run-time 1m \
  --headless
```

### Moderate Load (Staging)
```bash
locust -f backend/tests/load_test.py \
  --host=http://localhost:8890 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 3m \
  --headless
```

### Heavy Load (Stress Test)
```bash
locust -f backend/tests/load_test.py \
  --host=http://localhost:8890 \
  --users 200 \
  --spawn-rate 20 \
  --run-time 10m \
  --headless
```

## Interpreting Results

### Good Performance
```
Summary:
  Total requests: 15000
  Failures: 12 (0.08%)
  Avg response time: 45ms
  p50: 38ms
  p95: 87ms
  p99: 142ms
  Requests/sec: 50.2

✅ All targets met!
```

### Poor Performance
```
Summary:
  Total requests: 8000
  Failures: 240 (3.0%)
  Avg response time: 215ms
  p50: 180ms
  p95: 450ms
  p99: 890ms
  Requests/sec: 26.7

❌ Targets not met:
  - p95 > 100ms (450ms)
  - Error rate > 1% (3.0%)
  - RPS < 50 (26.7)
```

## Optimization Tips

If performance is poor:

1. **Database Indexes:**
   - Check query performance: `EXPLAIN ANALYZE <query>`
   - Add indexes on frequently filtered columns

2. **Connection Pool:**
   - Increase PostgreSQL pool size (default: 0-5)
   - Monitor pool utilization

3. **Caching:**
   - Enable Redis for session/price cache
   - Increase cache TTLs

4. **Query Optimization:**
   - Use `SELECT *` sparingly
   - Add pagination limits
   - Batch requests where possible

5. **Async Performance:**
   - Check for blocking I/O
   - Profile with `py-spy`
   - Optimize slow service methods

## Continuous Performance Testing

### GitHub Actions (CI/CD)

```yaml
name: Load Test

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start backend
        run: |
          python3 -m uvicorn backend.main:app --port 8890 &
          sleep 10
      - name: Run load test
        run: |
          pip install locust
          locust -f backend/tests/load_test.py \
            --host=http://localhost:8890 \
            --users 50 \
            --spawn-rate 5 \
            --run-time 2m \
            --headless \
            --csv=results/load_test
      - name: Check results
        run: |
          python3 scripts/check_load_test_results.py results/load_test_stats.csv
```

## Monitoring

For production monitoring, integrate with:

- **Prometheus:** Metrics collection
- **Grafana:** Visualization dashboards
- **Sentry:** Error tracking
- **DataDog/New Relic:** APM

## Troubleshooting

### "Connection refused"
Backend is not running. Start it first:
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8890
```

### "401 Unauthorized"
Check API credentials in `.test_credentials.env` or environment variables:
```bash
export TEST_API_KEY="your_key"
export TEST_API_SECRET="your_secret"
```

### "Too many open files"
Increase file descriptor limit:
```bash
ulimit -n 10000
```

### High p95 latency
Check database query performance:
```sql
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

## Resources

- Locust docs: https://docs.locust.io/
- Performance best practices: /docs/PERFORMANCE.md
- Database optimization: /docs/DATABASE_OPTIMIZATION.md
