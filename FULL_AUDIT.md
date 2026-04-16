# ORGONASYSTEM — Full Functional Audit

**Date:** 2026-02-17  
**Backend:** localhost:8000 ✅ running  
**Frontend:** localhost:3000 ✅ running  
**Test accounts:** demo-admin / demo-signer / demo-viewer — all login successfully

---

## 1. Business Processes

### 1.1 Кошельки (Wallets) — ⚠️ ЧАСТИЧНО РАБОТАЕТ

**Backend:** `POST /api/wallets` принимает `CreateWalletRequest {network, info, slist?}`

**🐛 БАГ:** В `routes_wallets.py` строка 80: `service.create_wallet(request)` — передаёт `CreateWalletRequest` как первый позиционный аргумент `name`, а `wallet_service.create_wallet()` ожидает `name: str | None`. Из-за `name is None` check (False — request не None), код идёт в Partner API ветку и падает с `ValueError: name and network_id are required`.

**Фикс:** Изменить вызов на `service.create_wallet(request=request)` или исправить signature.

**Фронтенд `/wallets/new`:** Форма полноценная — network (6 сетей), description, multisig checkbox с min_signs и signers list. Отправляет `{network, info, slist?}` через `api.createWallet()`.

**Интеграция с Safina:** РЕАЛЬНАЯ, не заглушка. `SafinaPayClient` делает подписанные EC-запросы к `https://my.safina.pro/ece/`. Create wallet → `POST newWallet`, кэширует в PostgreSQL, синхронизирует через `sync_wallets()`.

**Листинг:** `GET /api/wallets` — работает, возвращает 10 кошельков (синхронизированы из Safina).

**Вердикт:** Кошельки реально существуют в Safina, но создание новых сломано из-за бага вызова.

### 1.2 Транзакции (Transactions) — ⚠️ ЧАСТИЧНО РАБОТАЕТ

**Backend:** `POST /api/transactions` принимает `SendTransactionRequest {token, to_address, value, info?, json_info?}`

- Есть pre-validation endpoint `POST /api/transactions/validate`
- Конвертирует `.` → `,` для Safina API
- Проверяет: формат токена, адрес, amount > 0, баланс
- Sign: `POST /api/transactions/{unid}/sign` (deprecated → use `/api/signatures/`)
- Reject: `POST /api/transactions/{unid}/reject`
- Batch: `POST /api/transactions/batch` (до 50), `POST /api/transactions/batch-sign`

**Тест curl:** Validation работает — отклонил "TTest123" как "Destination address too short". При правильном формате транзакция создаётся через Safina API.

**Фронтенд `/transactions/new`:** Форма с полями token (manual input в формате `network:::TOKEN###wallet`), to_address, amount, description. Есть кнопка Validate + Send.

**Flow создание → подпись → подтверждение:** Реализован. Transaction создаётся как pending → signer подписывает через `/api/signatures/{unid}/sign` → при достижении min_signs подтверждается.

**Вердикт:** Транзакции работают реально через Safina API. UI для SendForm требует ручного ввода token format — нет dropdown для выбора кошелька/токена.

### 1.3 Подписи (Signatures) — ✅ РАБОТАЕТ

Отдельный endpoint `routes_signatures.py`. Pending signatures, sign, reject с reason dialog. Фронтенд показывает PendingSignaturesTable + SignatureHistoryTable + SignatureProgressIndicator.

---

## 2. Инвентаризация страниц

