# Phase 3 Plan: Frontend Components

**Date:** 2026-02-05
**Status:** In Progress
**Estimated Time:** 3-4 days

---

## 🎯 Phase 3 Goals

Integrate Phase 2 backend endpoints into frontend and create missing UI components:
1. **Update API Client** — Add Phase 2 endpoints
2. **Signatures Components** — Multi-sig management UI (completely missing)
3. **Enhanced Dashboard** — Use new stats, recent, alerts endpoints
4. **Transaction Filtering** — Filter UI for transactions
5. **Transaction Validation** — Pre-flight validation UI

---

## 📋 Current State Analysis

### ✅ Already Exists
**Pages:**
- ✅ Dashboard (`app/page.tsx`)
- ✅ Wallets list & details
- ✅ Transactions list, details, send form
- ✅ Networks page
- ✅ Settings page

**Components:**
- ✅ `StatCards` — Dashboard statistics
- ✅ `RecentTransactions` — Transaction feed
- ✅ `TokenSummary` — Token balances
- ✅ `NetworkStatus` — Network status grid
- ✅ `TransactionTable` — Transaction list
- ✅ `SendForm` — Send transaction form
- ✅ `WalletTable` — Wallet list
- ✅ Common components (Card, StatusBadge, LoadingSpinner, etc.)

### ⚠️ Needs Update
- **API Client (`lib/api.ts`):**
  - ❌ Missing Phase 2 endpoints (`/api/dashboard/stats`, `/api/dashboard/recent`, `/api/dashboard/alerts`)
  - ❌ Missing `/api/transactions/validate`
  - ❌ Missing transaction filtering params
  - ❌ Missing `/api/signatures/*` endpoints
  - ⚠️ Using deprecated `/api/transactions/{unid}/sign` and `/reject`

- **Dashboard (`app/page.tsx`):**
  - ⚠️ Using legacy `/api/dashboard/overview`
  - ❌ Not showing alerts
  - ❌ Not using new recent activity feed

- **Transactions:**
  - ❌ No filtering UI
  - ❌ No pre-flight validation

### ❌ Missing Completely
- **Signatures Management:**
  - No `/app/signatures/page.tsx` route
  - No signature components
  - No multi-sig UI

---

## 🚀 Implementation Plan

### Step 1: Update API Client
**File:** `frontend/src/lib/api.ts`

**Add Phase 2 Endpoints:**
```typescript
// Dashboard (Phase 2)
getDashboardStats: () => fetchAPI("/api/dashboard/stats"),
getDashboardRecent: (limit = 20) =>
  fetchAPI(`/api/dashboard/recent?limit=${limit}`),
getDashboardAlerts: () => fetchAPI("/api/dashboard/alerts"),

// Transactions (Phase 2)
validateTransaction: (data: {
  token: string;
  to_address: string;
  value: string;
  info?: string;
}) => fetchAPI("/api/transactions/validate", {
  method: "POST",
  body: JSON.stringify(data)
}),

getTransactionsFiltered: (params: {
  limit?: number;
  offset?: number;
  wallet?: string;
  status?: string;
  network?: string;
  from_date?: string;
  to_date?: string;
}) => {
  const query = new URLSearchParams(
    Object.entries(params)
      .filter(([_, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return fetchAPI(`/api/transactions?${query}`);
},

// Signatures (Phase 1 - not yet in API client)
getPendingSignaturesV2: () => fetchAPI("/api/signatures/pending"),
getSignatureHistory: (limit = 50) =>
  fetchAPI(`/api/signatures/history?limit=${limit}`),
getSignatureStatus: (txUnid: string) =>
  fetchAPI(`/api/signatures/${txUnid}/status`),
getSignatureDetails: (txUnid: string) =>
  fetchAPI(`/api/signatures/${txUnid}/details`),
signTransactionV2: (txUnid: string) =>
  fetchAPI(`/api/signatures/${txUnid}/sign`, { method: "POST" }),
rejectTransactionV2: (txUnid: string, reason = "") =>
  fetchAPI(`/api/signatures/${txUnid}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason })
  }),
getSignatureStats: () => fetchAPI("/api/signatures/stats"),

