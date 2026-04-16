# Phase 4 Plan: Integrations

**Date:** 2026-02-05
**Status:** In Progress
**Estimated Time:** 2-3 days

---

## 🎯 Phase 4 Goals

Integrate ORGON with external systems and add production-ready features:
1. **Telegram Bot Integration** — Real-time notifications for signatures
2. **ASAGENT Integration** — Connect to autonomous agent gateway
3. **Enhanced Features** — USD conversion, export, QR codes
4. **Production Polish** — Error handling, logging, monitoring

---

## 📋 Current State Analysis

### ✅ Already Exists in Backend
**SignatureService (Phase 1):**
- Already has `telegram_notifier` parameter
- `check_new_pending_signatures()` method ready
- Notification structure defined
- Background task configured (every 5 minutes)

**What's Missing:**
- TelegramNotifier class implementation
- ASAGENT Gateway integration
- USD price conversion
- Export functionality

### ✅ Already Exists in ASAGENT
**Gateway Server:**
- `asagent/gateway/server.py` — Telegram bot server
- `asagent/gateway/skills/builtin.py` — Bot commands
- `asagent/security/vault/vault.py` — Credential storage
- `.env` has `TELEGRAM_BOT_TOKEN`

**Integration Point:** ORGON backend can use ASAGENT's Telegram infrastructure

---

## 🚀 Implementation Plan

### Step 1: Telegram Notifier Integration

#### 1.1: Create TelegramNotifier Class
**File:** `backend/integrations/telegram_notifier.py` (NEW)

**Purpose:** Send notifications via Telegram

**Class Design:**
```python
class TelegramNotifier:
    def __init__(self, bot_token: str, default_chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    async def send_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown"
    ) -> dict:
        """Send a message to Telegram."""

    async def notify_pending_signature(
        self,
        tx_unid: str,
        token: str,
        value: str,
        to_addr: str,
        chat_id: Optional[str] = None
    ):
        """Notify about new pending signature."""

    async def notify_signature_complete(
        self,
        tx_unid: str,
        progress: str,
        chat_id: Optional[str] = None
    ):
        """Notify when signature threshold reached."""
```

**Features:**
- Async HTTP client (aiohttp)
- Markdown formatting
- Error handling (API failures)
- Retry logic (3 attempts)
- Rate limiting (respect Telegram limits)

#### 1.2: Update Configuration
**File:** `backend/config.py`

**Add Telegram Config:**
```python
{
    "telegram": {
        "enabled": os.getenv("TELEGRAM_ENABLED", "false").lower() == "true",
        "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
    }
}
```

#### 1.3: Wire Up SignatureService
**File:** `backend/main.py`

**Update Initialization:**
```python
# Initialize Telegram notifier (if enabled)
telegram_notifier = None
if config["telegram"]["enabled"] and config["telegram"]["bot_token"]:
    from backend.integrations.telegram_notifier import TelegramNotifier
    telegram_notifier = TelegramNotifier(
        bot_token=config["telegram"]["bot_token"],
        default_chat_id=config["telegram"]["chat_id"]
    )
    logger.info("Telegram notifier initialized")

# Pass to SignatureService
_signature_service = SignatureService(
    _safina_client,
    db,
    telegram_notifier=telegram_notifier
)
```

#### 1.4: Update .env
**File:** `backend/.env` or `ORGON/config/.env.example`

```bash
# Telegram Notifications
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**Tests:** `backend/tests/test_telegram_notifier.py` (10 tests)

---

### Step 2: ASAGENT Gateway Integration

#### 2.1: ASAGENT Bridge Module
**File:** `backend/integrations/asagent_bridge.py` (NEW)

**Purpose:** Connect ORGON to ASAGENT Gateway

**Class Design:**
```python
class ASAGENTBridge:
    def __init__(self, gateway_url: str = "http://localhost:8000"):
        self.gateway_url = gateway_url

    async def register_orgon_skills(self):
        """Register ORGON skills with ASAGENT."""
        skills = [
            {
                "name": "orgon_wallet_balance",
                "description": "Get wallet balance from ORGON",
                "parameters": {"wallet_name": "string"},
            },
            {
                "name": "orgon_send_transaction",
                "description": "Send transaction via ORGON",
                "parameters": {
                    "token": "string",
                    "to_address": "string",
                    "value": "string",
                },
            },
            {
                "name": "orgon_pending_signatures",
                "description": "Get pending signatures from ORGON",
            },
        ]
        # Register with ASAGENT Gateway

    async def handle_skill_call(self, skill_name: str, params: dict) -> dict:
        """Handle skill execution from ASAGENT."""
