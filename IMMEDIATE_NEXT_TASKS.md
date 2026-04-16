# 🎯 ORGON - Immediate Next Tasks (Next 7 days)

## 📅 Daily Breakdown

### 🔥 Day 1 (Today) - Address Book (4 hours)

#### Task 1.1: Backend Schema & Service (2 hours)

**1. Create migration:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON/backend/database/migrations
touch 005_address_book.sql
```

**SQL:**
```sql
-- 005_address_book.sql
CREATE TABLE IF NOT EXISTS address_book (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    network TEXT,
    category TEXT CHECK (category IN ('personal', 'business', 'exchange', 'other')),
    notes TEXT,
    favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_address_book_name ON address_book(name);
CREATE INDEX idx_address_book_address ON address_book(address);
CREATE INDEX idx_address_book_favorite ON address_book(favorite);
```

**2. Create AddressBookService:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON/backend/services
touch address_book_service.py
```

**Methods:**
- `get_contacts(limit, offset, category, search)` - List with filters
- `get_contact(id)` - Get by ID
- `create_contact(name, address, network, category, notes)` - Create
- `update_contact(id, data)` - Update
- `delete_contact(id)` - Delete
- `search_contacts(query)` - Search by name/address

**3. Add API routes:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON/backend/api
touch routes_contacts.py
```

**Endpoints:**
- `GET /api/contacts`
- `POST /api/contacts`
- `GET /api/contacts/{id}`
- `PUT /api/contacts/{id}`
- `DELETE /api/contacts/{id}`
- `GET /api/contacts/search?q=...`

---

#### Task 1.2: Frontend UI (2 hours)

**1. Create Contacts page:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON/frontend/src/app
mkdir contacts
touch contacts/page.tsx
```

**Features:**
- Contact list with search
- Add/Edit/Delete buttons
- Category filter
- Favorite toggle

**2. Create Contact Modal:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON/frontend/src/components
mkdir contacts
touch contacts/ContactModal.tsx
```

**Fields:**
- Name (required)
- Address (required)
- Network (select)
- Category (select)
- Notes (textarea)
- Favorite (checkbox)

**3. Integrate with Send Transaction:**
Edit `frontend/src/app/transactions/page.tsx`:
- Add "Select from contacts" button
- Contact picker dropdown
- Auto-fill address on select

**4. Update API client:**
Edit `frontend/src/lib/api.ts`:
```typescript
// Contacts
getContacts: (params?: { limit?: number; offset?: number; category?: string; search?: string }) => ...
getContact: (id: number) => ...
createContact: (data: {...}) => ...
updateContact: (id: number, data: {...}) => ...
deleteContact: (id: number) => ...
searchContacts: (query: string) => ...
```

---

### 🚀 Day 2 - Frontend Scheduling UI (8 hours)

#### Task 2.1: DateTime Components (3 hours)

**1. Install dependencies:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON/frontend
npm install react-datepicker date-fns
npm install --save-dev @types/react-datepicker
```

**2. Create ScheduleModal:**
```bash
mkdir -p src/components/transactions
touch src/components/transactions/ScheduleModal.tsx
```

**Features:**
- Date & Time picker
- Timezone selector
- One-time vs Recurring toggle
- Cron expression builder (for recurring)
- Preview next execution times

**3. Cron Builder Component:**
```bash
touch src/components/transactions/CronBuilder.tsx
```

**UI:**
- Visual cron builder (daily/weekly/monthly presets)
- Custom cron expression input
- Validation & preview
- Examples: "Every Monday at 10:00 AM"

---

#### Task 2.2: Scheduled Transactions Page (3 hours)

**1. Create page:**
```bash
mkdir -p src/app/scheduled
touch src/app/scheduled/page.tsx
```

**Features:**
- List of scheduled transactions
- Filters: Active/Paused/Completed
- Next execution time
- Edit/Pause/Delete actions
- Status indicators

**2. Calendar View:**
```bash
npm install react-big-calendar
touch src/components/transactions/ScheduleCalendar.tsx
```

**Features:**
- Month/Week/Day views
- Scheduled payments on calendar
- Click to view details
- Color-coded by status

---

#### Task 2.3: Integration (2 hours)

**1. Add to Send Transaction form:**
- "Schedule for later" checkbox
- Opens ScheduleModal
- Submit creates scheduled transaction

**2. Update API integration:**
- Use existing `/api/scheduled` endpoints
- Add frontend state management
- Real-time updates via WebSocket

**3. Test end-to-end:**
- Create one-time scheduled transaction
- Create recurring payment
- Edit scheduled transaction
- Delete scheduled transaction
- Verify execution

---

### 📊 Day 3 - Analytics & Charts (8 hours)

#### Task 3.1: Backend Aggregation (2 hours)

**1. Create analytics endpoints:**
```bash
touch backend/api/routes_analytics.py
```

**Endpoints:**
- `GET /api/analytics/balance-history?days=30` - Time-series data
- `GET /api/analytics/transaction-volume?network=...` - By network
- `GET /api/analytics/token-distribution` - Pie chart data
- `GET /api/analytics/signature-stats` - Completion rates
- `GET /api/analytics/daily-trends?from=...&to=...` - Trends

**2. Add AnalyticsService:**
```bash
touch backend/services/analytics_service.py
```

**Methods:**
- `get_balance_history(days)` - Aggregate daily balances
- `get_transaction_volume(network, period)` - Count & value
- `get_token_distribution()` - Group by token
- `get_signature_completion_rate()` - Signed/Total ratio
- `get_daily_transaction_trends(from_date, to_date)`

---

#### Task 3.2: Frontend Charts (4 hours)

**1. Install Recharts:**
```bash
cd frontend
npm install recharts
```

**2. Create Chart Components:**
```bash
mkdir -p src/components/analytics
touch src/components/analytics/BalanceChart.tsx
touch src/components/analytics/VolumeChart.tsx
touch src/components/analytics/TokenDistribution.tsx
touch src/components/analytics/SignatureStats.tsx
touch src/components/analytics/TrendsChart.tsx
```

**3. Create Analytics Page:**
```bash
mkdir -p src/app/analytics
touch src/app/analytics/page.tsx
```

**Layout:**
- Top: Balance History (line chart)
- Middle: Token Distribution (pie) + Transaction Volume (bar)
- Bottom: Signature Stats (gauge) + Daily Trends (area)

**4. Dashboard Widgets:**
Edit `src/app/page.tsx`:
- Add mini charts to dashboard
- Link to full analytics page
- Recent trends summary

---

#### Task 3.3: Export & Filtering (2 hours)

**1. Export functionality:**
- Export chart as PNG (via recharts)
- Export data as CSV
- Export button on each chart

**2. Date range picker:**
- Quick presets (7d/30d/90d/All time)
- Custom date range
- Apply to all charts

**3. Network filter:**
- Filter charts by network
- Multi-select support
- "All networks" option

---

### 🔐 Day 4 - Audit Log (4 hours)

#### Task 4.1: Backend Audit System (2 hours)

**1. Create migration:**
```sql
-- 006_audit_log.sql
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER, -- NULL for now (single-user)
    action TEXT NOT NULL,
    resource_type TEXT, -- wallet/transaction/contact/etc
    resource_id TEXT,
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
```

**2. Create AuditService:**
```bash
touch backend/services/audit_service.py
```

**Methods:**
- `log_action(action, resource_type, resource_id, details, request)`
- `get_logs(limit, offset, action, resource_type, from_date, to_date)`
- `get_resource_history(resource_type, resource_id)`

**3. Add audit middleware:**
```bash
touch backend/api/audit_middleware.py
```

**Auto-log:**
- All POST/PUT/DELETE requests
- Critical GET requests (signatures, wallets)
- Failed auth attempts

---

#### Task 4.2: Frontend Audit UI (2 hours)

**1. Create Audit Log page:**
```bash
mkdir -p src/app/audit
touch src/app/audit/page.tsx
```

**Features:**
- Timeline view of actions
- Filters: Action type, Date range, Resource
- Search by details
- Export to CSV

**2. Resource history:**
- Show audit trail on resource detail pages
- "View history" button
- Modal with timeline

---

### 🎨 Day 5 - UI/UX Polish (8 hours)

#### Task 5.1: Responsive Design (3 hours)

**Tasks:**
- Mobile breakpoints for all pages
- Touch-friendly buttons
- Collapsible sidebars
- Bottom navigation on mobile

---

#### Task 5.2: Loading States (2 hours)

**Components:**
- Skeleton loaders for tables
- Spinner for async actions
- Progress bars for uploads
- Optimistic UI updates

---

#### Task 5.3: Error Handling (2 hours)

**Improvements:**
- User-friendly error messages
- Retry buttons
- Error boundaries
- Toast notifications for errors

---

#### Task 5.4: Accessibility (1 hour)

**Tasks:**
- ARIA labels
- Keyboard navigation
- Focus indicators
- Screen reader testing

---

### 🧪 Day 6-7 - Testing & Documentation (16 hours)

#### Day 6: Testing (8 hours)

**Backend Tests:**
- Unit tests for new services
- API endpoint tests
- Integration tests
- Load testing

**Frontend Tests:**
- Component tests (Jest + React Testing Library)
- E2E tests (Playwright)
- Visual regression tests

---

#### Day 7: Documentation (8 hours)

**User Documentation:**
- User guide (Getting Started)
- Feature tutorials (videos/screenshots)
- FAQ
- Troubleshooting

**Developer Documentation:**
- API documentation (OpenAPI/Swagger)
- Architecture overview
- Deployment guide
- Contributing guidelines

---

## 📊 Weekly Summary

| Day | Focus | Hours | Deliverables |
|-----|-------|-------|--------------|
| 1 | Address Book | 4 | Contact management ✅ |
| 2 | Scheduling UI | 8 | Calendar, DateTime picker ✅ |
| 3 | Analytics | 8 | Charts, Export ✅ |
| 4 | Audit Log | 4 | Activity tracking ✅ |
| 5 | UI Polish | 8 | Responsive, Errors, A11y ✅ |
| 6 | Testing | 8 | Full test coverage ✅ |
| 7 | Docs | 8 | User + Dev docs ✅ |
| **Total** | **7 days** | **48h** | **Production-ready MVP** |

---

## ✅ Acceptance Criteria

### Address Book:
- [ ] Can create contact with name, address, network
- [ ] Can edit/delete contacts
- [ ] Search works by name and address
- [ ] Contacts appear in Send Transaction dropdown
- [ ] Favorites pinned to top

### Scheduling UI:
- [ ] Can schedule one-time transaction
- [ ] Can schedule recurring transaction (cron)
- [ ] Calendar view shows scheduled payments
- [ ] Can edit/pause/delete scheduled transactions
- [ ] Next execution time displayed

### Analytics:
- [ ] Balance history chart (7/30/90 days)
- [ ] Token distribution pie chart
- [ ] Transaction volume by network
- [ ] Signature completion rate
- [ ] Export charts as PNG/CSV

### Audit Log:
- [ ] All actions logged automatically
- [ ] Audit log page shows timeline
- [ ] Can filter by action, date, resource
- [ ] Resource history shows on detail pages

### UI/UX:
- [ ] Mobile-responsive (320px+)
- [ ] Loading states everywhere
- [ ] Error handling with retry
- [ ] Keyboard accessible

### Testing:
- [ ] 80%+ backend test coverage
- [ ] 70%+ frontend test coverage
- [ ] E2E tests pass
- [ ] No critical bugs

### Documentation:
- [ ] User guide complete
- [ ] API docs (Swagger)
- [ ] Deployment guide
- [ ] Video tutorials

---

## 🚀 Quick Commands

```bash
# Day 1: Start Address Book
git checkout -b feature/address-book
cd /Users/urmatmyrzabekov/AGENT/ORGON

# Day 2: Scheduling UI
git checkout -b feature/scheduling-ui
cd frontend && npm install react-datepicker date-fns

# Day 3: Analytics
git checkout -b feature/analytics
cd frontend && npm install recharts

# Day 4: Audit Log
git checkout -b feature/audit-log

# Run tests
npm test
pytest

# Deploy
docker-compose build
docker-compose up -d
```

---

## 📞 Next Action

**Right now:**
```bash
cd /Users/urmatmyrzabekov/AGENT/ORGON
git checkout -b feature/address-book

# Create migration
cat > backend/database/migrations/005_address_book.sql << 'EOF'
-- (SQL from Task 1.1)
EOF

# Apply migration
psql $DATABASE_URL -f backend/database/migrations/005_address_book.sql
```

**Then:** Implement AddressBookService (see Task 1.1)

---

**Ready to start! 🚀**
