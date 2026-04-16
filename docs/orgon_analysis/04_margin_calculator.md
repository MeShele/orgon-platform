# Калькулятор маржи и взаиморасчётов ORGON

**Дата:** 13 февраля 2026  
**Версия:** 1.0  
**Статус:** Финальная версия  

---

## 🎯 Обзор модели маржинальности

ORGON Platform работает на основе многоуровневой комиссионной модели, где каждый участник цепочки получает справедливую долю от создаваемой ценности. Основные принципы ценообразования:

1. **Pay-for-Value** — клиент платит за реальную ценность (хранение активов, оборот, compliance)
2. **Прогрессивность** — чем больше объём, тем меньше относительная комиссия
3. **Прозрачность** — все комиссии и расчёты видны клиенту
4. **Competitive Advantage** — наши цены значительно ниже BitGo/Fireblocks для СНГ рынка

---

## 💰 Трёхуровневая тарифная модель

### Тариф A: "Start" (Малые обменники, финтех)
- **Целевая аудитория:** Объём активов под управлением (AUC) до $100K, оборот до $50K/месяц
- **Модель оплаты:** Pay-as-you-go (оплата по факту использования)

| Параметр | Значение | Формула расчёта |
|----------|----------|-----------------|
| Setup Fee | $0 — $200 | Базовая настройка (1-2 часа работы) |
| Абонентская плата | $0 — $50/мес | За доступ к платформе |
| Комиссия за хранение | 0% | Бесплатное хранение до $100K AUC |
| Комиссия транзакций | 0,2% — 0,5% | От суммы транзакции, мин. $0,5 |
| Комиссия криптоэквайринг | 0,8% — 1,2% | Для приёма платежей от клиентов |
| Комиссия блокчейна | По факту + 20% | Bitcoin: $2-5, Ethereum: $3-15, Tron: $1 |
| KYC/AML проверки | $0,5 — $1/проверка | Автоматическая проверка через Sumsub |
| Лимиты | 1000 кошельков/мес | 5000 транзакций/мес |

### Тариф B: "Business" (Средние биржи, брокеры)
- **Целевая аудитория:** AUC $100K — $10M, оборот $100K — $1M/месяц
- **Модель оплаты:** Фиксированная лицензия + комиссии с объёма

| Параметр | Значение | Формула расчёта |
|----------|----------|-----------------|
| Setup Fee | $1,000 — $2,000 | Профессиональное внедрение (2-5 дней) |
| Абонентская плата | $300 — $800/мес | Фиксированная лицензия |
| Комиссия за хранение | 15-25 bps/год | 0,15-0,25% годовых от среднего AUC |
| Комиссия транзакций | 0,1% — 0,3% | Первые 10,000 транзакций — 0,1% |
| Комиссия криптоэквайринг | 0,6% — 0,9% | Volume discount для больших объёмов |
| Комиссия блокчейна | По факту + 15% | Оптовые тарифы |
| KYC/AML проверки | $0,3 — $0,7/проверка | Bulk pricing |
| Лимиты | 50,000 кошельков/мес | 100,000 транзакций/мес |
| Дополнительно | White-label UI | Брендинг + custom domain |

### Тариф C: "Enterprise" (Банки, крупные биржи)
- **Целевая аудитория:** AUC $10M+, оборот $1M+/месяц
- **Модель оплаты:** AUM-based (процент от активов под управлением)

| Параметр | Значение | Формула расчёта |
|----------|----------|-----------------|
| Setup Fee | $5,000 — $15,000 | Enterprise внедрение (2-4 недели) |
| Абонентская плата | $2,000 — $5,000/мес | Enterprise лицензия + SLA |
| Комиссия за хранение | 10-20 bps/год | 0,10-0,20% годовых (основной доход) |
| Комиссия транзакций | 0,05% — 0,15% | Минимальные тарифы |
| Комиссия криптоэквайринг | 0,4% — 0,7% | Premium rates |
| Комиссия блокчейна | По факту + 10% | Direct rates |
| KYC/AML проверки | $0,2 — $0,5/проверка | Enterprise rates |
| Лимиты | Без лимитов | Выделенные ресурсы |
| Дополнительно | 24/7 Support, SLA | Dedicated manager, API priority |

---

## 🔄 Цепочка комиссий и Revenue Waterfall

### Архитектура комиссий

```
Клиент обменника → Обменник → ASYSTEM → KAZ.ONE → Safina → Блокчейн
     (C11)            (EX1)    (Мы)    (Партнёр) (Инфра)  (Майнеры)
```

### Детальный breakdown для транзакции $1,000

#### Тариф B (Business): Комиссия транзакций 0,2%

```
Общая комиссия: $2,00 (0,2% от $1,000)

├─ Комиссия блокчейна: $3,00 (Bitcoin высокая нагрузка)
├─ Safina наценка: $0,45 (15% от $3,00)
├─ KAZ.ONE маржа: $0,50 (техническое обслуживание)
├─ ASYSTEM маржа: $1,05 (операционная прибыль)
└─ Обменнику к доплате: $3,00 (блокчейн превысил комиссию клиента)

Revenue Share (50/50):
├─ ASYSTEM: $0,525
└─ KAZ.ONE: $0,525

Итого клиент платит: $2,00
Итого обменник доплачивает: $3,00 (за высокие комиссии Bitcoin)
```