```

#### 2.2: ASAGENT Webhook Endpoint
**File:** `backend/api/routes_webhooks.py` (NEW)

**Endpoint:**
```python
@router.post("/webhooks/asagent")
async def asagent_webhook(request: dict):
    """
    Receive skill calls from ASAGENT Gateway.

    Request:
    {
        "skill": "orgon_wallet_balance",
        "params": {"wallet_name": "WALLET1"}
    }
    """
    bridge = get_asagent_bridge()
    result = await bridge.handle_skill_call(
        request["skill"],
        request["params"]
    )
    return result
```

#### 2.3: Update ASAGENT Gateway Skills
**File:** `asagent/gateway/skills/builtin.py`

**Add ORGON Commands:**
```python
async def handle_command(message: Message):
    text = message.text

    if text.startswith("/balance"):
        # Call ORGON API
        wallet_name = text.split()[1] if len(text.split()) > 1 else None
        result = await call_orgon_api("/api/wallets")
        # Format and send response

    elif text.startswith("/pending"):
        # Get pending signatures from ORGON
        result = await call_orgon_api("/api/signatures/pending")
        # Format and send response

    elif text.startswith("/approve"):
        # Approve transaction
        tx_unid = text.split()[1]
        result = await call_orgon_api(f"/api/signatures/{tx_unid}/sign", method="POST")
```

---

### Step 3: Enhanced Features

#### 3.1: USD Price Conversion
**File:** `backend/integrations/price_service.py` (NEW)

**Purpose:** Get USD prices for tokens

**API:** CoinGecko Free API
```python
class PriceService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes

    async def get_price(self, symbol: str) -> Optional[float]:
        """Get USD price for token symbol."""
        # Check cache
        # Call CoinGecko API
        # Return price or None

    async def get_prices_bulk(self, symbols: list[str]) -> dict[str, float]:
        """Get prices for multiple tokens."""
```

**Integration:**
- Add to BalanceService
- Display in frontend TokenSummary
- Show in dashboard stats

#### 3.2: Transaction Export (CSV)
**File:** `backend/api/routes_export.py` (NEW)

**Endpoint:**
```python
@router.get("/export/transactions")
async def export_transactions(
    format: str = "csv",
    wallet: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """
    Export transactions to CSV.

    Returns CSV file download.
    """
    service = get_transaction_service()
    transactions = await service.list_transactions(
        limit=10000,
        filters={
            "wallet_name": wallet,
            "from_date": from_date,
            "to_date": to_date,
        }
    )

    # Generate CSV
    csv_content = generate_csv(transactions)

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=transactions_{date}.csv"
        }
    )
```

**Frontend:**
- Add "Export" button to transactions page
- Download CSV file

#### 3.3: QR Code Generation
**File:** `backend/integrations/qr_service.py` (NEW)

**Purpose:** Generate QR codes for addresses

**Library:** `qrcode` (Python)

```python
class QRService:
    @staticmethod
    def generate_qr(data: str, size: int = 300) -> bytes:
        """Generate QR code PNG."""
        import qrcode
        from io import BytesIO

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
```

**API Endpoint:**
```python
@router.get("/qr/{address}")
async def generate_qr_code(address: str):
    """Generate QR code for address."""
    qr_bytes = QRService.generate_qr(address)
    return Response(content=qr_bytes, media_type="image/png")
```

**Frontend:**
- Show QR code in wallet details
- Modal popup with QR code

---

### Step 4: Production Polish

#### 4.1: Structured Logging
**File:** `backend/utils/logging.py` (NEW)

**Features:**
- JSON structured logs
- Request ID tracking
- Performance metrics
- Error context

#### 4.2: Health Check Enhancement
**File:** `backend/api/routes_health.py` (enhance)

**Add Detailed Health:**
```python
@router.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": check_database(),
            "safina_api": await check_safina_api(),
            "telegram": check_telegram(),
            "cache": get_cache_health(),
        },
        "version": "1.0.0",
    }
