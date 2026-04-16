# Phase 2 Plan: REST API Endpoints Enhancement

**Date:** 2026-02-05
**Status:** In Progress
**Estimated Time:** 1-2 days

---

## 🎯 Phase 2 Goals

Complete and enhance REST API endpoints for production readiness:
1. **DashboardService** — Aggregate statistics and activity feeds
2. **Transaction API Enhancement** — Add validation, filtering, better error handling
3. **Dashboard API Enhancement** — Add stats, recent activity, alerts

---

## 📋 Current State Analysis

### ✅ Already Complete (Phase 1)
- NetworkService with caching (routes_networks.py)
- SignatureService with multi-sig (routes_signatures.py)
- TransactionService with validation helpers

### ⚠️ Needs Enhancement
- **routes_transactions.py** (95 lines)
  - Has: list, get, send, sign, reject, sync
  - Missing: validation endpoint, filtering, deprecated sign/reject warnings

- **routes_dashboard.py** (22 lines)
  - Has: /overview, /balance-history
  - Missing: /stats, /recent, /alerts

---

## 🚀 Implementation Plan

### Step 1: Create DashboardService (NEW)
**File:** `backend/services/dashboard_service.py`

**Purpose:** Aggregate data from multiple services for dashboard views

**Key Methods:**
```python
class DashboardService:
    def __init__(
        self,
        wallet_service: WalletService,
        transaction_service: TransactionService,
        balance_service: BalanceService,
        signature_service: SignatureService,
        network_service: NetworkService
    ):
        # Aggregate multiple services

    async def get_stats(self) -> dict:
        """
        Returns:
        {
            "total_wallets": 5,
            "total_balance_usd": "1234.56",
            "transactions_24h": 12,
            "pending_signatures": 3,
            "networks_active": 4,
            "last_sync": "2026-02-05T12:00:00Z"
        }
        """

    async def get_recent_activity(self, limit: int = 20) -> list[dict]:
        """
        Returns combined feed of:
        - Recent transactions
        - New signatures
        - Wallet changes
        Sorted by timestamp DESC
        """

    async def get_alerts(self) -> dict:
        """
        Returns:
        {
            "pending_signatures": 3,
            "failed_transactions": 1,
            "low_balances": [],
            "sync_issues": []
        }
        """
```

**Tests:** `backend/tests/test_dashboard_service.py` (15-20 tests)

---

### Step 2: Enhance Transaction Endpoints
**File:** `backend/api/routes_transactions.py`

**Changes:**

#### 2.1: Add Validation Endpoint
```python
@router.post("/validate", status_code=200)
async def validate_transaction(request: SendTransactionRequest):
    """
    Validate transaction before sending (pre-flight check).

    Returns:
    {
        "valid": true,
        "errors": [],
        "warnings": ["Balance check skipped - API unavailable"],
        "balance": "100.5"
    }
    """
    service = _get_service()
    try:
        result = await service.validate_transaction(
            token=request.token,
            to_address=request.to_address,
            value=request.value,
            check_balance=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

#### 2.2: Add Filtering to List Endpoint
```python
@router.get("")
async def list_transactions(
    limit: int = 50,
    offset: int = 0,
    wallet: str | None = None,      # Filter by wallet
    status: str | None = None,       # Filter by status (pending/signed/confirmed)
    network: str | None = None,      # Filter by network ID
    from_date: str | None = None,    # ISO timestamp
    to_date: str | None = None       # ISO timestamp
):
    """List transactions with filtering."""
    service = _get_service()

    # Build filters dict
    filters = {}
    if wallet:
        filters["wallet_name"] = wallet
    if status:
        filters["status"] = status
    if network:
        filters["network"] = network
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date

    return await service.list_transactions(
        limit=limit,
        offset=offset,
        filters=filters
    )
```

#### 2.3: Enhance send_transaction
```python
@router.post("", status_code=201)
async def send_transaction(
    request: SendTransactionRequest,
    validate: bool = True  # Add query param for validation toggle
):
    """
    Send a new transaction with optional validation.

    - Validation is ENABLED by default (validate=true)
    - Set validate=false to skip pre-send checks
    """
    service = _get_service()
    try:
        tx_unid = await service.send_transaction(request, validate=validate)
        return {"tx_unid": tx_unid, "status": "pending"}
    except TransactionValidationError as e:
        raise HTTPException(status_code=400, detail={"error": "Validation failed", "details": str(e)})
    except SafinaError as e:
        raise HTTPException(status_code=502, detail=str(e))
```

#### 2.4: Deprecation Warnings
Add deprecation headers to sign/reject endpoints:
```python
@router.post("/{unid}/sign")
async def sign_transaction(unid: str):
    """
    DEPRECATED: Use POST /api/signatures/{tx_unid}/sign instead.
    This endpoint will be removed in v2.0.
    """
    # ... existing code with warning header
    response.headers["X-Deprecated"] = "true"
    response.headers["X-Deprecated-Alternative"] = "/api/signatures/{tx_unid}/sign"
```

**Tests:** `backend/tests/test_routes_transactions.py` (10 tests)

---

### Step 3: Enhance Dashboard Endpoints
**File:** `backend/api/routes_dashboard.py`

**New Endpoints:**

```python
@router.get("/stats")
async def get_dashboard_stats():
    """Get aggregated dashboard statistics."""
    from backend.main import get_dashboard_service
    service = get_dashboard_service()
    return await service.get_stats()


