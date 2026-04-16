# ORGON Development Roadmap — GOTCHA ATLAS Framework

**Дата создания:** 2026-02-06  
**Фреймворк:** GOTCHA ATLAS (Goals, Orchestration, Tools, Context, Hardprompts, Args, Time, Learning, Architecture, Security)  
**Статус:** Phase 1 Complete → Phase 2 Planning

---

## 📊 Текущее состояние (v1.0 - MVP Deployed)

### ✅ Что реализовано

**Backend Services (7/7):**
- ✅ WalletService — управление кошельками
- ✅ TransactionService — транзакции + validation
- ✅ SignatureService — multi-sig workflow
- ✅ NetworkService — справочники сетей/токенов (кеш 1h)
- ✅ BalanceService — балансы + history
- ✅ DashboardService — аналитика + stats
- ✅ SyncService — синхронизация с Safina

**API Endpoints (8 routers):**
- ✅ `/api/wallets` — CRUD кошельков
- ✅ `/api/transactions` — список, отправка, validation
- ✅ `/api/signatures` — pending, sign, reject, history
- ✅ `/api/networks` — сети + токены
- ✅ `/api/dashboard` — stats, overview, recent, alerts
- ✅ `/api/health` — healthcheck
- ✅ `/api/export` — CSV/JSON export
- ✅ `/api/webhooks` — входящие события

**Frontend Components (30+):**
- ✅ Dashboard (StatCards, RecentActivity, TokenSummary, Alerts)
- ✅ Wallets (list, detail, create)
- ✅ Transactions (list, filters, send form, detail)
- ✅ Signatures (pending table, history, progress indicator)
- ✅ Networks (list, status)
- ✅ Settings (keys, preferences)

**Infrastructure:**
- ✅ Cloudflare Tunnel — https://orgon.asystem.ai
- ✅ SQLite — local database
- ✅ Safina Pay API — integration complete
- ✅ Telegram Bot — notifications (@urmat_ai_bot)
- ✅ CORS — configured for production

---

## 🎯 GOTCHA ATLAS Roadmap

### **G — Goals (Цели бизнеса)**

#### Phase 2: Enhanced User Experience (2-3 недели)
**Цель:** Сделать ORGON удобным для ежедневного использования

**Приоритет 1: Real-time Updates**
- [ ] WebSocket connection для live updates
- [ ] Push notifications (browser + Telegram)
- [ ] Live balance updates (без refresh)
- [ ] Transaction status streaming

**Приоритет 2: Advanced Transaction Features**
- [ ] Transaction scheduling ("send tomorrow at 10:00")
- [ ] Recurring payments ("send 100 USDT every Monday")
- [ ] Batch transactions (multiple sends in one action)
- [ ] Transaction templates (сохранённые получатели)

**Приоритет 3: Analytics & Insights**
- [ ] Balance history charts (7/30/90 days)
- [ ] Transaction volume analytics
- [ ] Token performance tracking
- [ ] Spending categories & tagging
- [ ] Export to CSV/PDF для отчётности

**Acceptance:**
- Users can schedule transactions without manual intervention
- Dashboard shows real-time balance changes
- Analytics provide actionable insights

#### Phase 3: Enterprise Features (3-4 недели)
**Цель:** Multi-sig governance для команд

**Приоритет 1: Advanced Multi-Sig**
- [ ] Role-based approval workflows (CEO → CFO → Accountant)
- [ ] Spending limits per role
- [ ] Time-locked approvals (24h window)
- [ ] Audit trail с immutable logs

**Приоритет 2: Team Management**
- [ ] User accounts & authentication
- [ ] Permission system (admin, approver, viewer)
- [ ] Team workspace (shared wallets)
- [ ] Activity logs per user

**Priory 3: Compliance & Security**
- [ ] 2FA (TOTP, hardware keys)
- [ ] IP whitelisting
- [ ] Transaction limits & daily caps
- [ ] Suspicious activity detection

**Acceptance:**
- Teams can manage multi-sig wallets with clear approval flows
- Audit trail meets compliance requirements
- Security passes basic penetration testing

---

### **O — Orchestration (Автоматизация)**

#### Phase 2: ASAGENT Integration
**Цель:** Автономное управление через AI agent

**Auto-Approval Workflow:**
- [ ] Whitelist trusted addresses
- [ ] Auto-approve small amounts (<$100)
- [ ] Smart approval rules (e.g., "approve payroll every Friday")
- [ ] Telegram approval shortcuts (`/approve {tx_unid}`)