```

#### 4.3: Error Handling Middleware
**File:** `backend/api/middleware.py` (enhance)

**Add:**
- Global exception handler
- 500 error logging
- User-friendly error responses
- Request tracing

#### 4.4: Rate Limiting
**File:** `backend/api/middleware.py` (enhance)

**Add Rate Limiting:**
- Per-IP rate limits
- Per-endpoint rate limits
- 429 Too Many Requests responses

---

## 📊 Expected Deliverables

### New Files (10+)
1. `backend/integrations/telegram_notifier.py` (~200 lines)
2. `backend/integrations/asagent_bridge.py` (~150 lines)
3. `backend/integrations/price_service.py` (~100 lines)
4. `backend/integrations/qr_service.py` (~50 lines)
5. `backend/api/routes_webhooks.py` (~100 lines)
6. `backend/api/routes_export.py` (~150 lines)
7. `backend/tests/test_telegram_notifier.py` (~150 lines)
8. `backend/utils/logging.py` (~100 lines)
9. `asagent/gateway/skills/orgon_integration.py` (~200 lines)
10. `PHASE4_PLAN.md` (this file)
11. `PHASE4_COMPLETE.md` (after completion)

### Modified Files (5+)
1. `backend/main.py` — Telegram & ASAGENT initialization
2. `backend/config.py` — Add integration configs
3. `backend/api/routes_health.py` — Enhance health checks
4. `backend/api/middleware.py` — Error handling, rate limiting
5. `asagent/gateway/skills/builtin.py` — Add ORGON commands
6. `requirements.txt` — Add new dependencies

### Frontend Updates (3)
1. Add "Export" button to transactions page
2. Add QR code modal to wallet details
3. Show USD prices in token summary

### Total Estimated Lines
- **Backend integrations:** ~750 lines
- **ASAGENT updates:** ~200 lines
- **Frontend updates:** ~150 lines
- **Tests:** ~150 lines
- **Documentation:** ~500 lines
- **Total:** ~1,750 lines

---

## 🧪 Testing Strategy

**Unit Tests:**
- TelegramNotifier: 10 tests
- ASAGENTBridge: 8 tests
- PriceService: 6 tests
- QRService: 4 tests
- Export: 5 tests
- **Total:** ~35 new tests

**Integration Tests:**
- Test Telegram notification flow
- Test ASAGENT skill calls
- Test CSV export with filters
- Test QR code generation

**Manual Testing:**
- Send test Telegram notification
- Trigger pending signature notification
- Execute ASAGENT commands via Telegram
- Export transactions to CSV
- Generate QR codes

---

## 📈 Success Criteria

- [ ] Telegram notifications working
- [ ] ASAGENT Gateway connected
- [ ] ORGON skills registered in ASAGENT
- [ ] Telegram bot responds to /balance, /pending, /approve
- [ ] USD price conversion working (optional)
- [ ] CSV export working
- [ ] QR code generation working (optional)
- [ ] Structured logging implemented
- [ ] Detailed health check endpoint
- [ ] Rate limiting active
- [ ] All tests passing
- [ ] Documentation complete

---

## 🔄 Phase 4 Timeline

**Step 1:** Telegram Notifier (~3 hours)
**Step 2:** ASAGENT Integration (~4 hours)
**Step 3:** Enhanced Features (~3 hours)
**Step 4:** Production Polish (~2 hours)
**Documentation:** (~1 hour)

**Total:** ~13 hours (2 work days)

---

## 🎯 Phase 4 Priority

**Must Have (P0):**
1. Telegram Notifier ✅
2. ASAGENT Bridge ✅
3. Health checks ✅

**Should Have (P1):**
4. CSV Export ✅
5. Structured logging ✅

**Nice to Have (P2):**
6. USD Price conversion
7. QR codes
8. Rate limiting

---

**Phase 4 Status:** Ready to begin ✅
**Next:** Create TelegramNotifier
**Last Updated:** 2026-02-05