### Revenue Waterfall Model

#### 1. Setup Fee (100%/50% модель)
```
Клиент платит: $1,500 (Тариф B)
├─ Если внедрение выполняет ASYSTEM: ASYSTEM получает 100% ($1,500)
└─ Если привлекаем инженеров KAZ.ONE: 50/50 ($750 / $750)
```

#### 2. SaaS (Абонентская плата) — 30/70 модель
```
Клиент платит: $500/мес (Тариф B)
├─ ASYSTEM: $150 (30%) — продажи, поддержка L1, юридическое
└─ KAZ.ONE: $350 (70%) — серверы, поддержка API, обновления ПО
```

#### 3. Transaction Fees — 50/50 модель
```
Клиент платит: 0,2% от оборота
├─ ASYSTEM: 50% — рынок, клиентские отношения, compliance
└─ KAZ.ONE: 50% — технология, инфраструктура, разработка
```

#### 4. Консалтинг по токенизации — 70/30 модель
```
Клиент платит: $10,000 за выпуск токена
├─ ASYSTEM: $7,000 (70%) — юридическая экспертиза, регистрация
└─ KAZ.ONE: $3,000 (30%) — техническая реализация токена
```

---

## 👥 Профилирование клиентов и ROI

### Тип 1: Малый обменник ($50K AUC)
**Профиль:** 
- Активы под управлением: $50,000
- Месячный оборот: $25,000
- Количество клиентов: 100-200
- Транзакций в месяц: 800-1,200

**Финансовая модель (Тариф A):**
```
Доходы (в месяц):
├─ Абонентская плата: $25
├─ Комиссии с транзакций: $50 (0,2% × $25K)
├─ Комиссии блокчейна: $35 (+20% markup)
└─ KYC/AML: $40 (80 проверок × $0,5)
Итого доход ASYSTEM: $150/мес = $1,800/год

Расходы:
├─ KAZ.ONE доля (50%): $900/год
├─ Поддержка клиента: $200/год (5 часов × $40/час)
├─ Маркетинг/продажи: $300/год
└─ Операционные расходы: $150/год
Итого расходы: $1,550/год

Чистая прибыль ASYSTEM: $250/год
ROI: 16%
Payback period: 6 месяцев
```

### Тип 2: Средний обменник ($500K AUC)
**Профиль:**
- Активы под управлением: $500,000
- Месячный оборот: $200,000
- Количество клиентов: 1,000-2,000
- Транзакций в месяц: 5,000-8,000

**Финансовая модель (Тариф B):**
```
Доходы (в месяц):
├─ Абонентская плата: $500
├─ Комиссии за хранение: $625 (0,15% год от $500K ÷ 12)
├─ Комиссии с транзакций: $300 (0,15% × $200K)
├─ Комиссии блокчейна: $200 (+15% markup)
└─ KYC/AML: $175 (500 проверок × $0,35)
Итого доход ASYSTEM: $1,800/мес = $21,600/год

Revenue Share (50/50 для транзакций):
├─ ASYSTEM доля: $11,400/год
└─ KAZ.ONE доля: $10,200/год

Расходы ASYSTEM:
├─ Поддержка клиента: $800/год (20 часов × $40/час)
├─ Маркетинг/продажи: $1,500/год
└─ Операционные расходы: $600/год
Итого расходы: $2,900/год

Чистая прибыль ASYSTEM: $8,500/год
ROI: 393%
Payback period: 2 месяца
```

### Тип 3: Криптобиржа ($5M AUC)
**Профиль:**
- Активы под управлением: $5,000,000
- Месячный оборот: $2,000,000
- Количество клиентов: 10,000-20,000
- Транзакций в месяц: 50,000-80,000

**Финансовая модель (Тариф C):**
```
Доходы (в месяц):
├─ Абонентская плата: $3,000
├─ Комиссии за хранение: $8,333 (0,20% год от $5M ÷ 12)
├─ Комиссии с транзакций: $2,000 (0,10% × $2M)
├─ Комиссии блокчейна: $800 (+10% markup)
└─ KYC/AML: $1,000 (2,500 проверок × $0,4)
Итого доход ASYSTEM: $15,133/мес = $181,600/год

Revenue Share (50/50 для транзакций):
├─ ASYSTEM доля: $91,000/год
└─ KAZ.ONE доля: $90,600/год

Расходы ASYSTEM:
├─ Dedicated support: $6,000/год (150 часов × $40/час)
├─ Account manager: $12,000/год (30% FTE)
├─ Маркетинг/продажи: $8,000/год
└─ Операционные расходы: $3,000/год
Итого расходы: $29,000/год

Чистая прибыль ASYSTEM: $62,000/год
ROI: 313%
Payback period: 1,5 месяца
```