// Networks (Phase 1 - already in backend, add to client)
getCacheStats: () => fetchAPI("/api/cache/stats"),
refreshCache: () => fetchAPI("/api/cache/refresh", { method: "POST" }),
```

**Deprecation Notice:**
- Mark `signTransaction` and `rejectTransaction` as deprecated
- Add JSDoc comments pointing to new v2 methods

---

### Step 2: Create Signatures Components
**New Directory:** `frontend/src/components/signatures/`

#### 2.1: PendingSignaturesTable
**File:** `frontend/src/components/signatures/PendingSignaturesTable.tsx`

**Features:**
- Table of pending signatures
- Columns: Token, Amount, To Address, Age, Progress, Actions
- Sign/Reject buttons
- Signature progress indicator ("2/3")
- Age calculation (hours)
- Empty state

**Props:**
```typescript
interface Props {
  signatures: PendingSignature[];
  onSign: (txUnid: string) => void;
  onReject: (txUnid: string, reason: string) => void;
  loading?: boolean;
}
```

#### 2.2: SignatureHistoryTable
**File:** `frontend/src/components/signatures/SignatureHistoryTable.tsx`

**Features:**
- Table of signature history
- Columns: TX ID, Action, Timestamp, Reason
- Status badges (signed/rejected)
- Pagination
- Filter by action

#### 2.3: SignatureProgressIndicator
**File:** `frontend/src/components/signatures/SignatureProgressIndicator.tsx`

**Features:**
- Visual progress (e.g., "2/3 signed")
- Signed addresses list (with checkmarks)
- Waiting addresses list (with pending icons)
- Progress bar

**Props:**
```typescript
interface Props {
  signed: string[];
  waiting: string[];
  totalRequired: number;
  isComplete: boolean;
}
```

#### 2.4: RejectDialog
**File:** `frontend/src/components/signatures/RejectDialog.tsx`

**Features:**
- Radix UI Dialog
- Reason text input
- Confirm/Cancel buttons
- Form validation

---

### Step 3: Create Signatures Page
**File:** `frontend/src/app/signatures/page.tsx`

**Layout:**
```
┌─────────────────────────────────────────┐
│ Signatures                              │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Statistics Cards                    │ │
│ │ • Pending: 3  • Signed 24h: 12     │ │
│ │ • Rejected 24h: 1                  │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Pending Signatures (3)              │ │
│ │ [Table with Sign/Reject actions]    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Recent History                      │ │
│ │ [Signature history table]           │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

**Features:**
- Real-time updates via SWR
- Auto-refresh every 30 seconds
- Success/error notifications
- Empty states

---

### Step 4: Enhance Dashboard with Phase 2 Endpoints
**File:** `frontend/src/app/page.tsx`

**Changes:**

Replace `/api/dashboard/overview` with three Phase 2 endpoints:
```typescript
const { data: stats } = useSWR("/api/dashboard/stats", api.getDashboardStats);
const { data: recent } = useSWR("/api/dashboard/recent", () => api.getDashboardRecent(20));
const { data: alerts } = useSWR("/api/dashboard/alerts", api.getDashboardAlerts);
```

**New Layout:**
```
┌─────────────────────────────────────────┐
│ Dashboard                               │
│                                         │
│ ┌────────────────────────────┐          │
│ │ Stats Cards (Phase 2)      │          │
│ │ • Wallets: 5  • Tx 24h: 12 │          │
│ │ • Pending Sigs: 3          │          │
│ └────────────────────────────┘          │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Alerts Panel (NEW)                  │ │
│ │ ⚠️ 3 pending signatures              │ │
│ │ ❌ 1 failed transaction              │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Recent Activity (Phase 2)           │ │
│ │ [Combined feed: tx + signatures]    │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Token Summary                       │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

#### 4.1: Create AlertsPanel Component
**File:** `frontend/src/components/dashboard/AlertsPanel.tsx`

**Features:**
- Display pending signatures alert
- Display failed transactions alert
- Display cache warnings
- Click to navigate to details
- Dismissible alerts (optional)

#### 4.2: Update RecentActivity Component
**File:** `frontend/src/components/dashboard/RecentActivity.tsx` (NEW)

**Features:**
- Combined feed (transactions + signatures)
- Activity type icons
- Priority indicators
- Timestamps
- "Show more" button

#### 4.3: Update StatCards Component
**File:** `frontend/src/components/dashboard/StatCards.tsx`

**Update to use Phase 2 stats:**
```typescript
interface Props {
  stats: {
    total_wallets: number;
    transactions_24h: number;
    pending_signatures: number;
    networks_active: number;
    cache_stats: {
      networks_cache_hit: number;
      stale: boolean;
    };
  };
}
```

**Cards:**
- Total Wallets
- Transactions (24h)
- Pending Signatures (clickable → /signatures)
- Networks Active
- Cache Performance (tooltip)

---

### Step 5: Add Transaction Filtering UI
**File:** `frontend/src/app/transactions/page.tsx`

**Add Filter Bar:**
```
┌──────────────────────────────────────────┐
│ Filters:                                 │
│ [Wallet ▼] [Status ▼] [Network ▼]       │
│ [From Date] [To Date] [Apply] [Clear]   │
└──────────────────────────────────────────┘
```

**Components:**

#### 5.1: TransactionFilters Component
**File:** `frontend/src/components/transactions/TransactionFilters.tsx`

**Props:**
```typescript
interface Props {
  onFilterChange: (filters: {
    wallet?: string;
    status?: string;
    network?: string;
    from_date?: string;
    to_date?: string;
  }) => void;
  wallets: string[];
  networks: { network_id: string; network_name: string }[];
}
```

**Features:**
- Radix UI Select for dropdowns
- Date pickers
- Apply/Clear buttons
- Active filter count indicator

#### 5.2: Update TransactionTable
**File:** `frontend/src/components/transactions/TransactionTable.tsx`

**Add:**
- Pagination controls
- Filter state management
- Loading skeletons

---

### Step 6: Add Transaction Validation UI
**File:** `frontend/src/app/transactions/new/page.tsx`

**Enhance SendForm with validation:**

#### 6.1: Update SendForm Component
**File:** `frontend/src/components/transactions/SendForm.tsx`

**Add Pre-Flight Validation:**
```typescript
const [validation, setValidation] = useState<{
  valid: boolean;
  errors: string[];
  warnings: string[];
  balance?: string;
} | null>(null);

