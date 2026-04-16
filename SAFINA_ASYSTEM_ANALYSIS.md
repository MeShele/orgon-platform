# Анализ документа Safina-Asystem и рекомендации по ORGON

**Дата:** 2026-02-10  
**Источник:** Google Docs (Safina - Asystem)  
**Цель:** Корректировки проекта ORGON под бизнес-модель Asystem

---

## 📋 Извлеченный контекст

### Бизнес-модель

**ОсОО "Асистем":**
- Обслуживает **170+ криптообменников** Кыргызстана
- Услуги: обслуживание горячих кошельков (через Fireblocks), отчетность перед регуляторами
- План: **White Label решение "под ключ"** для обменников

**ОсОО "Tengrisoft" (API Safina):**
- Локальная альтернатива Fireblocks
- **Устраняет политические риски** (нет зависимости от иностранных регуляторов)
- Функции: создание hot/warm кошельков, мультиподпись, исполнение транзакций, поддержка блокчейнов

### Архитектура системы

```
Payment Gateway (фиат) ← → Asystem ← → API Safina ← → Chains (Tron, BNB, ETH)
                              ↓
                         EX 1...n (обменники) ← → NB (регулятор)
                              ↓
                         C11...Cnm (клиенты)
```

### Функциональность White Label решения

- **Web, Android, iOS** приложения
- **Фиатные платежи** (интеграция с банками/платежными системами)
- **Управление кошельками** (hot/warm для обменников и их клиентов)
- **Отчетность** перед регуляторами
- **KYC/AML** интеграции (на диаграмме не указаны, но упомянуты)

### Монетизация Safina

- **Фиксированные платежи:** xxx USDT/месяц с каждого обменника
- **Комиссии блокчейна**
- **Опционально:** фиксированная плата за вывод ($0.5-$1.0/транзакция) при делегировании ресурсов

### Ключевые вопросы для расчета

1. Количество горячих кошельков обменников
2. Предполагаемое количество транзакций
3. Блокчейны для подключения
4. Режим работы (24/7 или рабочее время)
5. Служба поддержки (кто обеспечивает)
6. Распределение доходов
7. Место снятия абонентской платы
8. Учет клиентских операций
9. Взаиморасчеты

---

## 🎯 Рекомендации по корректировкам ORGON

### 1. **Multi-Tenancy (Поддержка множества обменников)** 🏢

**Текущее состояние:** ORGON работает как single-tenant платформа  
**Требуется:**

- [ ] **Organizations/Tenants** модель
  - Каждый обменник = отдельная организация (tenant)
  - Изоляция данных между обменниками
  - Общая база кода, отдельные данные

- [ ] **Раздел "Organizations"** (новый)
  - Список обменников-клиентов
  - Профили организаций (название, лицензия, контакты)
  - Статус (активный/приостановлен/архив)
  - Billing информация

- [ ] **Role-Based Access Control (RBAC)**
  - Роли: Super Admin (Asystem), Org Admin (обменник), Operator, Viewer
  - Разграничение доступа по ролям и организациям

**Файлы для изменения:**
- `frontend/src/lib/api.ts` — добавить endpoints для organizations
- `frontend/src/app/(authenticated)/organizations/` — новый раздел
- Backend: модели Organization, User-Org связь, middleware для tenant isolation

---

### 2. **Billing & Subscription Management** 💰

**Текущее состояние:** Нет биллинга  
**Требуется:**

- [ ] **Раздел "Billing"** (новый)
  - Абонентская плата (xxx USDT/месяц)
  - История платежей
  - Счета/Invoices
  - Статус подписки (активна/просрочена)
  - Автоматическое напоминание о платеже

- [ ] **Transaction Fees Tracking**
  - Опциональная фиксированная плата за вывод ($0.5-$1.0)
  - Учет комиссий блокчейна
  - Отчет по комиссиям (для прозрачности перед клиентом)

- [ ] **Dashboard Widget: Billing Summary**
  - Текущий баланс подписки
  - Дата следующего платежа
  - Задолженность (если есть)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/billing/` — новый раздел
- `frontend/src/app/(authenticated)/dashboard/page.tsx` — добавить BillingWidget
- Backend: модели Subscription, Invoice, Payment, TransactionFee

---

### 3. **Regulatory Compliance (Отчетность перед регуляторами)** 📊

**Текущее состояние:** Есть Audit раздел, но нет регуляторной отчетности  
**Требуется:**

- [ ] **Раздел "Compliance"** (новый)
  - **Отчеты для регулятора (NB)**
    - Экспорт за период (день/месяц/год)
    - Формат: PDF, Excel, XML (по требованию регулятора)
    - Автоматическая генерация по расписанию
  - **KYC/AML статус**
    - Интеграция с KYC/AML провайдерами (Sumsub, Onfido, ComplyAdvantage)
    - Статус верификации клиентов (C11...Cnm)
    - Подозрительные транзакции (AML alerts)
  - **Шаблоны отчетов**
    - Настраиваемые шаблоны для разных регуляторов
    - Автоматическая отправка email/webhook

- [ ] **Audit Enhancement**
  - Добавить фильтр "Регуляторные события" (KYC, AML, Compliance)
  - Экспорт в формате для регулятора (не только CSV/JSON)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/compliance/` — новый раздел
