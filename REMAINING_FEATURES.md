# 📋 ORGON — Что осталось реализовать

**Обновлено:** 2026-02-06 16:50 GMT+6

---

## ✅ Уже реализовано (Week 1):

- ✅ PostgreSQL Migration (3h)
- ✅ WebSocket Real-Time Events (3h)
- ✅ Transaction Scheduling (2.5h)
- ✅ API Documentation (Swagger UI)

**Итого:** 8.5 часов, 3 killer features!

---

## 🔄 Week 1 — Осталось

### 1. **Address Book** (0.5 дня)
**Приоритет:** Средний  
**Время:** 4-6 часов

**Features:**
- Сохранение частых получателей
- Labels для адресов
- Quick select в send form
- Import/export contacts (CSV/JSON)

**Backend:**
```sql
CREATE TABLE address_book (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    address TEXT NOT NULL,
    network INTEGER,
    label TEXT,
    notes TEXT,
    favorite BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**API:**
- `GET /api/address-book` — List
- `POST /api/address-book` — Create
- `PUT /api/address-book/{id}` — Update
- `DELETE /api/address-book/{id}` — Delete

**UI:**
- Dropdown в send form
- Dedicated page `/address-book`
- Favorites star icon

---

## 🚀 Week 2 — Frontend UI

### 2. **Scheduling UI** (1 день)
**Приоритет:** Высокий  
**Время:** 8 часов

**Features:**
- DateTime picker в send form
- "Schedule" checkbox
- Calendar view upcoming transactions
- Edit/Cancel scheduled payments

**Components:**
- `<DateTimePicker />` — react-datetime-picker
- `<ScheduledTransactionCard />` — Upcoming payment card
- `<ScheduleCalendar />` — Calendar view
- `/scheduled` page — List scheduled

**Example:**
```tsx
<DateTimePicker
  value={scheduledAt}
  onChange={setScheduledAt}
  minDate={new Date()}
  format="yyyy-MM-dd HH:mm"
/>

<Checkbox
  checked={isRecurring}
  onChange={(e) => setIsRecurring(e.target.checked)}
>
  Recurring payment
</Checkbox>

{isRecurring && (
  <CronBuilder
    value={cronRule}
    onChange={setCronRule}
  />
)}
```

---

### 3. **Balance Charts** (0.5 дня)
**Приоритет:** Средний  
**Время:** 4 часов

**Features:**
- Line chart: Balance history (7/30/90 days)
- Pie chart: Token distribution
- Bar chart: Daily/weekly volume

**Library:** Chart.js or Recharts

**Components:**
- `<BalanceHistoryChart />` — Line chart
- `<TokenDistributionChart />` — Pie chart
- `<VolumeChart />` — Bar chart

---

### 4. **Enhanced Dashboard** (0.5 дня)
**Приоритет:** Низкий  
**Время:** 4 часа

**Features:**
- Live balance updates (WebSocket)
- Transaction volume today/week/month
- Network fee indicators
- Upcoming scheduled payments widget

---

## 🎯 Week 3 — Advanced Features

### 5. **Transaction Templates** (0.5 дня)
**Приоритет:** Средний  
**Время:** 4 часа

**Features:**
- Save transaction as template
- Quick send from template
- Template categories (payroll, rent, etc.)

**Backend:**
```sql
CREATE TABLE transaction_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    token TEXT NOT NULL,
    to_address TEXT NOT NULL,
    value TEXT NOT NULL,
    info TEXT,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 6. **Browser Push Notifications** (0.5 дня)
**Приоритет:** Средний  
**Время:** 4 часа

**Features:**
- Request permission
- Native browser notifications
- Custom sounds
- Action buttons (approve/reject)

**Example:**
```tsx
if (Notification.permission === "granted") {
  new Notification("Transaction Confirmed", {
    body: "100 USDT sent to T...",
    icon: "/orgon-logo.svg",
    badge: "/badge.png",
    actions: [
      { action: "view", title: "View Details" }
    ]
  });
}
```

---

