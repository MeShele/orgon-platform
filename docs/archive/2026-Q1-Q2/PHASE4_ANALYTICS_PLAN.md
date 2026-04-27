# Phase 4: Analytics & Advanced Features - PLAN

**Status:** Planning (2026-02-08 06:25 GMT+6)  
**Expected Duration:** 1-1.5 hours (traditional: 1 week)  
**Framework:** GOTCHA + ATLAS

---

## 🎯 ATLAS: Architect

### Problem Statement
Partners need analytics, scheduled transactions, and address book management via Partner API. Current implementation exists for internal use only (not exposed to Partner API).

### What Already Exists (70% done)
✅ **Services (Week 2):**
- AnalyticsService (10.9KB) - balance history, volume, distribution, fees
- ScheduledTransactionService (10.3KB) - cron scheduling, execution
- AddressBookService (8.3KB) - saved addresses, favorites

✅ **Internal API Routes:**
- routes_analytics.py (4.4KB) - `/api/analytics/*`
- routes_scheduled.py (5.7KB) - `/api/scheduled/*`
- routes_contacts.py (6.3KB) - `/api/contacts/*`

✅ **Database Tables (Phase 1):**
- transaction_analytics
- scheduled_transactions_b2b
- address_book_b2b

✅ **Background Worker:**
- Scheduled transaction processing job (every 1 min)

### What's Missing (30% to do)
❌ **Partner API Endpoints** (not exposed to B2B partners)
❌ **Price Feed Integration** (CoinGecko for USD values)
❌ **Load Testing** (validate performance at scale)

### Success Metrics
1. **Analytics:** Partners can view transaction volume, fees, token distribution
2. **Scheduled TX:** Partners can create/list/delete scheduled transactions
3. **Address Book:** Partners can save/list/delete addresses
4. **USD Values:** All analytics include USD equivalent (via CoinGecko)
5. **Performance:** <100ms API response time (p95)

---

## 🗺️ ATLAS: Trace

### API Endpoints to Create

**Analytics (Partner API):**
- GET `/api/v1/partner/analytics/volume` - Transaction volume over time
- GET `/api/v1/partner/analytics/fees` - Fee analysis
- GET `/api/v1/partner/analytics/distribution` - Token distribution
- GET `/api/v1/partner/analytics/export` - CSV/JSON export

**Scheduled Transactions (Partner API):**
- POST `/api/v1/partner/scheduled-transactions` - Create schedule
- GET `/api/v1/partner/scheduled-transactions` - List schedules
- GET `/api/v1/partner/scheduled-transactions/{id}` - Get schedule
- DELETE `/api/v1/partner/scheduled-transactions/{id}` - Delete schedule

**Address Book (Partner API):**
- POST `/api/v1/partner/addresses` - Save address
- GET `/api/v1/partner/addresses` - List addresses
- GET `/api/v1/partner/addresses/{id}` - Get address
- PUT `/api/v1/partner/addresses/{id}` - Update address
- DELETE `/api/v1/partner/addresses/{id}` - Delete address

### External Integrations

**CoinGecko API (Free Tier):**
- Endpoint: `https://api.coingecko.com/api/v3/simple/price`
- Rate limit: 10-50 calls/min (free tier)
- Supported coins: TRX, BTC, ETH, USDT, etc.
- Response: `{"tron": {"usd": 0.065}}`

**Caching Strategy:**
- Cache prices for 5 minutes (in-memory or Redis)
- Batch requests (multi-coin support)
- Fallback to last known price on API failure

---

## 🔗 ATLAS: Link

### Validation Checklist

**Partner API Integration:**
- [ ] Analytics endpoints require API Key + Secret
- [ ] Endpoints filter by partner_id automatically
- [ ] Pagination working (limit/offset)
- [ ] Error handling (404, 400, 500)

**Price Feed:**
- [ ] CoinGecko API working
- [ ] Prices cached (5 min TTL)
- [ ] Multi-coin batch requests
- [ ] Fallback to last known price
- [ ] USD conversion in analytics

**Performance:**
- [ ] Analytics queries <100ms (with indexes)
- [ ] Scheduled TX queries <50ms
- [ ] Address book queries <30ms
- [ ] Load test: 100 req/s sustained

---

## 🏗️ ATLAS: Assemble

### Implementation Tasks

**Task 1: Price Feed Service (30 min)**
- Create `backend/services/price_feed_service.py`
- Implement CoinGecko API client
- Add in-memory cache (5 min TTL)
- Add fallback logic
- Integrate with AnalyticsService

**Task 2: Partner Analytics API (20 min)**
- Create `backend/api/routes_partner_analytics.py`
- Wrap AnalyticsService with Partner API auth
- Add partner_id filtering
- Add USD conversion via price feed
- Register routes in main.py

**Task 3: Partner Scheduled TX API (15 min)**
- Create `backend/api/routes_partner_scheduled.py`
- Wrap ScheduledTransactionService with Partner API auth
- Add partner_id filtering
- Add cron expression validation
- Register routes in main.py

