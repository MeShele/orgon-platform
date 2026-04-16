# Phase 3: Webhooks & Events - PLAN

**Status:** Planning (2026-02-08 05:50 GMT+6)  
**Expected Duration:** 2-3 hours (traditional: 1 week)  
**Framework:** GOTCHA + ATLAS

---

## 🎯 ATLAS: Architect

### Problem Statement
Partners need real-time notifications when critical events occur (wallet created, transaction confirmed, signature needed). Current Partner API requires polling, which is inefficient and adds latency.

### Success Metrics
1. **Delivery reliability:** 99%+ of webhooks delivered within 30s
2. **Retry success:** 95%+ failed webhooks succeed after retries
3. **Partner trust:** Webhook signatures verify 100% of the time
4. **Performance:** Background worker processes 1000+ events/min

### User Stories

**Partner Developer:**
- "I want to receive instant notifications when transactions are confirmed"
- "I need to verify webhook authenticity to prevent spoofing"
- "I want to see webhook delivery history for debugging"

**Partner Operations:**
- "I want failed webhooks to auto-retry so I don't miss events"
- "I need to configure multiple webhook URLs for different event types"

### Architecture Decisions
- **Event Queue:** PostgreSQL table (webhook_events) for durability
- **Delivery:** Background worker (APScheduler) every 30s
- **Retry Policy:** Exponential backoff (1m, 5m, 15m, 1h, 6h)
- **Signature:** HMAC-SHA256 using partner's API secret
- **Idempotency:** Event ID in payload for deduplication

---

## 🗺️ ATLAS: Trace

### Data Schema

**webhook_events table:**
```sql
CREATE TABLE webhook_events (
    id SERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,              -- Idempotency key
    partner_id UUID NOT NULL REFERENCES partners(partner_id),
    event_type VARCHAR(50) NOT NULL,            -- wallet.created, tx.confirmed, etc.
    payload JSONB NOT NULL,                     -- Event data
    webhook_url TEXT NOT NULL,                  -- Delivery endpoint
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, delivered, failed
    attempts INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMPTZ,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    INDEX idx_status_next_retry (status, next_retry_at),
    INDEX idx_partner_created (partner_id, created_at DESC),
    INDEX idx_event_type (event_type)
);
```

**partner_webhooks table** (optional, for multi-URL support):
```sql
CREATE TABLE partner_webhooks (
    id SERIAL PRIMARY KEY,
    partner_id UUID NOT NULL REFERENCES partners(partner_id),
    url TEXT NOT NULL,
    event_types TEXT[] NOT NULL,               -- ['wallet.*', 'transaction.confirmed']
    is_active BOOLEAN NOT NULL DEFAULT true,
    secret TEXT,                                -- Optional custom secret (overrides API secret)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(partner_id, url)
);
```

### Event Types
1. **Wallets:**
   - `wallet.created` - New wallet created
   - `wallet.updated` - Wallet info changed
   - `wallet.balance_changed` - Token balance changed

2. **Transactions:**
   - `transaction.created` - New transaction initiated
   - `transaction.confirmed` - Transaction confirmed on-chain
   - `transaction.failed` - Transaction failed

3. **Signatures:**
   - `signature.pending` - Awaiting approval
   - `signature.approved` - Signature approved
   - `signature.rejected` - Signature rejected

### External Integrations
- **HTTP Client:** httpx (async)
- **Signature:** hmac + hashlib (stdlib)
- **Worker:** APScheduler (already in use)

### Technology Stack
- **Backend:** FastAPI + asyncpg (existing)
- **Queue:** PostgreSQL (webhook_events table)
- **Worker:** APScheduler background job
- **Testing:** pytest + httpx test client

---

## 🔗 ATLAS: Link

### Validation Checklist

**Database:**
- [ ] webhook_events table created
- [ ] Indexes tested for query performance
- [ ] partner_id foreign key constraint works
- [ ] JSONB payload queries functional

**Services:**
- [ ] WebhookService can insert events
- [ ] WebhookService can fetch pending events
- [ ] WebhookService can mark events delivered/failed
- [ ] HMAC signature generation validated

**Triggers:**
- [ ] wallet.created fires on WalletService.create_wallet()
- [ ] transaction.confirmed fires on TransactionService.sync()
- [ ] signature.pending fires on SignatureService

**HTTP Delivery:**
- [ ] httpx POST with timeout works
- [ ] Signature header (X-Webhook-Signature) included
- [ ] Retry logic respects exponential backoff
- [ ] Max retries enforced (default: 5)

**API Routes:**
- [ ] GET /api/v1/partner/webhooks (list webhook configs)
- [ ] POST /api/v1/partner/webhooks (register webhook URL)
- [ ] DELETE /api/v1/partner/webhooks/{id} (remove webhook)
- [ ] GET /api/v1/partner/webhook-events (event log)

---

## 🏗️ ATLAS: Assemble

### Implementation Layers

**Layer 1: Database Migration**
```bash
backend/database/migrations/009_webhooks.sql
```
- Create webhook_events table
- Create partner_webhooks table
- Add indexes

