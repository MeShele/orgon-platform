# Phase 2: Monetization — Billing & Compliance

**Дата начала:** 2026-02-11 19:56  
**Приоритет:** ВЫСОКИЙ  
**Цель:** Биллинг система + отчетность для регулятора  
**Длительность:** 2 недели (4+4+2 дня)  
**Ответственный:** Forge

---

## Обзор

Phase 2 добавляет монетизацию и compliance в платформу ORGON:
1. **Billing System** — подписки, инвойсы, платежи, комиссии
2. **Compliance & Regulatory** — KYC/AML, отчеты для регулятора
3. **Integration Testing** — end-to-end проверка

---

## Phase 2.1: Billing System (4 дня)

### Цель
Реализовать полный биллинг-цикл:
- Управление подписками (планы, пробные периоды)
- Генерация инвойсов (автоматическая, ручная)
- Обработка платежей (mock gateway на старте)
- Transaction fees (комиссии за операции)
- Auto-billing logic (cron jobs)

### Архитектура

#### Database Schema

**Таблицы:**
1. **subscription_plans** — тарифные планы
2. **subscriptions** — активные подписки организаций
3. **invoices** — счета (автоматические + ручные)
4. **invoice_line_items** — строки инвойса (детализация)
5. **payments** — платежи по инвойсам
6. **transaction_fees** — комиссии за транзакции (withdrawal, exchange, etc.)

#### API Endpoints

```
POST   /api/billing/subscription-plans          # Создать тарифный план
GET    /api/billing/subscription-plans          # Список планов
GET    /api/billing/subscription-plans/{id}     # Детали плана
PUT    /api/billing/subscription-plans/{id}     # Обновить план
DELETE /api/billing/subscription-plans/{id}     # Удалить план

POST   /api/billing/subscriptions               # Создать подписку для org
GET    /api/billing/subscriptions               # Список подписок (filtered by org)
GET    /api/billing/subscriptions/{id}          # Детали подписки
PUT    /api/billing/subscriptions/{id}          # Обновить подписку (upgrade/downgrade)
POST   /api/billing/subscriptions/{id}/cancel   # Отменить подписку

GET    /api/billing/invoices                    # Список инвойсов (filtered by org)
GET    /api/billing/invoices/{id}               # Детали инвойса (+ line items)
POST   /api/billing/invoices                    # Создать ручной инвойс
POST   /api/billing/invoices/{id}/pay           # Оплатить инвойс (mock payment)
GET    /api/billing/invoices/{id}/pdf           # Скачать PDF инвойса

GET    /api/billing/payments                    # История платежей
GET    /api/billing/payments/{id}               # Детали платежа

POST   /api/billing/fees                        # Записать комиссию (internal)
GET    /api/billing/fees                        # Список комиссий (filtered by org)
GET    /api/billing/fees/summary                # Сводка комиссий (dashboard)
```

#### Frontend Components

**New Pages:**
- `/billing` — Dashboard (subscription, balance, invoices)
- `/billing/invoices` — Список инвойсов
- `/billing/invoices/{id}` — Детали инвойса
- `/billing/subscription` — Управление подпиской
- `/billing/plans` — Выбор тарифного плана

**New Components:**
- `SubscriptionCard` — текущая подписка + кнопка upgrade
- `InvoiceList` — таблица инвойсов с фильтрами
- `InvoiceDetail` — детальный просмотр инвойса + оплата
- `PlanSelector` — выбор тарифа (cards layout)
- `PaymentMethodForm` — форма добавления карты (mock)

---

### Этап 2.1.1: Database Design (1 день)

**Задачи:**
- [ ] Проектирование schema (6 таблиц + индексы)
- [ ] Migration script (006_billing_system.sql)
- [ ] Seed data (2 subscription plans: Starter, Professional)
- [ ] Тест миграции на dev DB

**Deliverable:** Migration applied, schema verified

---

### Этап 2.1.2: Backend API (2 дня)

**Задачи:**
- [ ] Pydantic schemas (SubscriptionPlan, Subscription, Invoice, Payment, Fee)
- [ ] BillingService (business logic)
- [ ] API routes (billing.py)
- [ ] Auto-billing cron job (generate monthly invoices)
- [ ] Unit tests (pytest)

**Deliverable:** API endpoints работают, тесты проходят

---

### Этап 2.1.3: Frontend UI (1 день)

**Задачи:**
- [ ] Billing Dashboard page
- [ ] Invoices List + Detail pages
- [ ] Subscription Management page
- [ ] Plan Selector component
- [ ] i18n translations (en/ru/ky)

**Deliverable:** UI готов, интегрирован с API

---

## Phase 2.2: Compliance & Regulatory (4 дня)

### Цель
Реализовать compliance инструменты для регулятора:
- KYC/AML записи
- Генерация отчетов (PDF, Excel, XML)
- Alerts система (suspicious activity)
- Audit trail (все действия логируются)

### Архитектура

#### Database Schema

**Таблицы:**
1. **kyc_records** — KYC данные клиентов
2. **aml_alerts** — AML тревоги (suspicious transactions)
3. **compliance_reports** — сгенерированные отчеты для регулятора
4. **audit_logs** — логи всех действий (уже есть?)

#### API Endpoints

