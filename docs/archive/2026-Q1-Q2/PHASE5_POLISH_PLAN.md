# Phase 5: Polish & Production - PLAN

**Status:** Planning (2026-02-08 06:35 GMT+6)  
**Expected Duration:** 2-2.5 hours (traditional: 2 weeks)  
**Framework:** GOTCHA + ATLAS

---

## 🎯 ATLAS: Architect

### Problem Statement
ASYSTEM B2B Platform (Phases 1-4) is feature-complete but needs production-readiness:
- Security vulnerabilities may exist
- Performance bottlenecks under load
- No monitoring/observability
- Partners need onboarding documentation

### Current State
✅ **Features Complete (Phases 1-4):**
- 28 database tables
- 13 Partner API endpoints
- Authentication (API Key + Secret, bcrypt + SHA256)
- Rate limiting (multi-tier)
- Webhooks with retry logic
- Analytics with USD prices
- Audit logging

❌ **Production Gaps:**
- No security audit (OWASP, injection, XSS, etc.)
- Missing database indexes (N+1 queries)
- No monitoring (uptime, errors, performance)
- No partner documentation
- No migration guide (SQLite → PostgreSQL)

### Success Metrics
1. **Security:** Zero critical vulnerabilities (OWASP Top 10)
2. **Performance:** <100ms API response time (p95) under load
3. **Monitoring:** Real-time alerts for errors/downtime
4. **Documentation:** Partner can onboard in <30 minutes
5. **Production-Ready:** Can deploy to 10+ partners confidently

---

## 🗺️ ATLAS: Trace

### Security Audit Scope

