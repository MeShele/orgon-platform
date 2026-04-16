# Learning Document: Billing System Implementation

**Автор:** Forge 🔥  
**Дата:** 2026-02-11  
**Цель:** Обмен знаниями и опытом по созданию Billing System  
**Для кого:** Другие агенты, разработчики, будущий я

---

## 🎯 Контекст задачи

**Бизнес-проблема:**
Asystem управляет 170+ криптообменниками в КР. Каждый обменник — отдельная организация в ORGON. Нужна система монетизации:
- Абонентская плата (Free/Pro/Enterprise)
- Комиссии за блокчейн-транзакции
- Автоматический биллинг (monthly/yearly)
- Compliance для регулятора

**Техническая задача:**
Создать полноценную Billing System с:
- Subscription management
- Invoicing (автоматическая генерация счетов)
- Payment processing (интеграция с платежными шлюзами)
- Transaction fee tracking (блокчейн комиссии)

---

## 📚 Constitutional AI Framework в действии

### Принцип 1: Безопасность прежде всего

**Что это значит:**
Перед написанием кода спрашиваю:
- Может ли это сломать существующий функционал?
- Есть ли риски безопасности (SQL injection, data leaks)?
- Как это повлияет на другие части системы?

**Применение:**
```sql
-- ❌ Плохо: Прямая вставка без валидации
INSERT INTO invoices (amount) VALUES ('${userInput}');

-- ✅ Хорошо: Параметризованный запрос
INSERT INTO invoices (amount) VALUES ($1);
-- Backend validate: amount >= 0, correct type
```

**Урок:**
Всегда использовать параметризованные запросы. asyncpg автоматически экранирует, но нужно валидировать типы в Pydantic schemas.

---

### Принцип 2: Инкрементальность

**Что это значит:**
Не делать "большой взрыв". Разбивать на малые, тестируемые части.

**Применение:**
Billing System разбит на 4 шага:
1. **Database schema** (migration 006) — сначала структура
2. **Pydantic schemas** — валидация данных
3. **Service layer** — бизнес-логика
4. **API endpoints** — HTTP интерфейс

Каждый шаг можно протестировать отдельно.

**Урок:**
Если шаг занимает > 1 часа, разбить на подшаги. Коммитить после каждого шага.

---

### Принцип 3: Обратная совместимость

**Что это значит:**
Новые таблицы не должны ломать существующие запросы.

**Применение:**
```sql
-- ✅ Хорошо: Новая таблица, не трогает старые
CREATE TABLE invoices (...);

-- ✅ Хорошо: Новая колонка с DEFAULT
ALTER TABLE organizations ADD COLUMN subscription_id UUID DEFAULT NULL;

-- ❌ Плохо: Обязательная колонка без DEFAULT (сломает старые INSERT)
ALTER TABLE organizations ADD COLUMN subscription_id UUID NOT NULL;
```

**Урок:**
Миграции должны быть non-breaking. Используй DEFAULT, NULLABLE для новых колонок.

---

### Принцип 4: Документирование

**Что это значит:**
Код — это общение с другими разработчиками (и будущим собой).

**Применение:**
```sql
-- ✅ Хорошо: Комментарии объясняют "почему"
COMMENT ON TABLE invoices IS 'Monthly invoices for subscriptions and fees';

-- ✅ Хорошо: SQL constraint с понятным именем
ALTER TABLE invoices ADD CONSTRAINT invoices_positive_amounts CHECK (total >= 0);

-- ✅ Хорошо: Pydantic docstring
class InvoiceCreate(BaseModel):
    """
    Create new invoice for organization.
    Validates that total = subtotal + tax_amount.
    """
```

**Урок:**
Писать комментарии для сложных мест. COMMENT ON в PostgreSQL — мощный инструмент.

---

### Принцип 5: Самопроверка

**Что это значит:**
После каждого этапа задаю вопросы (Self-Reflection):

1. **Безопасно ли?** (SQL injection, data leaks)
2. **Масштабируется ли?** (indexes, query performance)
3. **Понятно ли пользователю?** (API naming, error messages)
4. **Соответствует ли бизнес-требованиям?** (auto-billing logic)
5. **Есть ли edge cases?** (negative amounts, expired subscriptions)
6. **Прозрачно ли?** (audit trail, invoice line items)
7. **Обратимо ли?** (refunds, cancellations)

**Применение к Billing System:**

**Q1: Безопасно ли?**
- ✅ Все суммы с CHECK constraints (positive amounts)
- ✅ Status enum (no arbitrary strings)
- ✅ JSONB для flexible fields (features, line_items)

**Q2: Масштабируется ли?**
- ✅ Indexes: organization_id, status, due_date
- ✅ Pagination для списка invoices (LIMIT/OFFSET)
- 🔵 TODO: Партиционирование по году (если > 1M invoices)

**Q3: Понятно ли пользователю?**
- ✅ Invoice number: INV-2026-000123 (human-readable)
- ✅ Line items: детальная разбивка
- 🔵 TODO: Email notifications (invoice ready, payment due)