**Smart Alerts:**
- [ ] Balance threshold alerts ("TRX below 1000")
- [ ] Large transaction alerts (">$500")
- [ ] Failed transaction notifications
- [ ] Network fee spike warnings

**Autonomous Tasks:**
- [ ] Auto-sync balances every 5 min
- [ ] Auto-refresh network cache hourly
- [ ] Auto-retry failed transactions
- [ ] Auto-backup database daily

**Implementation:**
```python
# asagent/workflows/orgon_auto_approve.py
async def auto_approve_trusted(tx_unid, details):
    if details.to_address in TRUSTED_ADDRESSES:
        if details.value_usd < 100:
            await orgon_client.sign_transaction(tx_unid)
            await telegram.notify(f"✅ Auto-approved: {details.value} to {details.to_address[:8]}...")
```

**Acceptance:**
- ASAGENT can approve 80% of routine transactions without human intervention
- Alerts arrive within 30 seconds of event
- Zero false positives on suspicious activity detection

#### Phase 3: Event-Driven Architecture
**Цель:** Реактивная система на события

**Event Types:**
- `wallet.created`, `wallet.balance_changed`
- `transaction.sent`, `transaction.confirmed`, `transaction.failed`
- `signature.pending`, `signature.approved`, `signature.rejected`
- `network.fee_spike`, `network.congestion`

**Event Handlers:**
- [ ] Webhook delivery (external systems)
- [ ] Email notifications
- [ ] Slack/Discord integration
- [ ] Custom triggers (if X then Y)

**Example:**
```yaml
# Event rule
on: transaction.confirmed
if: value_usd > 1000
then:
  - notify: telegram
  - export: accounting_system
  - log: audit_trail
```

---

### **T — Tools (Инструменты)**

#### Phase 2: Database Migration
**Цель:** Переход на PostgreSQL для scalability

**Current:** SQLite (140 KB)  
**Target:** PostgreSQL (Neon.tech)

**Migration Plan:**
1. [ ] Create Neon database schema
2. [ ] Export SQLite → PostgreSQL
3. [ ] Update backend to use asyncpg
4. [ ] Add connection pooling
5. [ ] Enable full-text search
6. [ ] Add materialized views for analytics

**Benefits:**
- ✅ Concurrent writes (SQLite locks entire DB)
- ✅ Full-text search на transactions
- ✅ Advanced queries (window functions, CTEs)
- ✅ Horizontal scaling готовность

#### Phase 2: WebSocket Server
**Цель:** Real-time communication

**Implementation:**
```python
# backend/websocket_server.py
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.broadcast({
        "type": "balance_update",
        "wallet": "E55EF...",
        "token": "TRX",
        "value": 4985.85
    })
```

**Use Cases:**
- Live balance updates
- Transaction status changes
- Signature approvals (multi-sig)
- Network status alerts

#### Phase 3: CLI Tools
**Цель:** Админ-утилиты для операций

```bash
# orgon-cli
orgon wallet list
orgon wallet create --network=5010 --info="Treasury"
orgon tx send --to=TRx6x... --value=10 --token=USDT
orgon backup create
orgon backup restore backups/2026-02-06.sql
orgon sync --force
```

---

### **C — Context (Контекстная информация)**

#### Phase 2: User Preferences
**Цель:** Персонализация опыта

**Features:**
- [ ] Favorite wallets (pinned to top)
- [ ] Default network selection
- [ ] Notification preferences (email/telegram/push)
- [ ] UI theme (dark/light/auto)
- [ ] Language selection (en/ru/kg)
- [ ] Currency display (USD/EUR/RUB)

**Storage:**
```sql
CREATE TABLE user_preferences (
  user_id UUID PRIMARY KEY,
  favorite_wallets JSONB,
  default_network INT,
  notifications JSONB,
  theme VARCHAR(10),
  language VARCHAR(2),
  currency VARCHAR(3),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
);
```

#### Phase 2: Address Book
**Цель:** Частые получатели

**Features:**
- [ ] Save recipient addresses with labels
- [ ] Group by category (payroll, vendors, personal)
- [ ] Auto-complete при вводе
- [ ] Import/export (CSV)

```json
{
  "id": "uuid",
  "label": "Salary - Aibek",
  "address": "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
  "network": "5010",
  "category": "payroll",
  "notes": "Monthly salary transfer"
}
```

#### Phase 3: Transaction Templates
**Цель:** Повторяющиеся операции

**Example:**
```json
{
  "name": "Monthly Payroll - Team Lead",
  "to_address": "TRx6x...",
  "token": "USDT",
  "value": "2000",
  "network": "5010",
  "info": "Salary payment",
  "schedule": "0 0 1 * *"  // First day of month
}
```