**Authentication & Authorization:**
- [ ] API Key storage (bcrypt'd in DB)
- [ ] API Secret validation (SHA256 pre-hash for >72 bytes)
- [ ] JWT token security (secret rotation, expiry)
- [ ] RBAC enforcement (partner_id isolation)

**Input Validation:**
- [ ] SQL injection protection (parameterized queries only)
- [ ] XSS protection (no HTML in responses)
- [ ] CSRF protection (not applicable for API-only)
- [ ] Rate limit bypass attempts

**Data Protection:**
- [ ] Sensitive data in logs (redact API keys, secrets)
- [ ] Database encryption at rest (Neon.tech default)
- [ ] HTTPS enforcement (Cloudflare Tunnel)
- [ ] Partner data isolation (no cross-partner access)

**Compliance:**
- [ ] Audit log completeness (all Partner API calls)
- [ ] Data retention policy (GDPR/SOC2)
- [ ] Webhook signature verification (HMAC)

### Performance Optimization

**Database Indexes (Missing):**
1. `wallets_b2b(partner_id, created_at DESC)` - List wallets
2. `transactions_b2b(partner_id, created_at DESC)` - List transactions
3. `transactions_b2b(wallet_id, status)` - Wallet transactions
4. `audit_log(partner_id, created_at DESC)` - Audit history
5. `scheduled_transactions_b2b(partner_id, next_run)` - Scheduler
6. `address_book_b2b(partner_id, favorite DESC)` - Address book
7. `webhooks_b2b(status, retry_count, next_retry_at)` - Webhook queue
8. `transaction_analytics(wallet_id, date)` - Analytics queries

**Query Optimization:**
- [ ] Analyze slow queries (pg_stat_statements)
- [ ] Add EXPLAIN ANALYZE for top 10 endpoints
- [ ] Optimize joins (wallets + transactions)
- [ ] Batch operations (bulk insert/update)

**Connection Pooling:**
- [ ] Verify asyncpg pool settings (min=5, max=20)
- [ ] Monitor pool exhaustion
- [ ] Add connection timeout handling

### Monitoring Setup

**Metrics to Track:**
- API response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Request rate (per endpoint)
- Database query time
- Webhook delivery success rate
- Partner API usage (by tier)

**Alerts to Configure:**
- Error rate >5% (5 min window)
- Response time >500ms (p95, 5 min)
- Database connection pool >90% full
- Webhook retry queue >100 items
- Rate limit hit >10 times/min (potential abuse)

**Tools:**
- **Prometheus** (metrics collection)
- **Grafana** (visualization)
- **Loki** (log aggregation, optional)
- **Alertmanager** (alerts via Telegram)

### Documentation Needed

**Partner Onboarding Guide:**
1. Account creation (partner tier selection)
2. API credentials (key + secret generation)
3. Authentication example (curl + Python)
4. Quick start (create wallet, send transaction)
5. Webhook setup (URL + secret)
6. Error handling guide
7. Rate limits per tier
8. Support contact

**Migration Documentation:**
- SQLite → PostgreSQL migration steps
- Data backup/restore procedures
- Environment variables reference
- Deployment checklist

---

## 🔗 ATLAS: Link

### Validation Checklist

**Security:**
- [ ] Run `safety check` (Python vulnerabilities)
- [ ] Run `bandit` (Python security linter)
- [ ] Manual code review (OWASP Top 10)
- [ ] Penetration testing (basic injection attempts)

**Performance:**
- [ ] Load test before/after indexes (100 req/s)
- [ ] Database query analysis (pg_stat_statements)
- [ ] Connection pool monitoring (under load)

**Monitoring:**
- [ ] Prometheus scraping /metrics endpoint
- [ ] Grafana dashboard rendering metrics
- [ ] Test alert delivery (Telegram)

**Documentation:**
- [ ] Partner can follow guide to first API call
- [ ] All endpoints documented (OpenAPI/Swagger)
- [ ] Error codes documented

---

## 🏗️ ATLAS: Assemble

### Implementation Tasks

**Task 1: Security Audit (45 min)**

**Subtasks:**
1. Install security tools:
   ```bash
   pip install safety bandit
   ```
2. Run automated scans:
   ```bash
   safety check --json > security-report.json
   bandit -r backend/ -f json > bandit-report.json
   ```
3. Manual code review:
   - Check API Key handling (middleware_b2b.py)
   - Verify SQL injection protection (all services)
   - Check XSS in responses (no HTML)
   - Verify partner_id isolation (all routes)
4. Create security checklist document

**Task 2: Database Indexes (30 min)**

File: `backend/database/migrations/010_performance_indexes.sql`

```sql
-- Wallet queries
CREATE INDEX idx_wallets_partner_created ON wallets_b2b(partner_id, created_at DESC);
CREATE INDEX idx_wallets_network ON wallets_b2b(network_id, partner_id);

-- Transaction queries
CREATE INDEX idx_transactions_partner_created ON transactions_b2b(partner_id, created_at DESC);
CREATE INDEX idx_transactions_wallet_status ON transactions_b2b(wallet_id, status);
CREATE INDEX idx_transactions_hash ON transactions_b2b(tx_hash) WHERE tx_hash IS NOT NULL;

-- Audit log queries
CREATE INDEX idx_audit_partner_created ON audit_log(partner_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit_log(action, partner_id);

-- Scheduled transactions
CREATE INDEX idx_scheduled_partner_nextrun ON scheduled_transactions_b2b(partner_id, next_run);
CREATE INDEX idx_scheduled_enabled ON scheduled_transactions_b2b(enabled, next_run) WHERE enabled = true;

-- Address book
CREATE INDEX idx_addresses_partner_created ON address_book_b2b(partner_id, created_at DESC);
CREATE INDEX idx_addresses_favorite ON address_book_b2b(partner_id, favorite DESC, created_at DESC);

-- Webhooks
CREATE INDEX idx_webhooks_queue ON webhooks_b2b(status, next_retry_at) WHERE status = 'pending';
CREATE INDEX idx_webhooks_partner ON webhooks_b2b(partner_id, created_at DESC);

-- Analytics
CREATE INDEX idx_analytics_wallet_date ON transaction_analytics(wallet_id, date);
CREATE INDEX idx_analytics_partner_date ON transaction_analytics(partner_id, date) WHERE partner_id IS NOT NULL;
```

**Task 3: Monitoring Setup (45 min)**

**Step 1: Add Prometheus metrics endpoint (15 min)**

File: `backend/services/metrics_service.py`

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])
active_connections = Gauge('db_connections_active', 'Active database connections')
webhook_queue_size = Gauge('webhook_queue_size', 'Webhook retry queue size')
```

Add to middleware:
```python
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