```
POST   /api/compliance/kyc                      # Добавить KYC запись
GET    /api/compliance/kyc                      # Список KYC (filtered by org)
GET    /api/compliance/kyc/{id}                 # Детали KYC
PUT    /api/compliance/kyc/{id}                 # Обновить KYC статус
POST   /api/compliance/kyc/{id}/verify          # Верифицировать KYC

GET    /api/compliance/aml-alerts               # Список AML тревог
GET    /api/compliance/aml-alerts/{id}          # Детали тревоги
PUT    /api/compliance/aml-alerts/{id}          # Обновить статус (reviewed/resolved)

POST   /api/compliance/reports/generate         # Сгенерировать отчет
GET    /api/compliance/reports                  # Список отчетов
GET    /api/compliance/reports/{id}             # Детали отчета
GET    /api/compliance/reports/{id}/download    # Скачать отчет (PDF/Excel/XML)

GET    /api/compliance/audit-logs               # Логи действий (filtered by org)
```

#### Frontend Components

**New Pages:**
- `/compliance` — Dashboard (KYC stats, AML alerts)
- `/compliance/kyc` — Список KYC записей
- `/compliance/kyc/{id}` — Детали KYC + верификация
- `/compliance/alerts` — AML тревоги
- `/compliance/reports` — Отчеты для регулятора

**New Components:**
- `KYCStatusBadge` — статус верификации (pending/verified/rejected)
- `AMLAlertCard` — карточка тревоги
- `ReportGenerator` — форма генерации отчета (date range, format)
- `AuditLogTable` — таблица логов с фильтрами

---

### Этап 2.2.1: Database Design (1 день)

**Задачи:**
- [ ] Проектирование schema (4 таблицы + индексы)
- [ ] Migration script (007_compliance_system.sql)
- [ ] Seed data (sample KYC records, AML alerts)
- [ ] Тест миграции на dev DB

**Deliverable:** Migration applied, schema verified

---

### Этап 2.2.2: Backend API (2 дня)

**Задачи:**
- [ ] Pydantic schemas (KYCRecord, AMLAlert, ComplianceReport)
- [ ] ComplianceService (business logic)
- [ ] API routes (compliance.py)
- [ ] Report generation logic (PDF, Excel, XML)
- [ ] Unit tests (pytest)

**Deliverable:** API endpoints работают, отчеты генерируются

---

### Этап 2.2.3: Frontend UI (1 день)

**Задачи:**
- [ ] Compliance Dashboard page
- [ ] KYC List + Detail pages
- [ ] AML Alerts page
- [ ] Reports page + generator
- [ ] i18n translations (en/ru/ky)

**Deliverable:** UI готов, интегрирован с API

---

## Phase 2.3: Integration & Testing (2 дня)

### Цель
End-to-end тестирование биллинга + compliance

### Задачи

**Этап 2.3.1: E2E Testing (1 день)**
- [ ] E2E: Subscription lifecycle (create → invoice → payment → renewal)
- [ ] E2E: KYC verification flow
- [ ] E2E: AML alert → investigation → resolution
- [ ] E2E: Report generation → download

**Этап 2.3.2: Security & Documentation (1 день)**
- [ ] Security audit (PCI DSS considerations, если есть карты)
- [ ] Performance testing (invoice generation для 100+ orgs)
- [ ] API documentation (Swagger)
- [ ] User guide (Billing + Compliance)

**Deliverable:** Phase 2 COMPLETE, готов к production

---

## Success Criteria (Phase 2)

### Функциональность
- ✅ Subscription plans созданы и работают
- ✅ Invoices генерируются автоматически
- ✅ Payments обрабатываются (mock gateway)
- ✅ Transaction fees записываются
- ✅ KYC records управляются
- ✅ AML alerts отслеживаются
- ✅ Compliance reports генерируются (PDF/Excel/XML)

### Качество
- ✅ Все тесты проходят (unit + e2e)
- ✅ Code coverage > 80%
- ✅ Security audit пройден
- ✅ Performance acceptable (<1s invoice generation)

### Документация
- ✅ API documented (Swagger)
- ✅ User guides написаны
- ✅ Migration guides готовы

---

## Timeline

**Старт:** 2026-02-11 19:56  
**Планируемое завершение:** 2026-02-25 (14 дней)

```
Week 1 (Feb 11-17):
- Phase 2.1.1: Database Design (1 день)
- Phase 2.1.2: Backend API (2 дня)
- Phase 2.1.3: Frontend UI (1 день)
- Phase 2.2.1: Database Design (1 день)
- Phase 2.2.2: Backend API (start, 2 дня)

Week 2 (Feb 18-25):
- Phase 2.2.2: Backend API (finish)
- Phase 2.2.3: Frontend UI (1 день)
- Phase 2.3.1: E2E Testing (1 день)
- Phase 2.3.2: Security & Documentation (1 день)
- Buffer: 2 дня
```

---

## Risk Management

### Risks
1. **Payment Gateway Integration** — может быть сложной
   - Mitigation: Начинаем с mock, добавим реальный gateway позже
2. **Compliance Regulations** — могут измениться
   - Mitigation: Консультация с юристом, flexible report formats
3. **Performance** — invoice generation для многих orgs
   - Mitigation: Background jobs, pagination, caching

### Dependencies
- Phase 1 (Multi-Tenancy) — COMPLETE ✅
- Docker services running ✅
- PostgreSQL 16 ready ✅

---

## Next Steps

**Immediate (сейчас):**
1. Создать migration 006_billing_system.sql
2. Определить схему всех 6 таблиц
3. Применить миграцию на dev DB
4. Создать seed data (2 subscription plans)

**After Phase 2:**
- Phase 3: White Label & Fiat Gateway
- Phase 4: Production Readiness

---

**Status:** 🟢 STARTED  
**Current Stage:** Phase 2.1.1 (Database Design)  
**Lead:** Forge  
**Started:** 2026-02-11 19:56 GMT+6