- `frontend/src/app/(authenticated)/audit/page.tsx` — добавить фильтр compliance events
- Backend: модели ComplianceReport, KYCRecord, AMLAlert, интеграции с KYC/AML API

---

### 4. **Payment Gateway Integration (Фиатный шлюз)** 💵

**Текущее состояние:** ORGON работает только с криптовалютами  
**Требуется:**

- [ ] **Раздел "Fiat Gateway"** (новый)
  - **Подключение банков/платежных систем**
    - Список интеграций (ELSOM, Мегапей, банки КР)
    - Статус подключения (active/inactive)
    - Настройки API ключей
  - **Фиатные транзакции**
    - Ввод фиата (deposit)
    - Вывод фиата (withdrawal)
    - История фиатных операций
  - **Reconciliation (Сверка)**
    - Автоматическая сверка банковских выписок
    - Несоответствия (discrepancies)

- [ ] **Dashboard Widget: Fiat Summary**
  - Фиатный баланс (KGS, USD, RUB)
  - Транзакции за 24ч (фиат)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/fiat/` — новый раздел
- `frontend/src/app/(authenticated)/dashboard/page.tsx` — добавить FiatSummaryWidget
- Backend: модели FiatGateway, FiatTransaction, интеграции с банками/платежными системами

---

### 5. **Multi-Blockchain Support (Несколько блокчейнов)** ⛓️

**Текущее состояние:** Поддержка нескольких сетей есть (Network selector)  
**Требуется уточнение:**

- [ ] **Проверить поддержку Tron, BNB Chain, Ethereum**
  - Убедиться что Safina API возвращает корректные данные для всех сетей
  - Добавить иконки/логотипы для каждого блокчейна

- [ ] **Раздел "Networks"** (опциональный, уже частично есть)
  - Список активных блокчейнов
  - Статус сети (online/offline)
  - Комиссии блокчейна (gas price) в реальном времени
  - Настройки делегирования ресурсов (для Tron)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/networks/` — расширить функционал
- `frontend/src/lib/networks.ts` — добавить Tron, BNB, ETH конфиги

---

### 6. **White Label Customization** 🎨

**Текущее состояние:** Единый дизайн для всех  
**Требуется:**

- [ ] **Брендинг для каждого обменника**
  - Logo (организации)
  - Цветовая схема (primary/secondary colors)
  - Название в UI (вместо "ORGON")
  - Домен/поддомен (ex1.asystem.kg, ex2.asystem.kg)

- [ ] **Settings → Branding** (новый подраздел)
  - Загрузка логотипа
  - Выбор цветов (color picker)
  - Предпросмотр (preview mode)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/settings/branding/` — новый подраздел
- `frontend/src/components/layout/Header.tsx` — динамический logo/название
- `frontend/tailwind.config.ts` — динамические цвета (CSS variables)
- Backend: модель OrganizationBranding, CDN для загрузки логотипов

---

### 7. **24/7 Operations & Support** 🛠️

**Текущее состояние:** Нет раздела для поддержки  
**Требуется:**

- [ ] **Раздел "Support"** (новый)
  - **Ticket System**
    - Создание тикета (с категорией: техническая проблема, вопрос, запрос функции)
    - История тикетов
    - Статус (открыт/в работе/закрыт)
  - **Live Chat** (опционально)
    - Интеграция с Intercom, Zendesk или собственный чат
  - **Knowledge Base**
    - FAQ
    - Руководства пользователя
    - API документация

- [ ] **Dashboard Widget: System Status**
  - Uptime (99.9%)
  - Статус сервисов (ORGON Backend, Safina API, Fiat Gateway)
  - Incident alerts (если есть проблемы)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/support/` — новый раздел
- `frontend/src/app/(authenticated)/dashboard/page.tsx` — добавить SystemStatusWidget
- Backend: модели SupportTicket, KnowledgeBaseArticle

---

### 8. **Enhanced Analytics (Расширенная аналитика)** 📈

**Текущее состояние:** Analytics раздел есть, но базовый  
**Требуется:**

- [ ] **Multi-Organization Analytics** (для Asystem Super Admin)
  - Сравнение обменников (top performers)
  - Общий объем транзакций (все обменники)
  - Revenue breakdown (по организациям)

- [ ] **Client-Level Analytics** (для обменника)
  - Статистика по клиентам (C11...Cnm)
  - Top клиенты по объему
  - Retention rate (процент возвращающихся)

