# ORGON Platform — Performance Testing Guide

**Last Updated:** 2026-02-12 05:50 GMT+6  
**Version:** 1.0  
**Testing Framework:** k6 (Grafana Load Testing)

---

## Overview

Performance testing ensures ORGON platform can handle production load:
- **Target:** 100+ organizations, 10K+ users
- **Peak Load:** 1000 concurrent users
- **Response Time:** < 500ms (p95)
- **Throughput:** 1000 req/sec

---

## Test Scenarios

### 1. Smoke Test (Baseline)
**Purpose:** Verify system under minimal load  
**Load:** 1 VU, 1 minute  
**Success:** All requests succeed

```javascript
// tests/k6/smoke.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,
  duration: '1m',
};

export default function() {
  // Health check
  let res = http.get('http://localhost:8000/health');
  check(res, { 'status is 200': (r) => r.status === 200 });
  
  sleep(1);
}
```

**Run:** `k6 run tests/k6/smoke.js`

---

### 2. Load Test (Normal Traffic)
**Purpose:** Validate performance under expected load  
**Load:** 100 VUs, 5 minutes  
**Success:** p95 < 500ms, error rate < 1%

```javascript
// tests/k6/load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },   // Ramp-up
    { duration: '3m', target: 100 },  // Stay at 100
    { duration: '1m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% requests < 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
  },
};

const BASE_URL = 'http://localhost:8000';

export default function() {
  // List organizations
  let res = http.get(`${BASE_URL}/api/v1/organizations`, {
    headers: { 'Authorization': 'Bearer test_token' },
  });
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time OK': (r) => r.timings.duration < 500,
  });
  
  sleep(Math.random() * 3);
}
```

**Run:** `k6 run tests/k6/load.js`

---

### 3. Stress Test (Breaking Point)
**Purpose:** Find system limits  
**Load:** Ramp up to 1000 VUs  
**Success:** Identify breaking point, no data corruption

```javascript
// tests/k6/stress.js
export const options = {
  stages: [
    { duration: '2m', target: 200 },
    { duration: '5m', target: 500 },
    { duration: '5m', target: 1000 },  // Push to limit
    { duration: '2m', target: 0 },
  ],
};

// Same test logic as load.js
```

**Run:** `k6 run tests/k6/stress.js`

---

### 4. Spike Test (Sudden Traffic)
**Purpose:** Handle sudden traffic spikes  
**Load:** 0 → 500 → 0 quickly  
**Success:** System recovers, no crashes

```javascript
// tests/k6/spike.js
export const options = {
  stages: [
    { duration: '10s', target: 500 },  // Instant spike
    { duration: '1m', target: 500 },   // Hold
    { duration: '10s', target: 0 },    // Drop
  ],
};
```

---

### 5. Soak Test (Stability)
**Purpose:** Detect memory leaks, resource exhaustion  
**Load:** 100 VUs, 1 hour  
**Success:** No degradation over time

```javascript
// tests/k6/soak.js
export const options = {
  vus: 100,
  duration: '1h',
};
```

---

## API Endpoint Tests

### Organizations API
```javascript
// Test: Create organization (write operation)
export function testCreateOrganization() {
  const payload = JSON.stringify({
    name: `Test Org ${Date.now()}`,
    slug: `test-org-${Date.now()}`,
  });
  
  const res = http.post(`${BASE_URL}/api/v1/organizations`, payload, {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer test_token',
    },
  });
  
  check(res, {
    'created': (r) => r.status === 201,
    'has id': (r) => JSON.parse(r.body).organization.id != null,
  });
}
```

### Billing API
```javascript
// Test: Get invoices (read operation with pagination)
export function testListInvoices() {
  const res = http.get(
    `${BASE_URL}/api/v1/billing/invoices?organization_id=${ORG_ID}&limit=20`,
    { headers: { 'Authorization': 'Bearer test_token' } }
  );
  
  check(res, {
    'status 200': (r) => r.status === 200,
    'has invoices': (r) => JSON.parse(r.body).invoices.length > 0,
  });
}
```

### Compliance API
```javascript
// Test: KYC records
export function testKYCRecords() {
  const res = http.get(
    `${BASE_URL}/api/v1/compliance/kyc?organization_id=${ORG_ID}`,
    { headers: { 'Authorization': 'Bearer test_token' } }
  );
  
  check(res, {
    'status 200': (r) => r.status === 200,
  });
}
```

---

## Database Performance

### Query Performance
```sql
-- Analyze slow queries
EXPLAIN ANALYZE SELECT * FROM organizations WHERE status = 'active';

-- Check indexes
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

### RLS Overhead Test
```python
# backend/tests/test_performance_rls.py
import asyncio
import time
from uuid import uuid4

async def test_rls_overhead():
    """Measure RLS performance impact"""
    
    # Without RLS (direct query)
    start = time.time()
    result = await conn.fetch("SELECT * FROM organizations LIMIT 1000")
    no_rls_time = time.time() - start
    
    # With RLS (set tenant context)
    await conn.execute("SELECT set_config('app.current_user_id', $1, false)", str(uuid4()))
    start = time.time()
    result = await conn.fetch("SELECT * FROM organizations LIMIT 1000")
    rls_time = time.time() - start
    
    overhead = (rls_time - no_rls_time) / no_rls_time * 100
    print(f"RLS Overhead: {overhead:.1f}%")
    
    # Target: < 100% overhead
    assert overhead < 100, f"RLS overhead too high: {overhead}%"
```

---

## Frontend Performance

### Lighthouse Audit
```bash
# Install Lighthouse
npm install -g lighthouse

# Run audit
lighthouse http://localhost:3000 --output html --output-path report.html