### Тип 4: Финтех компания ($2M AUC)
**Профиль:**
- Активы под управлением: $2,000,000
- Месячный оборот: $800,000
- Количество клиентов: 5,000-8,000
- Транзакций в месяц: 25,000-35,000

**Финансовая модель (Тариф B+):**
```
Доходы (в месяц):
├─ Абонентская плата: $1,500
├─ Комиссии за хранение: $2,500 (0,15% год от $2M ÷ 12)
├─ Комиссии с транзакций: $1,200 (0,15% × $800K)
├─ Криптоэквайринг: $3,600 (0,45% × $800K — основной сервис)
├─ Комиссии блокчейна: $450 (+15% markup)
└─ KYC/AML: $525 (1,500 проверок × $0,35)
Итого доход ASYSTEM: $9,775/мес = $117,300/год

Revenue Share:
├─ ASYSTEM доля: $59,000/год
└─ KAZ.ONE доля: $58,300/год

Расходы ASYSTEM:
├─ Technical support: $3,000/год (75 часов × $40/час)
├─ Integration support: $4,000/год (API помощь)
├─ Маркетинг/продажи: $5,000/год
└─ Операционные расходы: $2,500/год
Итого расходы: $14,500/год

Чистая прибыль ASYSTEM: $44,500/год
ROI: 407%
Payback period: 1,5 месяца
```

### Тип 5: Банк ($50M AUC)
**Профиль:**
- Активы под управлением: $50,000,000
- Месячный оборот: $5,000,000
- Количество клиентов: 50,000-100,000
- Транзакций в месяц: 100,000-200,000

**Финансовая модель (Тариф C Enterprise):**
```
Доходы (в месяц):
├─ Абонентская плата: $8,000
├─ Комиссии за хранение: $62,500 (0,15% год от $50M ÷ 12)
├─ Комиссии с транзакций: $4,000 (0,08% × $5M — объёмные скидки)
├─ Консалтинг токенизация: $15,000 (CBDC проекты)
├─ Комиссии блокчейна: $1,500 (+10% markup)
└─ KYC/AML Enterprise: $2,000 (10,000 × $0,2)
Итого доход ASYSTEM: $93,000/мес = $1,116,000/год

Revenue Share:
├─ ASYSTEM доля: $560,000/год
└─ KAZ.ONE доля: $556,000/год

Расходы ASYSTEM:
├─ Dedicated team: $80,000/год (2 FTE)
├─ Enterprise support: $24,000/год (600 часов × $40/час)
├─ Compliance officer: $36,000/год (0,75 FTE)
├─ Legal/regulatory: $15,000/год
├─ Маркетинг/продажи: $25,000/год
└─ Операционные расходы: $20,000/год
Итого расходы: $200,000/год

Чистая прибыль ASYSTEM: $360,000/год
ROI: 280%
Payback period: 2 месяца
```

---

## 📊 Анализ чувствительности маржи

### Оптимальные коэффициенты маржи

#### Scenario A: Консервативная маржа (10-15%)
```
Преимущества:
├─ Высокая конкурентоспособность
├─ Быстрое проникновение на рынок
├─ Лояльность клиентов
└─ Защита от конкурентов

Риски:
├─ Низкая прибыльность в краткосрочной перспективе
├─ Сложность масштабирования команды
└─ Зависимость от объёмов

ROI по типам клиентов:
├─ Малые обменники: 8-12%
├─ Средние: 150-200%
├─ Крупные биржи: 250-300%
└─ Банки: 200-250%
```

#### Scenario B: Умеренная маржа (20-30%)
```
Преимущества:
├─ Здоровая прибыльность
├─ Возможность инвестиций в R&D
├─ Качественная поддержка клиентов
└─ Финансовая стабильность

Риски:
├─ Возможная потеря ценочувствительных клиентов
└─ Привлечение конкурентов с демпингом

ROI по типам клиентов:
├─ Малые обменники: 15-25%
├─ Средние: 300-400%
├─ Крупные биржи: 400-500%
└─ Банки: 350-450%
```

#### Scenario C: Премиальная маржа (35-50%)
```
Преимущества:
├─ Высокая прибыльность
├─ Премиальный сервис
├─ Быстрое развитие продукта
└─ Возможность acquisitions

Риски:
├─ Потеря массового рынка
├─ Уход в сегмент "только для богатых"
├─ Привлечение серьёзных конкурентов
└─ Ограниченный рост клиентской базы

ROI по типам клиентов:
├─ Малые обменники: 30-50% (но мало клиентов)
├─ Средние: 500-700%
├─ Крупные биржи: 600-800%
└─ Банки: 500-700%
```

**Рекомендация:** Scenario B (20-30%) как оптимальный баланс прибыльности и роста.

---

## ⚔️ Конкурентное сравнение

### Наши цены vs BitGo vs Fireblocks

#### Для малого обменника ($50K AUC, $25K оборот/мес):