**Layer 2: WebhookService**
```python
backend/services/webhook_service.py
```
Methods:
- `emit_event(partner_id, event_type, payload)` - Queue event
- `process_pending_events()` - Background worker job
- `deliver_event(event)` - HTTP POST with HMAC
- `get_partner_webhooks(partner_id)` - Fetch configs
- `verify_signature(payload, signature, secret)` - HMAC check

**Layer 3: Event Triggers**
Update existing services to call webhook_service.emit_event():
- `wallet_service.py` → wallet.created
- `transaction_service.py` → transaction.confirmed/failed
- `signature_service.py` → signature.pending/approved/rejected

**Layer 4: API Routes**
```python
backend/api/routes_webhooks_partner.py
```
Endpoints:
- GET /api/v1/partner/webhooks
- POST /api/v1/partner/webhooks
- DELETE /api/v1/partner/webhooks/{id}
- GET /api/v1/partner/webhook-events

**Layer 5: Background Worker**
```python
backend/tasks/scheduler.py
```
Add job:
- `process_webhooks()` - Every 30s

**Layer 6: Example Receiver**
```python
backend/examples/webhook_receiver.py
```
- FastAPI app listening on port 9000
- Signature verification
- Event logging

---

## ✅ ATLAS: Stress-test

### Test Plan

**Unit Tests:**
- [ ] WebhookService.emit_event() inserts event
- [ ] WebhookService.deliver_event() makes HTTP POST
- [ ] Signature generation matches expected HMAC
- [ ] Retry backoff calculates correctly
- [ ] Max retries enforced

**Integration Tests:**
- [ ] wallet.created triggers webhook
- [ ] transaction.confirmed triggers webhook
- [ ] Background worker processes events
- [ ] Failed delivery updates status + next_retry_at
- [ ] Successful delivery marks event as delivered

**Load Tests:**
- [ ] 1000 events/min processed by worker
- [ ] Database queries remain <50ms
- [ ] HTTP delivery timeouts don't block worker

**Security Tests:**
- [ ] HMAC signature verification prevents spoofing
- [ ] Invalid signatures rejected
- [ ] Webhook URLs validated (HTTPS required in production)

---

## 📋 Task Breakdown

### Task 1: Database Migration (15 min)
- [ ] Create 009_webhooks.sql migration
- [ ] Run migration on dev database
- [ ] Verify tables created
- [ ] Test indexes with sample queries

### Task 2: WebhookService (30 min)
- [ ] Create webhook_service.py
- [ ] Implement emit_event()
- [ ] Implement deliver_event() with httpx
- [ ] Implement HMAC signature generation
- [ ] Implement retry logic (exponential backoff)
- [ ] Add error handling

### Task 3: Event Triggers (15 min)
- [ ] Update wallet_service.py (wallet.created)
- [ ] Update transaction_service.py (tx.confirmed, tx.failed)
- [ ] Update signature_service.py (signature.pending, approved, rejected)

### Task 4: Background Worker (10 min)
- [ ] Add process_webhooks() job to scheduler.py
- [ ] Configure 30s interval
- [ ] Test worker processes events

### Task 5: API Routes (20 min)
- [ ] Create routes_webhooks_partner.py
- [ ] Implement GET /webhooks (list)
- [ ] Implement POST /webhooks (register)
- [ ] Implement DELETE /webhooks/{id} (remove)
- [ ] Implement GET /webhook-events (log)

### Task 6: Example Receiver (15 min)
- [ ] Create webhook_receiver.py (FastAPI)
- [ ] Implement signature verification
- [ ] Add event logging
- [ ] Add usage instructions

### Task 7: Testing (25 min)
- [ ] Write unit tests (test_webhook_service.py)
- [ ] Write integration tests (test_webhooks_integration.py)
- [ ] Run all tests
- [ ] Fix any failures

### Task 8: Documentation (10 min)
- [ ] Update PHASE3_COMPLETE.md
- [ ] Add webhook examples to README
- [ ] Git commit

---

## ⏱️ Time Estimate

**Total:** ~2.5 hours (140 minutes)

| Task | Time |
|------|------|
| Database Migration | 15 min |
| WebhookService | 30 min |
| Event Triggers | 15 min |
| Background Worker | 10 min |
| API Routes | 20 min |
| Example Receiver | 15 min |
| Testing | 25 min |
| Documentation | 10 min |

**Buffer:** +30 min for unexpected issues  
**Expected:** 2-3 hours total

---

## 🚀 Success Criteria

**Phase 3 is complete when:**
- [ ] All 8 tasks completed
- [ ] All tests passing
- [ ] Example receiver working
- [ ] Documentation updated
- [ ] Git committed

**Demo scenario:**
1. Partner registers webhook URL via API
2. Create wallet via Partner API
3. Webhook delivered to receiver within 30s
4. Receiver verifies signature successfully
5. Event logged in webhook_events table

---

**Ready to start?** (2026-02-08 05:50 GMT+6)