---

### **H — Hardprompts (Жёсткие правила)**

#### Phase 2: Security Policies
**Цель:** Zero-trust architecture

**Policies:**
1. **Transaction Limits**
   - Max single tx: $10,000
   - Daily limit: $50,000
   - Require additional approval for >$5,000

2. **IP Whitelisting**
   - Admin panel accessible only from trusted IPs
   - API rate limiting: 100 req/min per IP
   - Geo-blocking suspicious regions

3. **Multi-Factor Authentication**
   - TOTP required for admin actions
   - Hardware key (YubiKey) support
   - Backup codes for account recovery

**Implementation:**
```python
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/admin"):
        if not is_whitelisted_ip(request.client.host):
            return JSONResponse({"detail": "Access denied"}, 403)
    return await call_next(request)
```

#### Phase 3: Compliance
**Цель:** AML/KYC готовность

**Features:**
- [ ] Transaction screening (OFAC lists)
- [ ] Large transaction reporting (>$10k)
- [ ] Audit logs (immutable, cryptographically signed)
- [ ] Data retention policies (7 years)

---

### **A — Args (Конфигурация)**

#### Phase 2: Feature Flags
**Цель:** Canary deployments

```yaml
# config/features.yaml
features:
  websocket_enabled: true
  auto_approval: false  # Disable for now
  analytics_v2: true
  neon_db: false  # SQLite for now
  telegram_inline_buttons: true
```

**Benefits:**
- Deploy new features to 10% users first
- Instant rollback без redeploy
- A/B testing

#### Phase 2: Environment Management
**Цель:** Dev/Staging/Prod separation

```bash
# .env.development
SAFINA_API_URL=https://my.safina.pro/ece-test
DATABASE_URL=sqlite:///dev.db
DEBUG=true

# .env.production
SAFINA_API_URL=https://my.safina.pro/ece
DATABASE_URL=postgresql://...
DEBUG=false
SENTRY_DSN=https://...
```

---

### **T — Time (Временные рамки)**

#### Short-Term (1-2 weeks)
**Quick Wins:**
- [ ] PostgreSQL migration
- [ ] WebSocket real-time updates
- [ ] Transaction scheduling UI
- [ ] Address book
- [ ] Balance history charts

#### Mid-Term (3-4 weeks)
**Major Features:**
- [ ] ASAGENT auto-approval
- [ ] Multi-sig governance UI
- [ ] Advanced analytics
- [ ] Team management
- [ ] 2FA implementation

#### Long-Term (2-3 months)
**Ambitious Goals:**
- [ ] Mobile app (React Native)
- [ ] API marketplace (3rd-party integrations)
- [ ] AI-powered insights ("unusual spending detected")
- [ ] Cross-chain support (не только Safina)

---

### **L — Learning (Обучение и адаптация)**

#### Phase 2: User Behavior Analytics
**Цель:** Понять как используют ORGON

**Metrics:**
- Most used features (wallets vs transactions vs signatures)
- Average session duration
- Conversion funnel (wallet create → transaction send)
- Error rates по endpoints

**Tools:**
- [ ] PostHog (event tracking)
- [ ] Sentry (error monitoring)
- [ ] LogRocket (session replay)

**Insights:**
- If 80% users never use multi-sig → simplify UX
- If transaction send fails 20% → improve validation
- If mobile traffic >50% → prioritize mobile app

#### Phase 3: AI-Powered Insights
**Цель:** Proactive recommendations

**Examples:**
- "You usually send to TRx6x... on Fridays. Schedule this week?"
- "USDT balance low. Convert TRX → USDT?"
- "Gas fees 30% higher than usual. Wait 2 hours?"

**Implementation:**
```python
# ML model on transaction patterns
model.predict_next_transaction(user_history)
# → {"to": "TRx6x...", "amount": 2000, "confidence": 0.85}
```

---

### **A — Architecture (Архитектура)**

#### Phase 2: Microservices (Optional)
**Цель:** Разделение ответственности

**Current:** Monolith (FastAPI)  
**Target:** Service-oriented (если scale требуется)

**Services:**
- `wallet-service` — wallet CRUD
- `transaction-service` — tx processing
- `notification-service` — alerts
- `analytics-service` — reporting
- `auth-service` — authentication

**Communication:** REST API + Message Queue (RabbitMQ/Redis)

**Benefits:**
- Independent scaling (analytics может быть slow, но не блокирует tx)
- Language flexibility (analytics на Python, real-time на Go)
- Fault isolation (если analytics падает, tx работают)