### 7. **Export Enhanced** (0.25 дня)
**Приоритет:** Низкий  
**Время:** 2 часа

**Current:** CSV/JSON export  
**Add:**
- PDF reports with charts
- Excel export with formatting
- Email scheduled reports
- Custom date ranges

---

## 🏢 Enterprise Features (Phase 3)

### 8. **Multi-User Support** (1 неделя)
**Приоритет:** Будущее  
**Время:** 5-7 дней

**Features:**
- User authentication (email/password)
- Role-based permissions (admin, approver, viewer)
- Team workspaces
- Per-user activity logs

**Backend:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_permissions (
    user_id INTEGER REFERENCES users(id),
    permission TEXT NOT NULL,
    resource_id INTEGER
);
```

---

### 9. **Advanced Multi-Sig** (1 неделя)
**Приоритет:** Будущее  
**Время:** 5-7 дней

**Features:**
- Approval workflows (CEO → CFO → Accountant)
- Spending limits per role
- Time-locked approvals (24h window)
- Audit trail with immutable logs

---

### 10. **Security Enhancements** (3-5 дней)
**Приоритет:** Будущее

**Features:**
- 2FA (TOTP, hardware keys)
- IP whitelisting
- Transaction limits & daily caps
- Suspicious activity detection
- Session management

---

### 11. **Mobile App** (2-3 недели)
**Приоритет:** Будущее

**Tech Stack:**
- React Native
- Biometric auth (Face ID, Fingerprint)
- Push notifications
- QR code scanner

---

## 🎨 UX Improvements

### 12. **Dark Mode Polish** (0.25 дня)
- Smooth transitions
- System preference detection
- Per-component theme overrides

### 13. **Responsive Design** (0.5 дня)
- Mobile-first approach
- Touch-friendly buttons
- Swipe gestures

### 14. **Loading States** (0.25 дня)
- Skeleton screens
- Progress indicators
- Optimistic UI updates

### 15. **Error Handling** (0.25 дня)
- User-friendly error messages
- Retry buttons
- Error boundary components

---

## 📊 Analytics & Insights (Phase 3+)

### 16. **Spending Analytics**
- Monthly spending breakdown
- Category tagging
- Budget tracking
- Spending forecast

### 17. **Performance Dashboard**
- Transaction success rate
- Average confirmation time
- Gas fee optimization tips
- Network congestion indicators

---

## 🔧 Technical Debt

### 18. **Testing** (1 неделя)
- Unit tests (backend)
- Integration tests (API)
- E2E tests (frontend)
- Load testing

### 19. **Documentation**
- User guide
- Admin handbook
- Developer docs
- Video tutorials

### 20. **CI/CD Pipeline**
- GitHub Actions
- Automated testing
- Staging environment
- Zero-downtime deploys

---

## 📅 Recommended Roadmap

**This Week (осталось 2 дня):**
- [ ] Address Book (0.5 день)
- [ ] Scheduling UI (1 день)
- [ ] Balance Charts (0.5 день)

**Next Week (Week 2):**
- [ ] Transaction Templates
- [ ] Browser Push Notifications
- [ ] Enhanced Dashboard
- [ ] Polish & Bug Fixes

**Week 3-4:**
- [ ] Export Enhanced
- [ ] UX Improvements
- [ ] Testing
- [ ] Documentation

**Phase 3 (Future):**
- [ ] Multi-User Support
- [ ] Advanced Multi-Sig
- [ ] Security Enhancements
- [ ] Mobile App

---

## 🎯 Quick Wins (можно сделать сегодня):

1. **Address Book** — 4 часа, максимум value
2. **Balance Charts** — 4 часа, visual impact
3. **Browser Notifications** — 4 часа, wow-эффект

---

**Total Remaining (Week 1):** ~12 часов  
**Total Phase 2:** ~80 часов (2 недели)  
**Total Phase 3:** ~200 часов (4-6 недель)

**MVP Status:** ✅ 90% Complete  
**Production Ready:** ✅ Yes (базовые фичи работают)