| Провайдер | Setup | Monthly Fee | Хранение | Транзакции | Итого/год |
|-----------|-------|-------------|----------|------------|-----------|
| **ORGON (Тариф A)** | $200 | $25/мес | $0 | 0,2% | **$1,700** |
| **BitGo** | $5,000 | $1,000/мес | 0,5% год | 0,25% | **$18,250** |
| **Fireblocks Essentials** | $0 | $699/мес | $0 | 0,23% | **$9,075** |
| **Экономия клиента** | vs BitGo | vs Fireblocks | | | **91% vs 81%** |

#### Для средней биржи ($5M AUC, $2M оборот/мес):

| Провайдер | Setup | Monthly Fee | Хранение | Транзакции | Итого/год |
|-----------|-------|-------------|----------|------------|-----------|
| **ORGON (Тариф C)** | $10,000 | $3,000/мес | 0,2% год | 0,1% | **$80,000** |
| **BitGo** | $10,000 | $5,000/мес | 0,4% год | 0,15% | **$126,000** |
| **Fireblocks Pro** | $0 | Enterprise | 0% | 0,16% | **$55,200** |
| **Позиция** | Средний | Средний | Лучший | Лучший | **Средний** |

#### Для банка ($50M AUC, $5M оборот/мес):

| Провайдер | Setup | Monthly Fee | Хранение | Транзакции | Итого/год |
|-----------|-------|-------------|----------|------------|-----------|
| **ORGON (Тариф C)** | $15,000 | $8,000/мес | 0,15% год | 0,08% | **$255,000** |
| **BitGo Enterprise** | $25,000 | $15,000/мес | 0,3% год | 0,1% | **$385,000** |
| **Anchorage Digital** | $50,000 | $25,000/мес | 0,6% год | 0,12% | **$672,000** |
| **Экономия клиента** | vs BitGo | vs Anchorage | | | **34% vs 62%** |

### Ключевые конкурентные преимущества:

1. **Локализация:** Понимание КР/СНГ рынка, говорим на одном языке
2. **Compliance:** Готовые решения под КР законодательство
3. **Ценовая доступность:** В 2-10 раз дешевле мировых лидеров
4. **Комплексность:** Кастоди + Эквайринг + Токенизация в одном решении
5. **Гибкость:** Настройка под специфику каждого клиента
6. **Support:** Техподдержка на русском/кыргызском языках

---

## 📈 Прогнозы на 6 месяцев

### Базовый сценарий (10 клиентов)

**Структура клиентов:**
- 5 × Малые обменники (Тариф A): $1,700 × 5 = $8,500/год
- 3 × Средние обменники (Тариф B): $21,600 × 3 = $64,800/год  
- 2 × Крупные биржи (Тариф C): $181,600 × 2 = $363,200/год

```
Финансовые результаты (6 месяцев):
├─ Общий доход: $218,250
├─ ASYSTEM доля: $110,000
├─ KAZ.ONE доля: $108,250
├─ Операционные расходы: $45,000
└─ Чистая прибыль ASYSTEM: $65,000

Ключевые метрики:
├─ ARR (Annual Recurring Revenue): $436,500
├─ MRR (Monthly Recurring Revenue): $36,375
├─ Average Revenue Per Customer: $43,650
├─ Customer Acquisition Cost: $4,500
├─ LTV/CAC: 9,7x (отличный показатель)
└─ Gross Margin: 75% (высокомаржинальный бизнес)
```

### Оптимистичный сценарий (25 клиентов)

**Структура клиентов:**
- 15 × Малые обменники: $25,500/год
- 7 × Средние обменники: $151,200/год
- 2 × Крупные биржи: $363,200/год
- 1 × Банк: $1,116,000/год

```
Финансовые результаты (6 месяцев):
├─ Общий доход: $827,950
├─ ASYSTEM доля: $415,000
├─ KAZ.ONE доля: $412,950
├─ Операционные расходы: $125,000 (масштабирование команды)
└─ Чистая прибыль ASYSTEM: $290,000

Ключевые метрики:
├─ ARR: $1,655,900
├─ MRR: $138,000
├─ Average Revenue Per Customer: $66,240
├─ Customer Acquisition Cost: $5,000
├─ LTV/CAC: 13,2x
└─ Gross Margin: 76%
```

### Пессимистичный сценарий (5 клиентов)

**Структура клиентов:**
- 3 × Малые обменники: $5,100/год
- 1 × Средний обменник: $21,600/год
- 1 × Крупная биржа: $181,600/год

```
Финансовые результаты (6 месяцев):
├─ Общий доход: $104,150
├─ ASYSTEM доля: $52,000
├─ KAZ.ONE доля: $52,150
├─ Операционные расходы: $35,000
└─ Чистая прибыль ASYSTEM: $17,000

Ключевые метрики:
├─ ARR: $208,300
├─ MRR: $17,350
├─ Average Revenue Per Customer: $41,660
├─ Customer Acquisition Cost: $7,000
├─ LTV/CAC: 5,9x (приемлемо, но требует оптимизации)
└─ Gross Margin: 67%
```