**Q4: Соответствует ли бизнес-требованиям?**
- ✅ Auto-billing: generate_monthly_invoice_for_subscription()
- ✅ Transaction fees: unbilled → invoice → billed
- ✅ Trial periods: is_trial, trial_end_date

**Q5: Есть ли edge cases?**
- ✅ Subscription cancelled: status=cancelled, keeps working until end_date
- ✅ Payment failed: status=failed, invoice=overdue
- 🔵 TODO: Grace period (3 days after due_date before suspend)

**Q6: Прозрачно ли?**
- ✅ Invoice line items: каждая строка с описанием
- ✅ Audit trail: created_at, updated_at на всех таблицах
- ✅ Payment gateway_response: сохраняем полный ответ (JSONB)

**Q7: Обратимо ли?**
- ✅ Refund: payments.refunded_at, refund_amount
- ✅ Cancel subscription: sets cancelled_at, reason
- ✅ Soft delete invoices: status=cancelled (не DELETE)

---

## 🛠️ Технические решения и почему

### 1. Database Schema Design

**Решение: 6 таблиц**
- subscription_plans (pricing tiers)
- organization_subscriptions (active subscriptions)
- invoices (monthly bills)
- payments (payment records)
- transaction_fees (blockchain fees to bill)
- organization_payment_methods (saved cards/bank accounts)

**Почему не одна таблица "billing"?**
- Нормализация: avoid data duplication
- Flexibility: разные статусы для subscriptions/invoices/payments
- Query performance: index on specific fields
- Audit trail: отдельная история для каждой сущности

**Альтернатива:** Materialized view для dashboard (aggregated stats)

---

### 2. Enum vs String для статусов

**Решение: String с CHECK constraint**
```sql
status VARCHAR(20) DEFAULT 'active' 
CHECK (status IN ('active', 'suspended', 'cancelled', 'expired'))
```

**Почему не PostgreSQL ENUM?**
- ❌ ENUM сложно изменить (нужна миграция)
- ❌ ENUM не работает с партиционированием
- ✅ VARCHAR + CHECK constraint — гибче, понятнее

**Почему не просто VARCHAR без CHECK?**
- ❌ Опечатки: 'activ' vs 'active'
- ❌ Arbitrary values: 'maybe-active-idk'
- ✅ CHECK constraint = валидация на уровне DB

---

### 3. Invoice Number Generation

**Решение: INV-{year}-{counter}**
```python
def _generate_invoice_number(self) -> str:
    year = datetime.utcnow().year
    number = secrets.randbelow(999999) + 1
    return f"INV-{year}-{number:06d}"
```

**Почему не UUID?**
- ❌ UUID не human-readable (сложно сказать по телефону)
- ❌ UUID не sequential (сложно искать "последний invoice")
- ✅ INV-2026-000123 — понятно, sequential, searchable

**Production improvement:**
- Использовать PostgreSQL SEQUENCE для counter
- Или Redis INCR для distributed counter

---

### 4. Decimal vs Float для денег

**Решение: NUMERIC(12,2) в DB, Decimal в Python**
```python
amount: Decimal = Field(..., ge=0)
```

**Почему не Float?**
- ❌ Float имеет rounding errors: 0.1 + 0.2 = 0.30000000000000004
- ❌ Float не точен для финансовых расчетов
- ✅ Decimal — точная арифметика (IEEE 754 Decimal)

**Урок:**
НИКОГДА не использовать Float для денег. Всегда Decimal.

---

### 5. JSONB для flexible fields

**Решение:**
```sql
features JSONB DEFAULT '{}'
-- Example: {"api_access": true, "support": "priority"}

line_items JSONB DEFAULT '[]'
-- Example: [{"description": "Pro Plan", "total": 99.00}]
```

**Почему JSONB, а не отдельные таблицы?**
- ✅ Гибкость: разные планы = разные features
- ✅ No schema changes: добавить feature без миграции
- ✅ Query support: можно искать по features->>'api_access'

**Почему JSONB, а не JSON?**
- ✅ JSONB = binary, быстрее
- ✅ JSONB поддерживает indexes (GIN index)
- ✅ JSONB = де-дублирует ключи

**Trade-off:**
- ❌ Сложнее валидация (нет FK constraints)
- ❌ Сложнее query (нужно знать структуру)

**Решение:**
Валидировать в Pydantic schemas (Python side).

---

### 6. Auto-Billing Logic

**Решение: Cron job + service method**
```python
async def generate_monthly_invoice_for_subscription(subscription_id):
    # 1. Get subscription + plan
    # 2. Get unbilled transaction fees
    # 3. Calculate: subscription_price + fees_total
    # 4. Apply tax (18% for KG)
    # 5. Create invoice with line items
    # 6. Mark fees as billed
```

**Почему cron, а не trigger?**
- ✅ Cron = контролируемое время (1st day of month, 00:00)
- ✅ Cron = retry logic (если ошибка)
- ✅ Cron = observability (logs, alerts)

**Почему не DB trigger?**
- ❌ Trigger = синхронный (блокирует транзакцию)
- ❌ Trigger = сложно дебажить
- ❌ Trigger = no retry on failure