**Task 4: Partner Address Book API (15 min)**
- Create `backend/api/routes_partner_addresses.py`
- Wrap AddressBookService with Partner API auth
- Add partner_id filtering
- Add address validation (network-specific)
- Register routes in main.py

**Task 5: Load Testing (20 min)**
- Create `backend/tests/load_test.py` (using locust)
- Test scenarios:
  - 100 concurrent users
  - Mixed read/write operations
  - Sustained 100 req/s for 5 minutes
- Validate p95 latency <100ms

---

## ✅ ATLAS: Stress-test

### Test Plan

**Unit Tests:**
- [ ] PriceFeedService.get_prices() returns correct format
- [ ] PriceFeedService caching works (5 min TTL)
- [ ] AnalyticsService USD conversion accurate

**Integration Tests:**
- [ ] GET /api/v1/partner/analytics/volume returns data
- [ ] POST /api/v1/partner/scheduled-transactions creates schedule
- [ ] GET /api/v1/partner/addresses returns only partner's addresses
- [ ] Price feed fallback works when CoinGecko unavailable

**Load Tests:**
- [ ] 100 req/s sustained for 5 minutes
- [ ] p95 latency <100ms
- [ ] No database connection pool exhaustion
- [ ] No memory leaks

---

## 📋 Task Breakdown

### Task 1: Price Feed Service (30 min)
File: `backend/services/price_feed_service.py`

Features:
- CoinGecko API integration
- In-memory cache (dict with timestamps)
- Multi-coin batch requests
- Fallback to last known price
- Error handling

Example usage:
```python
price_feed = PriceFeedService()
prices = await price_feed.get_prices(["tron", "bitcoin", "ethereum"])
# {"tron": 0.065, "bitcoin": 45000.0, "ethereum": 2500.0}
```

### Task 2: Partner Analytics API (20 min)
File: `backend/api/routes_partner_analytics.py`

Endpoints:
- GET /analytics/volume (time-series)
- GET /analytics/fees (aggregated)
- GET /analytics/distribution (pie chart data)
- GET /analytics/export (CSV/JSON)

All with partner_id filtering + USD values.

### Task 3: Partner Scheduled TX API (15 min)
File: `backend/api/routes_partner_scheduled.py`

Endpoints:
- POST /scheduled-transactions (create)
- GET /scheduled-transactions (list)
- GET /scheduled-transactions/{id} (details)
- DELETE /scheduled-transactions/{id} (cancel)

Validates cron expressions, network_id, wallet ownership.

### Task 4: Partner Address Book API (15 min)
File: `backend/api/routes_partner_addresses.py`

Endpoints:
- POST /addresses (save)
- GET /addresses (list with filters)
- GET /addresses/{id} (details)
- PUT /addresses/{id} (update)
- DELETE /addresses/{id} (remove)

Validates addresses per network (Tron, ETH, BTC formats).

### Task 5: Load Testing (20 min)
File: `backend/tests/load_test.py`

Using Locust:
```python
class PartnerAPIUser(HttpUser):
    @task(3)
    def get_wallets(self):
        self.client.get("/api/v1/partner/wallets", headers=auth_headers)
    
    @task(2)
    def get_analytics(self):
        self.client.get("/api/v1/partner/analytics/volume", headers=auth_headers)
    
    @task(1)
    def create_address(self):
        self.client.post("/api/v1/partner/addresses", json={...}, headers=auth_headers)
```

Target: 100 users, 5 min duration, p95 <100ms.

---

## ⏱️ Time Estimate

| Task | Time |
|------|------|
| Price Feed Service | 30 min |
| Partner Analytics API | 20 min |
| Partner Scheduled TX API | 15 min |
| Partner Address Book API | 15 min |
| Load Testing | 20 min |
| **Total** | **100 min** |

**Buffer:** +20 min for unexpected issues  
**Expected:** 1.5-2 hours total

**Traditional estimate:** 1 week (40 hours)  
**GOTCHA velocity:** 1.67 hours (100 min)  
**Expected multiplier:** **24x faster**

---

## 🚀 Success Criteria

**Phase 4 is complete when:**
- [ ] Price feed working (CoinGecko integration)
- [ ] Partner Analytics API (4 endpoints)
- [ ] Partner Scheduled TX API (4 endpoints)
- [ ] Partner Address Book API (5 endpoints)
- [ ] All endpoints authenticated (API Key + Secret)
- [ ] Load test passing (100 req/s, p95 <100ms)
- [ ] Documentation updated
- [ ] Git committed

**Demo scenario:**
1. Partner calls GET /analytics/volume → sees USD values
2. Partner creates scheduled transaction → executed automatically
3. Partner saves address → used in future transactions
4. Load test → sustains 100 req/s with <100ms latency

---

**Ready to start?** (2026-02-08 06:25 GMT+6)