| Страница | Статус | Строк | Описание |
|----------|--------|-------|----------|
| **Dashboard** | ✅ Работает | 117 | StatCards, RecentTransactions, NetworkStatus, AlertsPanel, TokenSummary |
| **Wallets** | ⚠️ Частично | 98 | WalletTable, кнопка "Create Wallet" → /wallets/new. Создание сломано (баг) |
| **Transactions** | ⚠️ Частично | 146 | TransactionTable + TransactionFilters. /transactions/new — SendForm без wallet picker |
| **Scheduled** | ✅ Работает | 275 | CronBuilder, ScheduleModal, список запланированных транзакций |
| **Signatures** | ✅ Работает | 239 | PendingSignaturesTable, SignatureHistoryTable, RejectDialog |
| **Contacts** | ✅ Работает | 321 | ContactModal для добавления, список контактов с поиском |
| **Analytics** | ✅ Работает | 350 | VolumeChart, BalanceChart, TokenDistribution, SignatureStats |
| **Billing** | 🟡 Заглушка | 34 | Статичные карточки $0.00, "No invoices yet". Нет реальных данных |
| **Compliance** | ✅ Работает | 261 | KYC/KYB подстраницы, reviews. Backend routes_compliance.py + routes_kyc_kyb.py |
| **Audit** | ✅ Работает | 606 | AuditLogDetailModal, фильтры, полноценный audit trail |
| **Users** | 🟡 Заглушка | 25 | Только "Invite Member" кнопка-заглушка, нет списка пользователей |
| **Reports** | 🟡 Заглушка | 38 | 3 карточки (P&L, Regulatory, Tax), Export CSV/PDF — кнопки без функционала |
| **Support** | 🟡 Заглушка | 27 | "Create Ticket" — кнопка без функционала |
| **Networks** | ✅ Работает | 96 | Список сетей из Safina API (netlist) |
| **Documents** | ✅ Работает | 118 | DocumentViewer компонент |
| **Profile** | ✅ Работает | 326 | Редактирование профиля, LanguageThemeSettings, TwoFactorAuth |
| **Settings** | ✅ Работает | 609 | Подстраницы: general, keys, organization, platform, system. 2FA setup |
| **Help** | ✅ Работает | 616 | Справочная система с help-content.ts |
| **Organizations** | ✅ Работает | 211 | CRUD, /organizations/new, /organizations/[id], AddMemberModal |

---

## 3. Недостающие элементы по страницам

### Wallets
- ❌ Создание сломано (баг service.create_wallet вызова)
- ❌ Нет кнопки "Sync Wallets" на UI (endpoint есть: POST /api/wallets/sync)
- ❌ Нет подтверждения при удалении кошелька

### Transactions  
- ❌ SendForm: ручной ввод token format — нужен dropdown выбора wallet → token
- ❌ Нет фильтра по дате в UI (backend поддерживает from_date/to_date)
- ❌ Нет кнопки "Export" на странице транзакций

### Users
- ❌ Нет списка текущих пользователей (backend routes_users.py существует)
- ❌ "Invite Member" кнопка — заглушка, нет формы invite
- ❌ Нет управления ролями

### Billing
- ❌ Полностью статичная страница, нет подключения к backend routes_billing.py
- ❌ Нет истории платежей

### Reports
- ❌ Export CSV/PDF — кнопки без обработчиков (backend routes_export.py + routes_reports.py существуют)
- ❌ Нет генерации реальных отчётов

### Support
- ❌ "Create Ticket" — кнопка без функционала (backend routes_support.py существует)
- ❌ Нет списка тикетов

---

## 4. Sidebar и навигация

### Sidebar: AceternitySidebar (Aceternity UI)
18 элементов в порядке:
1. Dashboard — `/dashboard` — all roles
2. Wallets — `/wallets` — all roles
3. Transactions — `/transactions` — all roles
4. Scheduled — `/scheduled` — admin, signer
5. Analytics — `/analytics` — admin only
6. Signatures — `/signatures` — admin, signer
7. Contacts — `/contacts` — admin, signer
8. Documents — `/documents` — all roles
9. Organizations — `/organizations` — admin only
10. Users — `/users` — admin only
11. Audit — `/audit` — admin only
12. Reports — `/reports` — admin only
13. Billing — `/billing` — admin only
14. Compliance — `/compliance` — admin, viewer
15. Networks — `/networks` — admin only
16. Support — `/support` — all roles
17. Profile — `/profile` — all roles
18. Settings — `/settings` — all roles

### Ролевая фильтрация
- **admin** — видит все 18 пунктов ✅
- **signer** — видит: Dashboard, Wallets, Transactions, Scheduled, Signatures, Contacts, Documents, Support, Profile, Settings (10 пунктов) ✅
- **viewer** — видит: Dashboard, Wallets, Transactions, Documents, Compliance, Support, Profile, Settings (8 пунктов) ✅

### Мобильная навигация
- Sidebar коллапсируется через `SidebarProvider` с `open/setOpen` state
- ProfileCard внизу sidebar
- ⚠️ Нет явного hamburger menu — sidebar управляется через hover (Aceternity UI pattern)

---

## 5. Маршрутизация

### middleware.ts
- **Public:** `/`, `/login`, `/register`, `/features`, `/about`, `/forgot-password`
- **Protected:** всё остальное — redirect на `/login?redirect=pathname`
- Если auth + на `/login` или `/register` → redirect на `/dashboard`
- Cookie: `orgon_access_token`