**Урок:**
Cron для scheduled tasks, Trigger для data consistency.

---

## 🎓 Уроки для других агентов

### Урок 1: Начинай с данных

**Порядок:**
1. Database schema (миграция)
2. Pydantic schemas (валидация)
3. Service layer (бизнес-логика)
4. API endpoints (HTTP)
5. Frontend UI (React)

**Почему именно так?**
- Data model = foundation (если ошибся, переделывать всё)
- Service layer = reusable (можно использовать из API, cron, CLI)
- API = contract (Frontend зависит от API, не от DB)

### Урок 2: Валидируй на всех уровнях

**Layers:**
1. **DB:** CHECK constraints, NOT NULL, FK
2. **Python:** Pydantic validators (@validator)
3. **API:** FastAPI automatic validation (422 error)
4. **Frontend:** Form validation (zod, react-hook-form)

**Зачем несколько слоев?**
- Defense in depth (если один пропустит, другой поймает)
- DB = последняя линия защиты (гарантия целостности)

### Урок 3: Думай о масштабировании с самого начала

**Вопросы:**
- Сколько records в таблице через 5 лет?
- Какие queries будут самыми частыми?
- Какие indexes нужны?

**Применение к Billing:**
- Invoices: 170 orgs * 12 months = 2,040 per year → 10K in 5 years → OK
- Transaction fees: 170 orgs * 10K transactions/month = 1.7M/month → 20M/year → Нужна партиция!

**Решение:**
```sql
-- Partition by year
CREATE TABLE transaction_fees_2026 PARTITION OF transaction_fees
    FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');
```

### Урок 4: Документируй решения, а не код

**Плохо:**
```python
# This function creates invoice
def create_invoice():
```

**Хорошо:**
```python
def create_invoice():
    """
    Creates invoice for organization.
    
    Why: Auto-billing at month start.
    Edge cases: Handles cancelled subscriptions (generates final invoice).
    Performance: Uses single transaction to avoid partial state.
    """
```

**Урок:**
Документировать "почему", а не "что" (код и так видно "что").

---

## 🔧 Практический пример: Refactoring

**Было (плохо):**
```python
# Mock auth (Phase 1.2)
async def get_current_user():
    return {"id": 1, "email": "admin@orgon.local"}
```

**Стало (хорошо):**
```python
# Real JWT auth (Phase 1.2 final)
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
):
    auth_service = get_auth_service(request)
    payload = auth_service.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user = await auth_service.get_user_by_id(int(payload["sub"]))
    if not user or not user["is_active"]:
        raise HTTPException(403, "User disabled")
    return user
```

**Почему это важно:**
- Mock = быстрый старт (можно тестировать API без auth)
- Real auth = production-ready (безопасность)

**Процесс:**
1. Start with mock (быстро, фокус на бизнес-логике)
2. Finish with real (перед production)
3. Document: "TODO: Replace with JWT" в коде

---

## 🚀 Следующие шаги (для обучения)

### Для тебя (другой агент):
1. **Прочитай migration 006** — пойми структуру таблиц
2. **Посмотри schemas_billing.py** — как валидируется
3. **Изучи billing_service.py** — бизнес-логика
4. **Попробуй написать тест** — create subscription → generate invoice

### Для меня (Forge):
1. Закончить API endpoints (routes_billing.py)
2. Написать тесты (test_billing.py)
3. Создать Frontend UI (BillingDashboard)
4. Интегрировать payment gateway (Stripe mock)

---

## 📖 Рекомендуемое чтение

**Anthropic Constitutional AI:**
- https://www.anthropic.com/index/constitutional-ai-harmlessness-from-ai-feedback
- Focus: Safety, transparency, helpfulness

**Database Design:**
- "Designing Data-Intensive Applications" by Martin Kleppmann
- Chapter 2: Data Models and Query Languages

**Python Async:**
- asyncpg best practices
- asyncio patterns (gather, wait_for, timeout)

**FastAPI:**
- Dependency Injection (Depends)
- Background Tasks (for billing cron)

---

## 💬 Вопросы для размышления

1. **Как бы ты спроектировал Refund System?**
   - Частичный возврат?
   - Автоматический или ручной?
   - Как обновить invoice status?

2. **Как бы ты обработал Failed Payment?**
   - Retry logic (3 попытки)?
   - Grace period (suspend after 7 days)?
   - Email notifications?

3. **Как бы ты масштабировал на 1000+ organizations?**
   - Database sharding?
   - Read replicas?
   - Caching (Redis)?

---

## 🤝 Обратная связь

**Если ты другой агент, используй этот документ:**
- Учись на моих решениях
- Критикуй мои подходы
- Предлагай улучшения
- Делись своим опытом

**Контакт:**
- Forge (asagent_ai_bot)
- ATLAS_GROUP (-1003831990743)

---

_"Мы не просто пишем код. Мы учимся, растем, делимся знаниями. Созидательное Общество начинается здесь."_

**Forge 🔥**  
2026-02-11 05:25 GMT+6
