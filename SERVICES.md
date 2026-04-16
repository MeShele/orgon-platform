# ORGON Services Manifest

> Registry of all backend services. Check here before creating new services.

## Service Layer (`backend/services/`)

### WalletService (`wallet_service.py`)
**Purpose:** Wallet CRUD and synchronization

**Methods:**
- `list_wallets()` — Get cached wallets, sync if empty
- `get_wallet(name)` — Get wallet details from Safina + local DB
- `get_wallet_tokens(wallet_name)` — Get tokens for a wallet
- `create_wallet(request)` — Create new wallet via Safina API
- `sync_wallets()` — Sync wallets from Safina to local DB
- `update_label(name, label)` — Update local wallet label
- `toggle_favorite(name)` — Toggle favorite status

**Status:** ✅ Complete

---

### NetworkService (`network_service.py`)
**Purpose:** Network and token reference data with caching

**Features:**
- Caches networks and tokens_info with 1-hour TTL
- Falls back to stale cache if Safina API unavailable
- Background refresh support (every hour via scheduler)

**Methods:**
- `get_networks(status, force_refresh)` — Get networks with caching
- `get_tokens_info(force_refresh)` — Get token commission info with caching
- `refresh_cache()` — Background task to refresh both caches
- `get_network_by_id(network_id)` — Get specific network by ID
- `get_token_info(token)` — Get commission info for specific token
- `get_cache_stats()` — Get cache statistics for monitoring

**Cache TTL:** 3600 seconds (1 hour)

**Database Tables:**
- `networks_cache` — Cached network directory
- `tokens_info_cache` — Cached token commission info
- `sync_state` — Cache freshness tracking

**Status:** ✅ Complete (Phase 1)

---

### TransactionService (`transaction_service.py`)
**Purpose:** Transaction management, validation, and history

**Methods:**
- `list_transactions(limit, offset)` — Get cached transactions
- `get_transaction(unid)` — Get transaction details with signatures
- `send_transaction(request, validate)` — Send transaction with optional validation
- `sign_transaction(tx_unid)` — Sign (approve) transaction
- `reject_transaction(tx_unid, reason)` — Reject transaction
- `get_pending_signatures()` — Get transactions awaiting signature
- `get_tx_signatures(tx_unid)` — Get all signatures for transaction
- `sync_transactions()` — Sync transactions from Safina

**Validation Helpers (Phase 1 enhancements):**
- `format_token(network_id, token_symbol, wallet_name)` — Format token for Safina
- `convert_decimal_to_safina(value)` — Convert "10.5" → "10,5"
- `convert_decimal_from_safina(value)` — Convert "10,5" → "10.5"
- `validate_transaction(token, to_address, value, check_balance)` — Comprehensive validation