# Targets:
# Performance: > 90
# Accessibility: > 90
# Best Practices: > 90
# SEO: > 90
```

### Bundle Size Analysis
```bash
# Next.js bundle analyzer
npm run build
# Check .next/analyze/

# Targets:
# First Load JS: < 200KB
# Page Load Time: < 2s (3G)
```

---

## Benchmarks (Target)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| API Response Time (p50) | < 200ms | TBD | ⏳ |
| API Response Time (p95) | < 500ms | TBD | ⏳ |
| API Response Time (p99) | < 1000ms | TBD | ⏳ |
| Throughput | 1000 req/s | TBD | ⏳ |
| Error Rate | < 0.1% | TBD | ⏳ |
| Database Connections | < 20 | TBD | ⏳ |
| Memory Usage (Backend) | < 512MB | TBD | ⏳ |
| Memory Usage (Frontend) | < 1GB | TBD | ⏳ |
| Frontend FCP | < 1.8s | TBD | ⏳ |
| Frontend LCP | < 2.5s | TBD | ⏳ |

---

## Optimization Strategies

### Backend
1. **Database:**
   - Index foreign keys ✅ (already done)
   - Materialized views for dashboards
   - Connection pooling (asyncpg handles)
   - Query result caching (Redis)

2. **API:**
   - Pagination for all list endpoints ✅
   - Response compression (gzip)
   - HTTP/2 support
   - CDN for static assets

3. **Code:**
   - Async everywhere ✅
   - Batch database operations
   - Lazy loading for heavy queries
   - Profile with `cProfile`

### Frontend
1. **Code Splitting:**
   - Dynamic imports for large components
   - Route-based splitting ✅ (Next.js default)
   - Lazy load below-the-fold content

2. **Caching:**
   - SWR for data fetching ✅
   - Service Worker for offline
   - CDN for static assets

3. **Images:**
   - Next.js Image optimization ✅
   - WebP format
   - Lazy loading
   - Responsive images

---

## Monitoring (Production)

### Metrics to Track
- **Response Time:** p50, p95, p99
- **Throughput:** req/sec
- **Error Rate:** 5xx errors
- **Database:** Query time, connection count
- **Memory:** Heap usage, GC pauses
- **CPU:** Utilization %

### Tools
- **APM:** Sentry (errors + performance)
- **Metrics:** Prometheus + Grafana
- **Logs:** Loki or CloudWatch
- **Uptime:** Pingdom

### Alerts
- p95 response time > 500ms (5 min)
- Error rate > 1% (1 min)
- Database connections > 80% (immediate)
- Memory usage > 80% (5 min)
- Disk usage > 90% (immediate)

---

## Performance Testing Checklist

**Before Testing:**
- [ ] Seed database with realistic data (1000+ orgs, 10K+ users)
- [ ] Configure rate limiting (may interfere with tests)
- [ ] Disable debug logging
- [ ] Use production build

**During Testing:**
- [ ] Monitor CPU/Memory on server
- [ ] Watch database connections
- [ ] Check for errors in logs
- [ ] Record metrics (response time, throughput)

**After Testing:**
- [ ] Analyze results (p95 < 500ms?)
- [ ] Identify bottlenecks (slow queries, N+1 problems)
- [ ] Optimize and re-test
- [ ] Document baseline metrics

---

## Sample k6 Output

```
running (5m00.0s), 000/100 VUs, 30000 complete and 0 interrupted iterations
default ✓ [======================================] 100 VUs  5m0s

     ✓ status is 200
     ✓ response time OK

     checks.........................: 100.00% ✓ 60000      ✗ 0     
     data_received..................: 18 MB   60 kB/s
     data_sent......................: 3.6 MB  12 kB/s
     http_req_blocked...............: avg=1.2ms   min=1µs     med=2µs     max=500ms   p(90)=3µs    p(95)=4µs   
     http_req_connecting............: avg=1.1ms   min=0s      med=0s      max=450ms   p(90)=0s     p(95)=0s    
     http_req_duration..............: avg=150ms   min=50ms    med=120ms   max=1.2s    p(90)=280ms  p(95)=350ms
       { expected_response:true }...: avg=150ms   min=50ms    med=120ms   max=1.2s    p(90)=280ms  p(95)=350ms
     http_req_failed................: 0.00%   ✓ 0          ✗ 30000
     http_req_receiving.............: avg=50µs    min=10µs    med=40µs    max=5ms     p(90)=80µs   p(95)=100µs
     http_req_sending...............: avg=20µs    min=5µs     med=15µs    max=2ms     p(90)=30µs   p(95)=40µs 
     http_req_tls_handshaking.......: avg=0s      min=0s      med=0s      max=0s      p(90)=0s     p(95)=0s    
     http_req_waiting...............: avg=149ms   min=49ms    med=119ms   max=1.2s    p(90)=279ms  p(95)=349ms
     http_reqs......................: 30000   100/s
     iteration_duration.............: avg=3.15s   min=1.05s   med=3.12s   max=6.2s    p(90)=3.28s  p(95)=3.35s
     iterations.....................: 30000   100/s
     vus............................: 100     min=0        max=100
     vus_max........................: 100     min=100      max=100
```

**Analysis:** ✅ PASS
- p95 response time: 350ms (target: < 500ms)
- Error rate: 0% (target: < 1%)
- Throughput: 100 req/s (target: 1000 req/s — need more VUs)

---

**Next Steps:**
1. Run smoke test
2. Optimize slow endpoints
3. Run load test (100 VUs)
4. Run stress test (find breaking point)
5. Document baseline metrics

**Owner:** Forge 🔥  
**Status:** Ready for testing