@router.get("/recent")
async def get_recent_activity(limit: int = 20):
    """Get recent activity feed."""
    from backend.main import get_dashboard_service
    service = get_dashboard_service()
    return await service.get_recent_activity(limit=limit)


@router.get("/alerts")
async def get_alerts():
    """Get system alerts (pending signatures, failures, etc.)."""
    from backend.main import get_dashboard_service
    service = get_dashboard_service()
    return await service.get_alerts()
```

**Tests:** `backend/tests/test_routes_dashboard.py` (8 tests)

---

### Step 4: Update TransactionService for Filtering
**File:** `backend/services/transaction_service.py`

**Enhance list_transactions:**
```python
async def list_transactions(
    self,
    limit: int = 50,
    offset: int = 0,
    filters: dict | None = None
) -> list[dict]:
    """
    Get transactions with optional filtering.

    Filters:
    - wallet_name: Filter by wallet
    - status: Filter by status
    - network: Filter by network ID
    - from_date: ISO timestamp
    - to_date: ISO timestamp
    """
    query = "SELECT * FROM transactions WHERE 1=1"
    params = []

    if filters:
        if "wallet_name" in filters:
            query += " AND wallet_name = ?"
            params.append(filters["wallet_name"])
        if "status" in filters:
            query += " AND status = ?"
            params.append(filters["status"])
        if "network" in filters:
            query += " AND network = ?"
            params.append(filters["network"])
        if "from_date" in filters:
            query += " AND created_at >= ?"
            params.append(filters["from_date"])
        if "to_date" in filters:
            query += " AND created_at <= ?"
            params.append(filters["to_date"])

    query += " ORDER BY init_ts DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    txs = self._db.fetchall(query, tuple(params))

    # Auto-sync if empty
    if not txs and not filters:
        await self.sync_transactions()
        txs = self._db.fetchall(query, tuple(params))

    return txs
```

**Tests:** Add to `backend/tests/test_transaction_service.py` (5 tests)

---

### Step 5: Update main.py
**File:** `backend/main.py`

**Add DashboardService:**
```python
from backend.services.dashboard_service import DashboardService

_dashboard_service: DashboardService | None = None

def get_dashboard_service() -> DashboardService:
    return _dashboard_service

# In lifespan:
_dashboard_service = DashboardService(
    wallet_service=_wallet_service,
    transaction_service=_transaction_service,
    balance_service=_balance_service,
    signature_service=_signature_service,
    network_service=_network_service
)
```

---

## 📊 Expected Deliverables

### New Files (3)
1. `backend/services/dashboard_service.py` (~400 lines)
2. `backend/tests/test_dashboard_service.py` (~350 lines)
3. `backend/tests/test_routes_transactions.py` (~200 lines)
4. `backend/tests/test_routes_dashboard.py` (~150 lines)

### Modified Files (4)
1. `backend/services/transaction_service.py` (add filtering to list_transactions)
2. `backend/api/routes_transactions.py` (add validate endpoint, filtering, deprecation)
3. `backend/api/routes_dashboard.py` (add stats, recent, alerts)
4. `backend/main.py` (add DashboardService initialization)

### Documentation (2)
1. `PHASE2_PLAN.md` (this file)
2. `PHASE2_COMPLETE.md` (summary after completion)

---

## 🧪 Testing Strategy

**Unit Tests:**
- DashboardService: 15-20 tests
- Transaction filtering: 5 tests
- Route tests: 18 tests
- **Total:** ~40 new tests

**Integration Tests:**
- Test full dashboard stats flow
- Test transaction filtering edge cases
- Test validation endpoint with real data

**Target:** 90/90 total tests passing (50 from Phase 1 + 40 from Phase 2)

---

## 📈 Success Criteria

- [x] Plan created and reviewed
- [ ] DashboardService created with all methods
- [ ] DashboardService tests passing (15-20 tests)
- [ ] Transaction filtering implemented
- [ ] Validation endpoint added
- [ ] Dashboard endpoints enhanced (/stats, /recent, /alerts)
- [ ] All route tests passing
- [ ] Deprecation warnings added
- [ ] main.py updated with DashboardService
- [ ] Documentation complete (PHASE2_COMPLETE.md)
- [ ] All 90 tests passing

---

## 🔄 Phase 2 Timeline

**Step 1:** DashboardService creation (~2 hours)
**Step 2:** Transaction endpoints enhancement (~1 hour)
**Step 3:** Dashboard endpoints enhancement (~1 hour)
**Step 4:** TransactionService filtering (~30 minutes)
**Step 5:** Integration and testing (~1 hour)
**Step 6:** Documentation (~30 minutes)

**Total:** ~6 hours (1 work day)

---

## 🎯 Phase 2 vs Phase 1 Comparison

| Metric | Phase 1 | Phase 2 (Est.) |
|--------|---------|----------------|
| New Services | 2 (Network, Signature) | 1 (Dashboard) |
| Service Enhancements | 1 (Transaction validation) | 1 (Transaction filtering) |
| New Endpoints | 13 (networks + signatures) | 4 (validate + 3 dashboard) |
| Enhanced Endpoints | 0 | 2 (list transactions, send) |
| Unit Tests | 50 | 40 |
| Lines of Code | 1,800 | ~1,200 |
| Lines of Tests | 800 | ~700 |
| Documentation | 3,000 | ~1,500 |

---

**Phase 2 Status:** Ready to begin ✅
**Next:** Create DashboardService
**Last Updated:** 2026-02-05