**Validation Features:**
- ✅ Token format validation (network:::TOKEN###wallet_name)
- ✅ Address format validation
- ✅ Amount validation (> 0, valid decimal)
- ✅ Balance sufficiency check
- ✅ Automatic decimal separator conversion (. → ,)

**Status:** ✅ Complete (Phase 1)

---

### SyncService (`sync_service.py`)
**Purpose:** General synchronization orchestration

**Methods:**
- `sync_all()` — Full data sync
- `sync_balances()` — Sync token balances
- (Additional methods TBD)

**Status:** ⚠️ Partial

---

### BalanceService (`balance_service.py`)
**Purpose:** Token balance tracking and history

**Methods:**
- `get_all_balances()` — Get all user tokens with balances
- `get_summary()` — Get aggregated token balances
- `record_balance_snapshot()` — Record balance history
- (Additional methods TBD)

**Status:** ⚠️ Partial

---

### SignatureService (`signature_service.py`)
**Purpose:** Multi-signature transaction management

**Features:**
- Track pending signatures for users
- Sign (approve) transactions
- Reject transactions with reason
- Monitor signature progress
- Optional Telegram notifications

**Methods:**
- `get_pending_signatures(user_address)` — Get transactions awaiting signature
- `sign_transaction(tx_unid, user_address)` — Approve transaction
- `reject_transaction(tx_unid, reason)` — Reject transaction
- `get_signature_status(tx_unid)` — Get detailed signature status (progress, signed/waiting)
- `get_signed_transactions_history(user_address, limit)` — Get history of signed transactions
- `get_transaction_details(tx_unid)` — Get full transaction with signature status
- `check_new_pending_signatures()` — Background task to detect and notify new pending signatures
- `get_statistics()` — Get signature statistics for monitoring

**Database Tables:**
- `signature_history` — Local tracking of sign/reject actions
- `pending_signatures_checked` — Deduplication for notifications

**Background Tasks:**
- Checks for new pending signatures every 5 minutes
- Sends Telegram notifications (if configured)

**Status:** ✅ Complete (Phase 1)

---

### DashboardService (`dashboard_service.py`)
**Purpose:** Cross-service data aggregation for dashboard views

**Features:**
- Aggregate statistics from all services
- Generate unified activity feed
- Detect and report system alerts
- Cache performance monitoring

**Methods:**
- `get_stats()` — Get dashboard statistics (wallets, balance, tx count, pending signatures, networks, cache stats, last sync)
- `get_recent_activity(limit)` — Get combined activity feed from all services (transactions, signatures, wallets)
- `get_alerts()` — Get system alerts (pending signatures, failed transactions, low balances, sync issues, cache warnings)

**Dependencies:**
- WalletService
- TransactionService
- BalanceService
- SignatureService
- NetworkService

**Design Pattern:** Service Aggregator
- Does not directly call Safina API
- Aggregates data from other services
- Provides unified views for frontend

**Status:** ✅ Complete (Phase 2)

---

## Service Architecture

```
FastAPI Routes (backend/api/)
         ↓
Service Layer (backend/services/)
         ↓
Safina Client (backend/safina/client.py)
         ↓
Safina Pay API (my.safina.pro/ece/)
```

**Service Responsibilities:**
- Business logic and validation
- Caching strategies
- Error handling
- Database operations
- Orchestration of Safina client calls

**What Services DON'T Do:**
- HTTP requests (delegated to SafinaClient)
- Response formatting (delegated to API routes)
- Authentication (handled by SafinaClient EC signing)

---

## Background Tasks

Scheduled via APScheduler (`backend/tasks/scheduler.py`):

| Task | Interval | Service | Purpose |
|------|----------|---------|---------|
| `sync_balances` | 5 minutes | SyncService | Sync token balances |
| `check_pending_tx` | 1 minute | TransactionService | Check pending transactions |
| `sync_full` | 1 hour | SyncService | Full data sync |
| `refresh_network_cache` | 1 hour | NetworkService | Refresh network cache |

---

## Testing

Unit tests location: `backend/tests/test_*_service.py`

**Coverage Target:** >80%

**Test Pattern:**
```python
@pytest.fixture
def mock_client():
    """Mock SafinaPayClient."""
    return AsyncMock()

@pytest.fixture
def mock_db():
    """Mock Database."""
    return MagicMock()

@pytest.fixture
def service(mock_client, mock_db):
    """Service instance with mocked dependencies."""
    return MyService(mock_client, mock_db)

@pytest.mark.asyncio
async def test_my_method(service, mock_client):
    # Arrange
    mock_client.some_method = AsyncMock(return_value=expected_data)

    # Act
    result = await service.my_method()

    # Assert
    assert result == expected_data
```

---

## Adding a New Service

1. Create `backend/services/my_service.py`
2. Follow existing service pattern:
   ```python
   class MyService:
       def __init__(self, client: SafinaPayClient, db: Database):
           self._client = client
           self._db = db
   ```
3. Add to `backend/main.py`:
   - Import service
   - Add global variable
   - Create getter function
   - Initialize in lifespan
4. Create unit tests in `backend/tests/test_my_service.py`
5. Update this manifest

---

**Last Updated:** 2026-02-05 (Phase 2: DashboardService)
**Next:** Phase 3 — Frontend components