---

## 🏗️ Реализация в платформе

### База данных для трекинга комиссий

#### Таблица: commission_calculations
```sql
CREATE TABLE commission_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    transaction_id UUID REFERENCES transactions(id),
    calculation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Базовые параметры
    transaction_amount DECIMAL(20,8) NOT NULL,
    transaction_currency VARCHAR(10) NOT NULL,
    usd_rate DECIMAL(10,4) NOT NULL, -- курс к USD на момент транзакции
    auc_amount DECIMAL(20,8), -- Assets Under Custody на дату расчёта
    
    -- Применённые тарифы
    tariff_plan VARCHAR(20) NOT NULL, -- 'start', 'business', 'enterprise'
    setup_fee DECIMAL(10,2),
    monthly_fee DECIMAL(10,2),
    
    -- Комиссии (все в USD)
    custody_fee_rate DECIMAL(8,6), -- годовая ставка (например, 0.002 = 0.2%)
    custody_fee_amount DECIMAL(10,2),
    
    transaction_fee_rate DECIMAL(8,6), -- ставка с транзакции
    transaction_fee_amount DECIMAL(10,2),
    
    blockchain_fee_original DECIMAL(10,2), -- оригинальная комиссия блокчейна
    blockchain_fee_markup DECIMAL(4,2), -- наценка (например, 1.15 = +15%)
    blockchain_fee_total DECIMAL(10,2),
    
    acquiring_fee_rate DECIMAL(8,6), -- для криптоэквайринга
    acquiring_fee_amount DECIMAL(10,2),
    
    kyc_fee_amount DECIMAL(10,2),
    other_fees DECIMAL(10,2),
    
    -- Итоговые суммы
    total_client_fee DECIMAL(10,2) NOT NULL, -- что платит клиент
    total_gross_revenue DECIMAL(10,2) NOT NULL, -- общая выручка
    
    -- Revenue Share
    asystem_share_rate DECIMAL(4,2) NOT NULL, -- процент ASYSTEM (0.5 = 50%)
    asystem_revenue DECIMAL(10,2) NOT NULL,
    kazofone_revenue DECIMAL(10,2) NOT NULL,
    
    -- Метаданные
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Индексы для быстрых запросов
CREATE INDEX idx_commission_calculations_org_date ON commission_calculations(organization_id, calculation_date DESC);
CREATE INDEX idx_commission_calculations_tariff ON commission_calculations(tariff_plan, calculation_date DESC);
CREATE INDEX idx_commission_calculations_transaction ON commission_calculations(transaction_id);
```

#### Таблица: revenue_share_settlements
```sql
CREATE TABLE revenue_share_settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    settlement_period_start DATE NOT NULL,
    settlement_period_end DATE NOT NULL,
    
    -- Агрегированные данные за период
    total_transactions INTEGER NOT NULL,
    total_volume_usd DECIMAL(20,2) NOT NULL,
    total_client_fees DECIMAL(15,2) NOT NULL,
    total_gross_revenue DECIMAL(15,2) NOT NULL,
    
    -- Breakdown по типам дохода
    setup_fees DECIMAL(10,2) NOT NULL DEFAULT 0,
    monthly_fees DECIMAL(10,2) NOT NULL DEFAULT 0,
    custody_fees DECIMAL(10,2) NOT NULL DEFAULT 0,
    transaction_fees DECIMAL(10,2) NOT NULL DEFAULT 0,
    acquiring_fees DECIMAL(10,2) NOT NULL DEFAULT 0,
    consulting_fees DECIMAL(10,2) NOT NULL DEFAULT 0,
    other_revenue DECIMAL(10,2) NOT NULL DEFAULT 0,
    
    -- Revenue Share расчёт
    asystem_total_share DECIMAL(15,2) NOT NULL,
    kazofone_total_share DECIMAL(15,2) NOT NULL,
    
    -- Статус расчётов
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, confirmed, paid
    asystem_paid_at TIMESTAMP WITH TIME ZONE,
    kazofone_paid_at TIMESTAMP WITH TIME ZONE,
    
    -- Ссылки на платежи
    asystem_payment_reference VARCHAR(100),
    kazofone_payment_reference VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### API Endpoints для калькулятора

#### POST /api/v1/admin/margin-calculator
```python
from pydantic import BaseModel
from decimal import Decimal
from typing import Optional

class MarginCalculationRequest(BaseModel):
    # Входные параметры
    transaction_amount: Decimal
    transaction_currency: str
    auc_amount: Optional[Decimal] = None
    tariff_plan: str  # 'start', 'business', 'enterprise'
    transaction_type: str  # 'transfer', 'exchange', 'acquiring'
    blockchain: str  # 'bitcoin', 'ethereum', 'tron'
    kyc_checks_count: int = 0
    
    # Опциональные параметры для кастомных расчётов
    custom_transaction_rate: Optional[Decimal] = None
    custom_custody_rate: Optional[Decimal] = None

