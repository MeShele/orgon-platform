# ORGON — Next Steps (Quick Reference)

**Статус:** MVP deployed ✅ — https://orgon.asystem.ai  
**Дата:** 2026-02-06  
**Roadmap:** См. ROADMAP_GOTCHA_ATLAS.md для полного плана

---

## 🎯 Top 5 Priorities (This Month)

### 1. PostgreSQL Migration (Week 1)
**Why:** SQLite locks on concurrent writes, no full-text search  
**Impact:** High — enables scaling  
**Effort:** Medium — 2-3 days

**Steps:**
```bash
# 1. Create Neon database (already connected!)
psql 'postgresql://neondb_owner:npg_c3Qrb2ZpSufs@ep-late-sea-aglfcbe1...'

# 2. Export SQLite schema
sqlite3 data/orgon.db .schema > schema.sql

# 3. Update backend/database/db.py
# Replace aiosqlite → asyncpg

# 4. Migrate data
python scripts/migrate_to_postgres.py

# 5. Test
pytest tests/

# 6. Deploy
./restart-all.sh
```

**Acceptance:**
- ✅ All tests pass
- ✅ Concurrent writes work
- ✅ Full-text search enabled

---

### 2. WebSocket Real-Time Updates (Week 1)
**Why:** Users want live balance updates без refresh  
**Impact:** High — better UX  
**Effort:** Medium — 2 days

**Implementation:**
```python
# backend/websocket.py
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Broadcast balance update
    await manager.broadcast({
        "type": "balance_update",
        "wallet": "E55EF...",
        "token": "TRX",
        "value": 4985.85
    })
```

**Frontend:**
```typescript
// src/lib/websocket.ts
const ws = new WebSocket('wss://orgon.asystem.ai/ws')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  if (data.type === 'balance_update') {
    updateBalance(data.wallet, data.token, data.value)
  }
}
```

**Acceptance:**
- ✅ Live balance updates
- ✅ Live transaction status
- ✅ Connection survives network blips

---

### 3. Transaction Scheduling (Week 2)
**Why:** Users want "send tomorrow at 10:00" feature  
**Impact:** Medium-High — killer feature  
**Effort:** Low — 1 day

**Backend:**
```python
# backend/services/scheduler_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('date', run_date='2026-02-07 10:00:00')
async def send_scheduled_transaction(tx_data):
    await transaction_service.send_transaction(tx_data)
```

**Frontend:**
```tsx
// components/transactions/SchedulePicker.tsx
<DateTimePicker 
  value={scheduleTime}
  onChange={(date) => setScheduleTime(date)}
  minDate={new Date()}
/>
```

**Acceptance:**
- ✅ Schedule UI works
- ✅ Scheduled tx executes on time
- ✅ Can cancel/edit scheduled tx

---

### 4. Address Book (Week 2)
**Why:** Typing "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL" каждый раз — pain  
**Impact:** Medium — quality of life  
**Effort:** Low — 1 day

**Database:**
```sql
CREATE TABLE address_book (
  id UUID PRIMARY KEY,
  user_id UUID,
  label VARCHAR(100),
  address VARCHAR(100),
  network INT,
  category VARCHAR(50),
  notes TEXT,
  created_at TIMESTAMPTZ
);
```

**UI:**
```tsx
// Auto-complete when typing address
<AddressInput
  onSearch={(query) => searchAddressBook(query)}
  suggestions={addressBook}
/>
```

**Acceptance:**
- ✅ Save addresses with labels
- ✅ Auto-complete works
- ✅ Import/export CSV

---

### 5. ASAGENT Auto-Approval (Week 3)
**Why:** Autonomous AI agent can approve trusted tx  
**Impact:** High — automation  
**Effort:** Medium — 2 days

**Workflow:**
```python
# asagent/workflows/orgon_auto_approve.py

TRUSTED_ADDRESSES = [
    "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",  # Payroll
]

async def check_pending_signatures():
    pending = await orgon.get_pending_signatures()
    
    for tx in pending:
        if tx.to_address in TRUSTED_ADDRESSES:
            if tx.value_usd < 100:
                await orgon.sign_transaction(tx.unid)
                await telegram.notify(f"✅ Auto-approved: ${tx.value_usd} to {tx.to_address[:8]}...")
```

**Configuration:**
```yaml
# asagent/args/orgon_auto_approve.yaml
trusted_addresses:
  - "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
max_amount_usd: 100
check_interval_seconds: 300
enabled: true
```

**Acceptance:**
- ✅ Auto-approves trusted tx <$100
- ✅ Telegram notification sent
- ✅ Logs every auto-approval

---

## 🔮 Future Features (Backlog)

**Phase 3 (Month 2-3):**
- Multi-sig governance UI (role-based approval)
- Team management (users, permissions)
- 2FA (TOTP, YubiKey)
- Balance history charts (7/30/90 days)
- Transaction analytics
- Recurring payments
- Batch transactions
- Mobile app (React Native)

**Phase 4 (Month 3+):**
- AI insights ("unusual spending detected")
- Cross-chain support (not just Safina)
- API marketplace (3rd-party integrations)
- Bug bounty program

---

## 📊 Success Metrics

**Week 1 Goals:**
- [ ] PostgreSQL migration complete
- [ ] WebSocket live updates работают
- [ ] Zero downtime during migration

**Week 2 Goals:**
- [ ] Transaction scheduling released
- [ ] Address book с 10+ entries
- [ ] <1s response time на dashboard

**Week 3 Goals:**
- [ ] ASAGENT auto-approves >80% routine tx
- [ ] Telegram notifications <30s latency
- [ ] Zero security incidents

**Month 1 Goals:**
- [ ] 50+ active wallets
- [ ] 1000+ transactions processed
- [ ] 99.9% uptime
- [ ] All Phase 2 features deployed

---

## 🛠️ Quick Commands

**Check status:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
./status.sh
```

**Restart services:**
```bash
./restart-all.sh
```

**View logs:**
```bash
tail -f backend.log
tail -f frontend/frontend.log
tail -f cloudflared.log
```

**Run tests:**
```bash
source venv/bin/activate
pytest backend/tests/ -v
```

**Database backup:**
```bash
sqlite3 data/orgon.db .dump > backups/orgon-$(date +%Y%m%d).sql
```

---

## 📞 Support

**Documentation:**
- Full Roadmap: `ROADMAP_GOTCHA_ATLAS.md`
- API Docs: https://orgon.asystem.ai/docs
- Deployment: `DEPLOYMENT.md`

**Infrastructure:**
- Public URL: https://orgon.asystem.ai
- Backend: localhost:8890
- Frontend: localhost:3000
- Database: data/orgon.db (→ PostgreSQL soon)

**ASAGENT:**
- Framework: GOTCHA ATLAS
- Memory: `/Users/urmatmyrzabekov/AGENT/memory/`
- Skills: `/Users/urmatmyrzabekov/AGENT/asagent/`

---

**Last Updated:** 2026-02-06 14:25 GMT+6  
**Next Review:** 2026-02-13 (weekly sprint)