- [ ] **Blockchain Analytics**
  - Распределение транзакций по блокчейнам (Tron vs BNB vs ETH)
  - Средние комиссии
  - Время подтверждения (confirmation time)

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/analytics/page.tsx` — расширить
- Backend: новые endpoints для multi-org аналитики

---

### 9. **Scheduled Transactions Enhancement** ⏰

**Текущее состояние:** Есть раздел Scheduled  
**Требуется:**

- [ ] **Recurring Payments** (Регулярные платежи)
  - Абонентская плата (ежемесячная автоотправка)
  - Salary payouts (для обменников)
  - Dividend distributions

- [ ] **Batch Transactions**
  - Массовая отправка (например, зарплаты сотрудникам)
  - CSV импорт списка получателей

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/scheduled/page.tsx` — добавить recurring и batch функции
- Backend: модели RecurringPayment, BatchTransaction

---

### 10. **Security Enhancements** 🔐

**Текущее состояние:** Есть 2FA (упомянут в Settings)  
**Требуется:**

- [ ] **IP Whitelisting**
  - Разрешить доступ только с определенных IP (для обменников)
  
- [ ] **API Rate Limiting**
  - Защита от DDoS/злоупотреблений
  
- [ ] **Withdrawal Limits**
  - Дневные/месячные лимиты на вывод (настраиваемые для каждого обменника)
  
- [ ] **Cold Storage Management** (для теплых кошельков)
  - Автоматическое перемещение средств hot → warm → cold
  - Правила (например, "если баланс > X USDT, переместить в cold")

**Файлы для изменения:**
- `frontend/src/app/(authenticated)/settings/security/` — новый подраздел
- Backend: middleware для IP whitelisting, rate limiting, модели WithdrawalLimit, ColdStorageRule

---

## 📅 Приоритизация (Рекомендуемая)

### Фаза 1: MVP для Asystem (2-3 недели)
1. ✅ **Multi-Tenancy** (Organizations) — критически важно
2. ✅ **Billing & Subscription** — для монетизации
3. ✅ **Regulatory Compliance** (базовая отчетность) — обязательно для лицензированных обменников

### Фаза 2: White Label Ready (1-2 недели)
4. ✅ **White Label Customization** — для запуска обменников
5. ✅ **Fiat Gateway Integration** — ключевая функция
6. ✅ **Enhanced Analytics** — для принятия решений

### Фаза 3: Production Hardening (1-2 недели)
7. ✅ **24/7 Support System** — для клиентов
8. ✅ **Security Enhancements** — для безопасности
9. ✅ **Scheduled Transactions Enhancement** — для автоматизации

### Фаза 4: Scale & Optimize (постоянно)
10. ✅ **Multi-Blockchain Optimization** — по мере роста

---

## 🛠️ Технические задачи (TODO)

### Backend (приоритетные)
- [ ] Создать модели: Organization, Subscription, Invoice, ComplianceReport, FiatGateway
- [ ] Middleware: tenant isolation, IP whitelisting, rate limiting
- [ ] API endpoints: `/organizations`, `/billing`, `/compliance`, `/fiat`
- [ ] Интеграции: KYC/AML провайдеры, банки/платежные системы

### Frontend (приоритетные)
- [ ] Новые разделы: Organizations, Billing, Compliance, Fiat Gateway, Support
- [ ] Dashboard виджеты: Billing Summary, Fiat Summary, System Status
- [ ] Settings подразделы: Branding, Security
- [ ] White Label: динамический logo/colors через CSS variables

### Инфраструктура
- [ ] Multi-tenancy database schema (PostgreSQL row-level security или отдельные schemas)
- [ ] CDN для загрузки логотипов (S3/CloudFlare R2)
- [ ] Monitoring: Uptime (Pingdom/UptimeRobot), Error tracking (Sentry)
- [ ] Backup strategy: daily backups, disaster recovery plan

---

## 📝 Вопросы для уточнения (из документа)

1. **Количество кошельков:** Сколько hot/warm кошельков на одного обменника в среднем?
2. **Количество транзакций:** Средний/пиковый объем транзакций в день?
3. **Блокчейны:** Только Tron, BNB, ETH или нужны другие (Polygon, Arbitrum, Solana)?
4. **Режим работы:** 24/7 (assumed) или есть maintenance windows?
5. **Поддержка:** Внутренняя команда Asystem или аутсорс?
6. **Распределение доходов:** Asystem + Tengrisoft — как делится прибыль?
7. **Абонентская плата:** Фиксированная сумма (xxx USDT) — сколько точно?
8. **Учет операций:** Кто ведет бухгалтерию (Asystem или каждый обменник сам)?
9. **Взаиморасчеты:** Asystem ↔ Tengrisoft — как проходят платежи (крипто/фиат)?

---

## 🎯 Следующие шаги

1. **Обсудить приоритеты** с командой Asystem/Tengrisoft
2. **Уточнить бизнес-требования** (ответить на вопросы выше)
3. **Создать техническое задание** для Фазы 1 (Multi-Tenancy, Billing, Compliance)
4. **Оценить трудозатраты** (человеко-часы для каждой фазы)
5. **Начать разработку** с приоритетных задач

---

**Автор:** Forge 🔥  
**Дата:** 2026-02-10 05:55 GMT+6