**Step 2: Docker Compose monitoring stack (20 min)**

File: `backend/monitoring/docker-compose.monitoring.yml`

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
  
  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml
    ports:
      - "9093:9093"

volumes:
  prometheus_data:
  grafana_data:
```

**Step 3: Grafana dashboard (10 min)**

Pre-built dashboard JSON with panels:
- Request rate (per endpoint)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- Database connections
- Webhook queue size

**Task 4: Partner Onboarding Guide (30 min)**

File: `docs/PARTNER_ONBOARDING.md`

Sections:
1. Account Creation
2. API Authentication
3. Quick Start (Python + curl)
4. Webhook Setup
5. Error Handling
6. Rate Limits
7. Support

**Task 5: Migration Documentation (20 min)**

File: `docs/MIGRATION_GUIDE.md`

Sections:
1. Prerequisites
2. Database Backup
3. PostgreSQL Setup (Neon.tech)
4. Migration Script
5. Verification Steps
6. Rollback Procedure

---

## ✅ ATLAS: Stress-test

### Testing Plan

**Security Tests:**
- [ ] SQL injection attempts (sqlmap)
- [ ] API Key brute force (fail after 5 attempts)
- [ ] Rate limit bypass (blocked)
- [ ] Cross-partner data access (403 Forbidden)

**Performance Tests:**
- [ ] Load test with indexes: 100 req/s, p95 <100ms
- [ ] Database query time <50ms (95%)
- [ ] Connection pool stable under load

**Monitoring Tests:**
- [ ] Metrics endpoint returns data
- [ ] Grafana dashboard loads
- [ ] Test alert fires (trigger error spike)

**Documentation Tests:**
- [ ] Partner follows guide to first API call (success)
- [ ] All code examples work (copy-paste)

---

## 📋 Task Breakdown

### Execution Order

1. **Database Indexes** (30 min) - Immediate performance gain
2. **Security Audit** (45 min) - Critical before production
3. **Monitoring Setup** (45 min) - Observability
4. **Partner Onboarding Guide** (30 min) - Documentation
5. **Migration Guide** (20 min) - Ops documentation

**Total:** 2 hours 50 minutes

---

## ⏱️ Time Estimate

| Task | Time |
|------|------|
| Security Audit | 45 min |
| Database Indexes | 30 min |
| Monitoring Setup | 45 min |
| Partner Onboarding Guide | 30 min |
| Migration Guide | 20 min |
| **Total** | **170 min (2.83h)** |

**Traditional estimate:** 2 weeks (80 hours)  
**GOTCHA velocity:** 2.83 hours  
**Expected multiplier:** **28x faster**

---

## 🚀 Success Criteria

**Phase 5 is complete when:**
- [ ] Security audit complete (zero critical issues)
- [ ] Database indexes deployed (8+ indexes)
- [ ] Monitoring stack running (Prometheus + Grafana)
- [ ] Partner onboarding guide published
- [ ] Migration guide published
- [ ] Load test passing (100 req/s, <100ms p95)
- [ ] All documentation committed to Git

**Production-Ready Checklist:**
- [ ] HTTPS enforced (Cloudflare Tunnel)
- [ ] API Keys bcrypt'd in database
- [ ] Rate limiting active (multi-tier)
- [ ] Webhook signatures verified (HMAC)
- [ ] Audit log capturing all Partner API calls
- [ ] Partner data isolated (no cross-access)
- [ ] Monitoring alerts configured (Telegram)
- [ ] Database indexes deployed
- [ ] Connection pool stable under load
- [ ] Documentation complete (API + guides)

---

**Ready to execute?** (2026-02-08 06:35 GMT+6)

**Strategy:**
1. Start with database indexes (immediate win, 30 min)
2. Security audit while indexes deploy (45 min)
3. Monitoring setup (45 min)
4. Documentation (50 min total)
5. Final validation & commit