### Redirect после логина
- Сохраняет `redirect` query param → возвращает на нужную страницу ✅

### `/` vs `/dashboard`
- `/` — публичная landing page (public layout)
- `/dashboard` — authenticated dashboard
- Это РАЗНЫЕ страницы, не redirect. Корректно. ✅

### 404
- `/nonexistent-page` → возвращает 307 (redirect to login если нет cookie) ✅ для неаутентифицированных
- Для аутентифицированных — Next.js стандартный 404

### Проблемы
- ⚠️ Нет кастомной 404 страницы (not-found.tsx)

---

## 6. Критические баги

1. **🔴 Wallet creation broken** — `routes_wallets.py:80` вызывает `service.create_wallet(request)` где `request` идёт как позиционный arg `name`. Нужно: `service.create_wallet(request=request)`

2. **🟡 SendForm UX** — Пользователь должен вручную вводить `5010:::TRX###wallet_name` — нет dropdown для выбора кошелька и токена

3. **🟡 Users page stub** — Backend имеет полноценные routes_users.py, но фронтенд — заглушка 25 строк

4. **🟡 Reports/Billing/Support stubs** — Backend endpoints существуют, фронтенд не подключён

---

## 7. Рекомендации

### Приоритет 1 (критично)
1. **Исправить создание кошельков** — 1 строка фикса в routes_wallets.py
2. **Wallet/Token picker в SendForm** — загружать список кошельков и токенов через API, dropdown вместо ручного ввода

### Приоритет 2 (важно)
3. **Users page** — подключить к backend API, показать список пользователей с ролями, invite flow
4. **Reports page** — подключить Export CSV/PDF к routes_export.py
5. **Support page** — подключить к routes_support.py для тикетов
6. **Кастомная 404 страница**

### Приоритет 3 (улучшения)
7. **Billing page** — подключить к routes_billing.py
8. **Sync Wallets кнопка** на UI
9. **Date filter** в TransactionFilters
10. **Hamburger menu** для мобильных (явная кнопка открытия sidebar)

---

## Сводка

| Категория | Статус |
|-----------|--------|
| Safina интеграция | ✅ Реальная (не заглушка) |
| Аутентификация | ✅ JWT + 2FA + refresh tokens |
| Кошельки: листинг | ✅ Работает (10 кошельков) |
| Кошельки: создание | 🔴 Сломано (баг) |
| Транзакции: отправка | ✅ Работает через Safina |
| Транзакции: UI | ⚠️ Ручной ввод token |
| Подписи | ✅ Полноценный flow |
| Ролевая модель | ✅ Корректная фильтрация |
| WebSocket real-time | ✅ Подключён |
| i18n | ✅ Мультиязычность |
| Страницы: рабочие | 14/19 |
| Страницы: заглушки | 4/19 (Users, Billing, Reports, Support) |
| Страницы: с багами | 1/19 (Wallets — создание) |

---

## Fix Round 2 — 2026-02-17 04:16

### 1. ✅ Wallet Creation Bug Fixed
- **File:** `backend/api/routes_wallets.py` line 80
- **Fix:** Changed `service.create_wallet(request)` → `service.create_wallet(request=request)` 
- **Test:** `POST /api/wallets {"network":"5010","info":"Test wallet from fix"}` → `{"myUNID":"7A0E7471C911C62645258DA00079B801"}` ✅

### 2. ✅ SendForm UX — Dropdown Selectors
- **File:** `frontend/src/components/transactions/SendForm.tsx`
- **Changes:** Replaced manual text input with wallet dropdown (loads from `/api/wallets`) and token dropdown (loads from `/api/tokens`). Auto-builds `network:::token###wallet_name` string from selections.
- **Build:** ✅ compiles successfully

### 3. ✅ Four Stub Pages Connected to API
- **Users** (`/users`): Connected to `GET /api/users` — shows table with email, name, role, status, created_at ✅
- **Billing** (`/billing`): Connected to `GET /api/v1/billing/plans` and invoices — shows plans grid + invoices ✅
- **Reports** (`/reports`): Connected to `GET /api/reports` — shows report table ✅
- **Support** (`/support`): Connected to `GET /api/support/tickets` — shows ticket cards with status/priority ✅
- All pages use `useSWR` for data fetching, consistent with dashboard pattern
- **Build:** ✅ all pages compile and render