class MarginCalculationResponse(BaseModel):
    # Входные данные (echo back)
    inputs: MarginCalculationRequest
    
    # Применённые тарифы
    applied_rates: dict
    
    # Детальный breakdown
    custody_fee: Decimal
    transaction_fee: Decimal
    blockchain_fee_original: Decimal
    blockchain_fee_markup: Decimal
    blockchain_fee_total: Decimal
    acquiring_fee: Decimal
    kyc_fees: Decimal
    other_fees: Decimal
    
    # Итоги
    total_client_fee: Decimal
    gross_revenue: Decimal
    
    # Revenue Share
    asystem_revenue: Decimal
    kazofone_revenue: Decimal
    
    # Конкурентное сравнение
    bitgo_equivalent: Optional[Decimal] = None
    fireblocks_equivalent: Optional[Decimal] = None
    savings_vs_bitgo: Optional[str] = None  # "45% savings"
    savings_vs_fireblocks: Optional[str] = None

# Реализация калькулятора
async def calculate_margins(request: MarginCalculationRequest) -> MarginCalculationResponse:
    # 1. Получение текущих курсов и тарифов
    usd_rate = await get_currency_rate(request.transaction_currency)
    tariff_config = await get_tariff_config(request.tariff_plan)
    
    # 2. Расчёт комиссий
    amount_usd = request.transaction_amount * usd_rate
    
    custody_fee = 0
    if request.auc_amount and tariff_config.custody_rate > 0:
        custody_fee = request.auc_amount * tariff_config.custody_rate / 12  # месячная ставка
    
    transaction_fee = amount_usd * (request.custom_transaction_rate or tariff_config.transaction_rate)
    
    blockchain_fee = await get_blockchain_fee(request.blockchain, request.transaction_amount)
    blockchain_fee_total = blockchain_fee * tariff_config.blockchain_markup
    
    # 3. Revenue Share
    total_revenue = custody_fee + transaction_fee + (blockchain_fee_total - blockchain_fee)
    asystem_share = total_revenue * tariff_config.revenue_split.asystem
    kazofone_share = total_revenue * tariff_config.revenue_split.kazofone
    
    # 4. Конкурентное сравнение
    bitgo_fee = await calculate_competitor_fee('bitgo', request)
    fireblocks_fee = await calculate_competitor_fee('fireblocks', request)
    
    return MarginCalculationResponse(
        inputs=request,
        applied_rates=tariff_config.dict(),
        custody_fee=custody_fee,
        transaction_fee=transaction_fee,
        blockchain_fee_original=blockchain_fee,
        blockchain_fee_total=blockchain_fee_total,
        total_client_fee=custody_fee + transaction_fee + blockchain_fee_total,
        gross_revenue=total_revenue,
        asystem_revenue=asystem_share,
        kazofone_revenue=kazofone_share,
        bitgo_equivalent=bitgo_fee,
        fireblocks_equivalent=fireblocks_fee,
        savings_vs_bitgo=f"{((bitgo_fee - total_client_fee) / bitgo_fee * 100):.0f}% savings" if bitgo_fee else None
    )
```

### Frontend: Страница калькулятора в админке

#### Компонент MarginCalculator.tsx
```typescript
import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Calculator, TrendingUp, DollarSign, PieChart } from 'lucide-react';

interface MarginCalculatorProps {
  organizationId?: string; // для контекста организации
}