**Cost:** Complexity ↑, operational overhead ↑

**Recommendation:** Stick to monolith до 10,000 users. Then consider.

#### Phase 3: Event Sourcing
**Цель:** Immutable audit trail

**Current:** Update-in-place (UPDATE transactions SET status='confirmed')  
**Target:** Append-only log

**Example:**
```json
// Event stream
{"event": "TransactionCreated", "tx_unid": "F49D...", "timestamp": "..."}
{"event": "SignatureAdded", "tx_unid": "F49D...", "signer": "0xA285..."}
{"event": "TransactionConfirmed", "tx_unid": "F49D...", "tx_hash": "2ab53..."}
```

**Benefits:**
- Full audit trail (кто, что, когда)
- Time travel debugging ("what was balance on Feb 1?")
- Compliance ready

---

### **S — Security (Безопасность)**

#### Phase 2: Threat Model
**Risks:**
1. **Private Key Leak**
   - Mitigation: Vault integration, HSM support
   - Detection: Unusual tx patterns

2. **API Key Compromise**
   - Mitigation: Short-lived tokens, rotation
   - Detection: IP/geo anomalies

3. **SQL Injection**
   - Mitigation: Parameterized queries (already done via SQLAlchemy/asyncpg)
   - Testing: SQLMap scan

4. **CSRF**
   - Mitigation: CSRF tokens, SameSite cookies
   - Testing: Burp Suite

**Security Checklist:**
- [ ] HTTPS everywhere (✅ via Cloudflare)
- [ ] Input validation (✅ Pydantic)
- [ ] Rate limiting (⏳ TODO)
- [ ] CORS configured (✅)
- [ ] Secrets in env vars (✅)
- [ ] Dependency scanning (⏳ TODO: Dependabot)
- [ ] Penetration testing (⏳ TODO)

#### Phase 3: Bug Bounty Program
**Цель:** Community-driven security

**Scope:**
- Critical: $500 (RCE, auth bypass, private key leak)
- High: $200 (XSS, CSRF, data leak)
- Medium: $50 (DoS, info disclosure)

**Platform:** HackerOne or self-hosted

---

## 📋 Implementation Priority Matrix

| Feature | Impact | Effort | Priority | Phase |
|---------|--------|--------|----------|-------|
| PostgreSQL migration | High | Medium | 🔥 P0 | 2 |
| WebSocket real-time | High | Medium | 🔥 P0 | 2 |
| Transaction scheduling | High | Low | 🔥 P0 | 2 |
| Address book | Medium | Low | ⚡ P1 | 2 |
| Balance charts | Medium | Low | ⚡ P1 | 2 |
| ASAGENT auto-approval | High | High | ⚡ P1 | 2 |
| 2FA | High | Medium | ⚡ P1 | 2 |
| Team management | Medium | High | 📌 P2 | 3 |
| Mobile app | High | Very High | 📌 P2 | 3 |
| AI insights | Low | Very High | 🔮 P3 | 3+ |

---

## 🚀 Next Steps (This Week)

### Day 1-2: PostgreSQL Migration
1. Create Neon database
2. Export SQLite schema + data
3. Update `backend/database/db.py` для asyncpg
4. Test all endpoints
5. Deploy

### Day 3-4: WebSocket + Real-time
1. Implement WebSocket server
2. Frontend WebSocket client
3. Live balance updates
4. Live transaction status

### Day 5: Transaction Scheduling
1. Backend: cron integration
2. Frontend: date/time picker
3. UI: scheduled transactions list
4. Test: scheduled send

### Weekend: Documentation
1. Update API docs (Swagger)
2. User guide (как создать кошелёк, отправить tx)
3. Admin guide (deployment, backup)

---

## 📞 Support & Resources

**GOTCHA ATLAS Framework:**
- Documentation: `/Users/urmatmyrzabekov/AGENT/CLAUDE.md`
- Experts: `asagent/experts/`
- Tools: `asagent/tools/`

**ORGON Project:**
- Docs: `/Users/urmatmyrzabekov/AGENT/ORGON/docs/`
- API Reference: https://orgon.asystem.ai/docs
- Status: `./status.sh`

**External APIs:**
- Safina Pay: https://my.safina.pro/ece
- Neon PostgreSQL: https://neon.tech
- Cloudflare: https://dash.cloudflare.com

---

**Compiled by:** ASAGENT  
**Framework:** GOTCHA ATLAS v2.0  
**Last Updated:** 2026-02-06 14:20 GMT+6