const handleValidate = async () => {
  const result = await api.validateTransaction({
    token: selectedToken,
    to_address: recipientAddress,
    value: amount,
  });
  setValidation(result);
};
```

**UI Changes:**
- "Validate" button (pre-flight check)
- Validation results display:
  - ✅ Valid → green checkmark
  - ❌ Errors → red list
  - ⚠️ Warnings → yellow list
- Disable "Send" if validation fails
- Show balance check result

**Layout:**
```
┌──────────────────────────────────────┐
│ [Token Dropdown ▼]                   │
│ [Recipient Address _______________]  │
│ [Amount _____________]               │
│                                      │
│ [Validate]  [Send Transaction]      │
│                                      │
│ ┌────────────────────────────────┐   │
│ │ Validation Results             │   │
│ │ ✅ Valid                        │   │
│ │ Balance: 100.5 TRX             │   │
│ │ ⚠️ Warning: ...                 │   │
│ └────────────────────────────────┘   │
└──────────────────────────────────────┘
```

---

### Step 7: Update Navigation
**File:** `frontend/src/components/layout/Sidebar.tsx`

**Add Signatures Link:**
```typescript
{
  name: "Signatures",
  href: "/signatures",
  icon: SignatureIcon, // From lucide-react
  badge: pendingCount // Show pending count
}
```

---

## 📊 Expected Deliverables

### New Files (15+)
1. `frontend/src/components/signatures/PendingSignaturesTable.tsx`
2. `frontend/src/components/signatures/SignatureHistoryTable.tsx`
3. `frontend/src/components/signatures/SignatureProgressIndicator.tsx`
4. `frontend/src/components/signatures/RejectDialog.tsx`
5. `frontend/src/app/signatures/page.tsx`
6. `frontend/src/components/dashboard/AlertsPanel.tsx`
7. `frontend/src/components/dashboard/RecentActivity.tsx`
8. `frontend/src/components/transactions/TransactionFilters.tsx`
9. `PHASE3_PLAN.md` (this file)
10. `PHASE3_COMPLETE.md` (after completion)

### Modified Files (8+)
1. `frontend/src/lib/api.ts` — Add Phase 2 endpoints
2. `frontend/src/app/page.tsx` — Use Phase 2 endpoints
3. `frontend/src/components/dashboard/StatCards.tsx` — Update props
4. `frontend/src/app/transactions/page.tsx` — Add filtering
5. `frontend/src/components/transactions/SendForm.tsx` — Add validation
6. `frontend/src/components/transactions/TransactionTable.tsx` — Update for filters
7. `frontend/src/components/layout/Sidebar.tsx` — Add Signatures link
8. `frontend/src/app/layout.tsx` — Add signatures route (if needed)

### Total Estimated Lines
- **Components:** ~1,500 lines
- **Pages:** ~500 lines
- **API Client:** ~100 lines
- **Total:** ~2,100 lines

---

## 🧪 Testing Strategy

**Manual Testing:**
- Test all new signature flows
- Test transaction filtering combinations
- Test pre-flight validation with valid/invalid data
- Test alert navigation
- Test responsive design (mobile/tablet/desktop)

**E2E Testing (optional):**
- Use Playwright (already in package.json)
- Test critical flows: sign transaction, reject transaction, send with validation

---

## 📈 Success Criteria

- [ ] API client updated with all Phase 2 endpoints
- [ ] Signatures page created and functional
- [ ] All signature components created
- [ ] Dashboard using Phase 2 endpoints (/stats, /recent, /alerts)
- [ ] Alerts panel showing on dashboard
- [ ] Transaction filtering UI working
- [ ] Pre-flight validation UI working
- [ ] Navigation updated with Signatures link
- [ ] All pages responsive (mobile/tablet/desktop)
- [ ] No TypeScript errors
- [ ] No console errors in browser
- [ ] Documentation complete (PHASE3_COMPLETE.md)

---

## 🔄 Phase 3 Timeline

**Step 1:** API client update (~30 minutes)
**Step 2:** Signatures components (~4 hours)
**Step 3:** Signatures page (~2 hours)
**Step 4:** Enhanced dashboard (~3 hours)
**Step 5:** Transaction filtering (~2 hours)
**Step 6:** Transaction validation UI (~2 hours)
**Step 7:** Navigation & polish (~1 hour)

**Total:** ~15 hours (2 work days)

---

**Phase 3 Status:** Ready to begin ✅
**Next:** Update API client with Phase 2 endpoints
**Last Updated:** 2026-02-05