export function MarginCalculator({ organizationId }: MarginCalculatorProps) {
  const [inputs, setInputs] = useState({
    transactionAmount: '',
    transactionCurrency: 'USD',
    aucAmount: '',
    tariffPlan: 'business',
    transactionType: 'transfer',
    blockchain: 'bitcoin',
    kycChecksCount: '0'
  });
  
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const calculateMargins = async () => {
    setLoading(true);
    try {
      const response = await api.post('/admin/margin-calculator', {
        transaction_amount: parseFloat(inputs.transactionAmount),
        transaction_currency: inputs.transactionCurrency,
        auc_amount: inputs.aucAmount ? parseFloat(inputs.aucAmount) : null,
        tariff_plan: inputs.tariffPlan,
        transaction_type: inputs.transactionType,
        blockchain: inputs.blockchain,
        kyc_checks_count: parseInt(inputs.kycChecksCount)
      });
      setResults(response.data);
    } catch (error) {
      console.error('Calculation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Калькулятор маржи</h2>
          <p className="text-muted-foreground">
            Расчёт комиссий, прибыли и сравнение с конкурентами
          </p>
        </div>
        <Calculator className="h-8 w-8 text-blue-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Левая панель: Ввод данных */}
        <Card>
          <CardHeader>
            <CardTitle>Параметры расчёта</CardTitle>
            <CardDescription>
              Введите данные для расчёта маржинальности
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Сумма транзакции</label>
                <Input
                  type="number"
                  placeholder="1000"
                  value={inputs.transactionAmount}
                  onChange={(e) => setInputs(prev => ({ ...prev, transactionAmount: e.target.value }))}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Валюта</label>
                <Select value={inputs.transactionCurrency} onValueChange={(value) => 
                  setInputs(prev => ({ ...prev, transactionCurrency: value }))
                }>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="BTC">Bitcoin</SelectItem>
                    <SelectItem value="ETH">Ethereum</SelectItem>
                    <SelectItem value="USDT">Tether</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium">AUC (активы под управлением)</label>
              <Input
                type="number"
                placeholder="500000 (опционально)"
                value={inputs.aucAmount}
                onChange={(e) => setInputs(prev => ({ ...prev, aucAmount: e.target.value }))}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium">Тарифный план</label>
                <Select value={inputs.tariffPlan} onValueChange={(value) => 
                  setInputs(prev => ({ ...prev, tariffPlan: value }))
                }>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="start">Start (A)</SelectItem>
                    <SelectItem value="business">Business (B)</SelectItem>
                    <SelectItem value="enterprise">Enterprise (C)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Блокчейн</label>
                <Select value={inputs.blockchain} onValueChange={(value) => 
                  setInputs(prev => ({ ...prev, blockchain: value }))
                }>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bitcoin">Bitcoin</SelectItem>
                    <SelectItem value="ethereum">Ethereum</SelectItem>
                    <SelectItem value="tron">Tron</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Button 
              className="w-full" 
              onClick={calculateMargins}
              disabled={loading || !inputs.transactionAmount}
            >
              {loading ? 'Расчёт...' : 'Рассчитать маржу'}
            </Button>
          </CardContent>
        </Card>

        {/* Правая панель: Результаты */}
        {results && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PieChart className="h-5 w-5" />
                Результаты расчёта
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Основные метрики */}
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    ${results.total_client_fee.toFixed(2)}
                  </div>
                  <div className="text-sm text-green-700">Клиент платит</div>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    ${results.asystem_revenue.toFixed(2)}
                  </div>
                  <div className="text-sm text-blue-700">ASYSTEM доля</div>
                </div>
              </div>

              {/* Breakdown комиссий */}
              <div className="space-y-2">
                <h4 className="font-medium">Структура комиссий:</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span>Хранение:</span>
                    <span>${results.custody_fee.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Транзакция:</span>
                    <span>${results.transaction_fee.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Блокчейн:</span>
                    <span>${results.blockchain_fee_total.toFixed(2)}</span>
                  </div>
                  <hr />
                  <div className="flex justify-between font-medium">
                    <span>Итого:</span>
                    <span>${results.total_client_fee.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Конкурентное сравнение */}
              {results.bitgo_equivalent && (
                <div className="space-y-2">
                  <h4 className="font-medium">Сравнение с конкурентами:</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm">BitGo:</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm">${results.bitgo_equivalent.toFixed(2)}</span>
                        <Badge variant="outline" className="text-green-600 border-green-600">
                          {results.savings_vs_bitgo}
                        </Badge>
                      </div>
                    </div>
                    {results.fireblocks_equivalent && (
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Fireblocks:</span>
                        <div className="flex items-center gap-2">
                          <span className="text-sm">${results.fireblocks_equivalent.toFixed(2)}</span>
                          <Badge variant="outline" className="text-green-600 border-green-600">
                            {results.savings_vs_fireblocks}
                          </Badge>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Нижняя секция: Детальный breakdown */}
      {results && (
        <Card>
          <CardHeader>
            <CardTitle>Revenue Share детализация</CardTitle>
            <CardDescription>
              Распределение дохода между ASYSTEM и KAZ.ONE
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <TrendingUp className="h-6 w-6 mx-auto mb-2 text-blue-600" />
                <div className="text-xl font-bold text-blue-600">
                  ${results.gross_revenue.toFixed(2)}
                </div>
                <div className="text-sm text-blue-700">Общая выручка</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <DollarSign className="h-6 w-6 mx-auto mb-2 text-green-600" />
                <div className="text-xl font-bold text-green-600">
                  ${results.asystem_revenue.toFixed(2)}
                </div>
                <div className="text-sm text-green-700">ASYSTEM ({((results.asystem_revenue / results.gross_revenue) * 100).toFixed(0)}%)</div>
              </div>
              <div className="text-center p-4 bg-orange-50 rounded-lg">
                <DollarSign className="h-6 w-6 mx-auto mb-2 text-orange-600" />
                <div className="text-xl font-bold text-orange-600">
                  ${results.kazofone_revenue.toFixed(2)}
                </div>
                <div className="text-sm text-orange-700">KAZ.ONE ({((results.kazofone_revenue / results.gross_revenue) * 100).toFixed(0)}%)</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
```

### Автоматические расчёты взаиморасчётов

#### Cron Job для месячных взаиморасчётов
```python
from datetime import datetime, timedelta
from sqlalchemy import and_
import asyncio

async def monthly_revenue_settlement():
    """
    Ежемесячная задача для расчёта взаиморасчётов ASYSTEM ↔ KAZ.ONE
    Выполняется 1 числа каждого месяца в 02:00 UTC
    """
    # Период расчёта: прошлый месяц
    today = datetime.now().date()
    period_end = today.replace(day=1) - timedelta(days=1)  # последний день прошлого месяца
    period_start = period_end.replace(day=1)  # первый день прошлого месяца
    
    # Получаем все организации
    organizations = await get_active_organizations()
    
    for org in organizations:
        # Агрегируем все комиссии за период
        commission_data = await db.execute("""
            SELECT 
                COUNT(*) as total_transactions,
                SUM(transaction_amount * usd_rate) as total_volume_usd,
                SUM(total_client_fee) as total_client_fees,
                SUM(total_gross_revenue) as total_gross_revenue,
                SUM(CASE WHEN setup_fee > 0 THEN setup_fee ELSE 0 END) as setup_fees,
                SUM(custody_fee_amount) as custody_fees,
                SUM(transaction_fee_amount) as transaction_fees,
                SUM(acquiring_fee_amount) as acquiring_fees,
                SUM(asystem_revenue) as asystem_total_share,
                SUM(kazofone_revenue) as kazofone_total_share
            FROM commission_calculations 
            WHERE organization_id = %s 
            AND calculation_date >= %s 
            AND calculation_date <= %s
        """, (org.id, period_start, period_end))
        
        settlement = RevenuShareSettlement(
            organization_id=org.id,
            settlement_period_start=period_start,
            settlement_period_end=period_end,
            **commission_data.first()
        )
        
        await settlement.save()
        
        # Отправляем уведомления
        await send_settlement_notification(org, settlement)
        
    # Генерируем общий отчёт для ASYSTEM
    await generate_consolidated_settlement_report(period_start, period_end)

# Функции для работы с платежами
async def mark_settlement_as_paid(settlement_id: str, party: str, payment_reference: str):
    """
    Помечаем расчёт как оплаченный
    party: 'asystem' или 'kazofone'
    """
    settlement = await RevenuShareSettlement.get(settlement_id)
    
    if party == 'asystem':
        settlement.asystem_paid_at = datetime.now()
        settlement.asystem_payment_reference = payment_reference
    elif party == 'kazofone':
        settlement.kazofone_paid_at = datetime.now()
        settlement.kazofone_payment_reference = payment_reference
    
    # Если обе стороны подтвердили оплату, меняем статус
    if settlement.asystem_paid_at and settlement.kazofone_paid_at:
        settlement.status = 'paid'
    else:
        settlement.status = 'confirmed'
    
    await settlement.save()

# Отчёт для консолидированных расчётов
async def generate_consolidated_settlement_report(period_start: date, period_end: date):
    """
    Генерирует сводный отчёт по всем организациям за период
    """
    settlements = await RevenuShareSettlement.filter(
        settlement_period_start=period_start,
        settlement_period_end=period_end
    ).all()
    
    report_data = {
        'period': f"{period_start} - {period_end}",
        'total_organizations': len(settlements),
        'total_volume_usd': sum(s.total_volume_usd for s in settlements),
        'total_revenue': sum(s.total_gross_revenue for s in settlements),
        'asystem_total': sum(s.asystem_total_share for s in settlements),
        'kazofone_total': sum(s.kazofone_total_share for s in settlements),
        'breakdown_by_org': [
            {
                'org_name': s.organization.name,
                'volume': s.total_volume_usd,
                'revenue': s.total_gross_revenue,
                'asystem_share': s.asystem_total_share,
                'kazofone_share': s.kazofone_total_share
            }
            for s in settlements
        ]
    }
    
    # Сохраняем в файл и отправляем руководству
    report_file = await generate_excel_report(report_data)
    await send_monthly_report_email(report_file, period_start, period_end)
    
    return report_data
```

---

## 🎯 Ключевые инсайты и рекомендации

### Оптимальная стратегия ценообразования:

1. **Тариф A (Start):** Максимально низкие барьеры входа для захвата малых игроков рынка
2. **Тариф B (Business):** Сбалансированная модель для устойчивого роста
3. **Тариф C (Enterprise):** High-value клиенты с долгосрочными контрактами

### Revenue Mix для максимального ROI:

- **40% Setup fees** — высокомаржинальный доход в начале отношений
- **30% SaaS subscriptions** — предсказуемый recurring revenue
- **25% Transaction fees** — масштабируется с ростом клиентов  
- **5% Consulting** — премиальные услуги для Enterprise клиентов

### Критические факторы успеха:

1. **Retention Rate > 95%** — низкий churn критически важен для SaaS модели
2. **Time to Value < 2 недели** — быстрое внедрение для положительного first impression
3. **Net Promoter Score > 50** — довольные клиенты приводят новых клиентов
4. **Gross Margin > 70%** — здоровая маржинальность для инвестиций в R&D

Калькулятор маржи не только помогает с ценообразованием, но и становится важным sales tool для демонстрации экономии клиентам по сравнению с BitGo/Fireblocks. Это ключевое конкурентное преимущество для быстрого захвата рынка СНГ.