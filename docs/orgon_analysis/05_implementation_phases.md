# 05. Фазированный план реализации ORGON (GOTCHA Framework)

> **Документ:** Plan v2.0 | **Дата:** Февраль 2026  
> **Автор:** Atlas (Master Controller) | **Утверждение:** Урмат Мырзабеков  
> **Метод:** GOTCHA (Goals → Orchestration → Tools → Context → Hard prompts → Args)

---

## Обзор фаз

| Фаза | Срок | Цель | Бюджет |
|------|------|------|--------|
| **Phase 1: MVP Deploy** | 2 недели | Рабочая платформа на orgon.asystem.ai | $0 (инфраструктура есть) |
| **Phase 2: Billing & Compliance** | 4 недели | Биллинг, калькулятор маржи, AML/KYT | ~$200 (API сервисы) |
| **Phase 3: White-label & Partner API** | 4 недели | B2B готовность, первые пилоты | ~$500 (тестирование) |
| **Phase 4: Scale & Enterprise** | 4 недели | 5+ клиентов, enterprise features | ~$1000 (маркетинг) |

---

## Phase 1: MVP Deploy (Недели 1-2)

### 🎯 Goal
Развернуть ORGON на VM 501 (100.121.231.50) так, чтобы orgon.asystem.ai показывал рабочую платформу: лендинг, регистрация, логин, dashboard, кошельки, транзакции.

### 🔧 Orchestration
- **Executor:** ORGON Agent (@Orgon_ai_bot)
- **Supervisor:** Atlas (задачи порционально, проверка качества)
- **Approver:** Урмат (финальная приёмка)

### 🛠️ Tools
- Docker + Docker Compose (контейнеризация)
- Cloudflare Tunnel (публикация на orgon.asystem.ai)
- PM2 / systemd (process management)
- Neon PostgreSQL (БД, уже подключена)
- Tailscale (dev-доступ: orgon.tail70fd.ts.net)

### 📋 Задачи Phase 1

#### Неделя 1: Инфраструктура и деплой

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 1.1 | **Организация кода на VM 501** | Код в `/home/asystem/orgon/`, структура backend/ + frontend/, .env настроен | P0 |
| 1.2 | **Backend деплой** | `uvicorn` на порту 8000, `/docs` (Swagger) доступен, health check OK | P0 |
| 1.3 | **Frontend деплой** | Next.js build + start на порту 3000, лендинг рендерится | P0 |
| 1.4 | **Docker Compose (dev)** | `docker-compose up` поднимает backend + frontend, оба доступны | P0 |
| 1.5 | **Cloudflare Tunnel** | orgon.asystem.ai → frontend:3000, API проксируется через /api | P0 |
| 1.6 | **SSL/TLS** | HTTPS через Cloudflare, сертификат валидный | P0 |

#### Неделя 2: Функциональность и тестирование

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 2.1 | **Регистрация и логин** | Новый пользователь может зарегистрироваться, получить JWT, войти | P0 |
| 2.2 | **Создание организации** | После логина можно создать организацию (тенант) | P0 |
| 2.3 | **Dashboard** | Показывает статистику: кошельки, балансы, последние транзакции | P0 |
| 2.4 | **Создание кошелька** | Через Safina API создаётся кастодиальный кошелёк (BTC/ETH/TRX) | P0 |
| 2.5 | **Список кошельков** | Все кошельки организации с балансами и адресами | P1 |
| 2.6 | **Отправка транзакции** | Создание TX → подписание → broadcast (тестовая сеть) | P1 |
| 2.7 | **i18n проверка** | Переключение ru/en/ky работает на всех страницах | P1 |
| 2.8 | **Mobile responsive** | Все страницы корректно отображаются на мобильных устройствах | P2 |
| 2.9 | **Error handling** | 404, 500, network errors — красивые страницы ошибок | P2 |

### 📊 Context
- Backend уже работал на Mac Mini (Forge), 40+ endpoints реализованы
- Frontend: 27 страниц, Aceternity UI, dark theme
- Safina API интеграция есть в `backend/safina/client.py`
- Docker files существуют: `docker-compose.yml`, `docker-compose.dev.yml`
- БД: Neon PostgreSQL с 9 миграциями (orgs, tenants, billing, compliance, whitelabel, fiat)

### ✅ Definition of Done (Phase 1)
- [ ] orgon.asystem.ai загружается без ошибок (HTTP 200)
- [ ] Регистрация → Логин → Dashboard → Создание кошелька — полный flow работает
- [ ] API документация доступна на /api/docs
- [ ] Время ответа API < 500ms (95 percentile)
- [ ] Время загрузки страницы < 2 секунды

### 🚀 Команды деплоя

```bash
# На VM 501 (100.121.231.50)
ssh root@100.121.231.50

# 1. Установка зависимостей (если не установлены)
apt update && apt install -y docker.io docker-compose nodejs npm python3-pip

# 2. Настройка .env
cd /home/asystem/orgon
cp .env.example .env
# Заполнить: DATABASE_URL, SAFINA_API_KEY, JWT_SECRET, NEXTAUTH_URL

# 3. Docker Compose (dev)
docker-compose -f docker-compose.dev.yml up -d

# 4. Cloudflare Tunnel
cloudflared tunnel create orgon
cloudflared tunnel route dns orgon orgon.asystem.ai
cloudflared tunnel run orgon

# 5. Проверка
curl -s https://orgon.asystem.ai | head -5
curl -s https://orgon.asystem.ai/api/v1/health
```

---

## Phase 2: Billing & Compliance (Недели 3-6)

### 🎯 Goal
Модуль биллинга для учёта транзакций, калькулятор маржи для определения справедливых комиссий, compliance модуль для AML/KYT мониторинга. Admin panel для управления клиентами-компаниями.

### 🔧 Orchestration
- **Backend:** ORGON Agent (реализация API)
- **Frontend:** ORGON Agent (UI компоненты)
- **Architecture:** Atlas (review, рекомендации)
- **Testing:** Atlas (автоматические тесты)

### 📋 Задачи Phase 2

#### Неделя 3-4: Биллинг и калькулятор

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 3.1 | **Таблицы биллинга** | `transaction_fees`, `billing_periods`, `invoices`, `settlements` в БД | P0 |
| 3.2 | **Fee engine** | При каждой транзакции автоматически рассчитывается комиссия по тарифу | P0 |
| 3.3 | **Калькулятор маржи (API)** | POST /admin/calculator — расчёт по входным параметрам (AUC, объём, тариф) | P0 |
| 3.4 | **Калькулятор маржи (UI)** | Страница в admin panel с интерактивными слайдерами | P1 |
| 3.5 | **Settlement engine** | Автоматический расчёт: ASYSTEM доля vs KAZ.ONE доля за период | P1 |
| 3.6 | **Invoicing** | Генерация счетов для клиентов (PDF/email) | P2 |
| 3.7 | **Usage dashboard** | Графики использования: транзакции/день, объём, комиссии | P1 |

#### Неделя 5-6: Compliance и Admin Panel

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 4.1 | **AML/KYT pipeline** | Каждая транзакция проходит risk scoring (через Safina CCC) | P0 |
| 4.2 | **Risk alerts** | Высокорисковые транзакции блокируются, уведомление admin | P0 |
| 4.3 | **KYB verification** | Процесс верификации компании-клиента: документы → review → approve | P0 |
| 4.4 | **Отчётность ПУВА** | Формирование отчётов для Финнадзор КР (формат по Приказам 579п, 580) | P1 |
| 4.5 | **SuperAdmin panel** | Управление всеми организациями, пользователями, тарифами | P0 |
| 4.6 | **Tenant management** | Создание/приостановка/удаление тенантов из admin panel | P0 |
| 4.7 | **Audit log viewer** | Просмотр всех действий с фильтрацией по user/org/action/date | P1 |

### 📊 Схема данных биллинга

```sql
-- Комиссии за транзакции
CREATE TABLE transaction_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id),
    org_id UUID REFERENCES organizations(id),
    fee_type VARCHAR(50), -- 'transaction', 'custody', 'subscription'
    gross_amount DECIMAL(18,8),
    fee_rate DECIMAL(8,6),
    fee_amount DECIMAL(18,8),
    asystem_share DECIMAL(18,8),  -- наша доля
    partner_share DECIMAL(18,8),  -- доля KAZ.ONE
    tariff_plan VARCHAR(20), -- 'A', 'B', 'C'
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Периоды расчётов
CREATE TABLE billing_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id),
    period_start DATE,
    period_end DATE,
    total_transactions INT,
    total_volume DECIMAL(18,2),
    total_fees DECIMAL(18,2),
    subscription_fee DECIMAL(18,2),
    custody_fee DECIMAL(18,2),
    status VARCHAR(20) DEFAULT 'pending' -- pending, invoiced, paid
);

-- Взаиморасчёты ASYSTEM ↔ KAZ.ONE
CREATE TABLE settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start DATE,
    period_end DATE,
    total_revenue DECIMAL(18,2),
    asystem_revenue DECIMAL(18,2),
    partner_revenue DECIMAL(18,2),
    status VARCHAR(20) DEFAULT 'pending', -- pending, confirmed, paid
    settlement_date DATE,
    notes TEXT
);
```

### ✅ Definition of Done (Phase 2)
- [ ] Каждая транзакция автоматически генерирует fee record
- [ ] Калькулятор маржи доступен в admin panel
- [ ] AML/KYT проверка на каждую транзакцию
- [ ] SuperAdmin может управлять организациями и тарифами
- [ ] Отчёт за период генерируется в 1 клик

---

## Phase 3: White-label & Partner API (Недели 7-10)

### 🎯 Goal
B2B готовность: клиенты могут кастомизировать платформу под свой бренд, Partner API для интеграций, production hardening для стабильной работы.

### 📋 Задачи Phase 3

#### Неделя 7-8: White-label

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 5.1 | **Branding settings** | Клиент загружает логотип, выбирает цвета, название | P0 |
| 5.2 | **Custom domain** | Поддержка custom domain для тенанта (CNAME → платформа) | P1 |
| 5.3 | **Email templates** | Брендированные email для каждого тенанта | P1 |
| 5.4 | **Widget embed** | JS-виджет для встраивания кошелька на сайт клиента | P2 |

#### Неделя 9-10: Partner API и Production

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 6.1 | **Partner API v1** | REST API для партнёров: кошельки, транзакции, балансы, webhooks | P0 |
| 6.2 | **API Keys management** | Генерация/отзыв API ключей в настройках организации | P0 |
| 6.3 | **Webhook system** | Уведомления о входящих транзакциях, изменениях статуса | P0 |
| 6.4 | **Rate limiting** | Redis-based rate limiting: 100 req/min (A), 1000 (B), unlimited (C) | P1 |
| 6.5 | **Docker production** | Оптимизированные Docker images, multi-stage build | P0 |
| 6.6 | **Мониторинг** | Health checks, error tracking (Sentry), uptime alerts в Telegram | P1 |
| 6.7 | **Backup strategy** | Automated DB backups (daily), point-in-time recovery | P1 |
| 6.8 | **Load testing** | API выдерживает 100 concurrent users, < 500ms response | P2 |
| 6.9 | **Security audit** | Pen-test основных endpoints, OWASP top 10 check | P1 |

### 📊 Partner API структура

```
Partner API v1
├── POST   /partner/v1/wallets           — Создание кошелька
├── GET    /partner/v1/wallets           — Список кошельков
├── GET    /partner/v1/wallets/:id       — Детали кошелька
├── GET    /partner/v1/wallets/:id/balance — Баланс
├── POST   /partner/v1/transactions      — Отправка транзакции
├── GET    /partner/v1/transactions      — Список транзакций
├── GET    /partner/v1/transactions/:id  — Статус транзакции
├── POST   /partner/v1/webhooks          — Регистрация webhook
├── GET    /partner/v1/networks          — Доступные сети
├── GET    /partner/v1/tokens            — Доступные токены
└── GET    /partner/v1/fees              — Текущие комиссии
```

### ✅ Definition of Done (Phase 3)
- [ ] Клиент может настроить бренд (логотип, цвета) через UI
- [ ] Partner API документирован и доступен
- [ ] Webhooks работают для входящих транзакций
- [ ] Production Docker deployment с health checks
- [ ] Backup + monitoring настроены
- [ ] Готовность к пилотным клиентам

---

## Phase 4: Scale & Enterprise (Недели 11-14)

### 🎯 Goal
Первые 5+ реальных клиентов, enterprise features для банков, масштабирование инфраструктуры.

### 📋 Задачи Phase 4

| # | Задача | Критерий приёмки | Приоритет |
|---|--------|-----------------|-----------|
| 7.1 | **Onboarding flow** | Автоматизированный процесс: заявка → KYB → настройка → launch | P0 |
| 7.2 | **Пилотные клиенты (3-5)** | Подключены, используют платформу, генерируют транзакции | P0 |
| 7.3 | **Multi-sig advanced** | Настраиваемые политики одобрения (2-из-3, 3-из-5, time-lock) | P1 |
| 7.4 | **RBAC расширенный** | Роли: Owner, Admin, Operator, Auditor, Viewer с гранулярными правами | P0 |
| 7.5 | **CSV/PDF export** | Выгрузка транзакций, балансов, отчётов | P1 |
| 7.6 | **2FA обязательный** | TOTP (Google Auth) + SMS backup для critical actions | P0 |
| 7.7 | **SLA dashboard** | Uptime monitoring, response times, SLA compliance (99.9%) | P1 |
| 7.8 | **Horizontal scaling** | Docker Swarm / K8s для backend, read replicas для DB | P2 |
| 7.9 | **Регуляторная отчётность** | Автоматическая генерация отчётов ПУВА для Финнадзор | P1 |
| 7.10 | **Региональная экспансия** | Подготовка для рынков Узбекистана, Казахстана | P2 |

### ✅ Definition of Done (Phase 4)
- [ ] 5+ клиентов активно используют платформу
- [ ] Enterprise тариф доступен с выделенным инстансом
- [ ] SLA 99.9% подтверждён мониторингом
- [ ] Регуляторная отчётность автоматизирована
- [ ] Первый доход от транзакционных комиссий

---

## Дорожная карта (Timeline)

```
Февраль 2026                    Март 2026                        Апрель 2026                      Май 2026
├─── Phase 1 (MVP) ────────────┤                                                                    
│ W1: Инфра + Docker           │                                                                    
│ W2: Функционал + тесты       │                                                                    
├──────────────────────────────├─── Phase 2 (Billing) ──────────┤                                    
│                              │ W3-4: Биллинг + калькулятор    │                                    
│                              │ W5-6: Compliance + Admin       │                                    
│                              ├────────────────────────────────├─── Phase 3 (B2B) ─────────────┤   
│                              │                                │ W7-8: White-label              │   
│                              │                                │ W9-10: Partner API + Prod      │   
│                              │                                ├────────────────────────────────├── Phase 4 (Scale)
│                              │                                │                                │ W11-14: Enterprise
│                              │                                │                                │ 5+ клиентов
```

---

## Прогноз ресурсов

### Команда
| Роль | Кто | Загрузка |
|------|-----|----------|
| Product Owner | Урмат | 20% (решения, приёмка) |
| Orchestrator | Atlas | 30% (планирование, контроль) |
| Developer | ORGON Agent | 100% (реализация) |
| Sales | Урмат | 40% (с Phase 3) |

### Инфраструктура
| Ресурс | Стоимость/мес | Когда |
|--------|--------------|-------|
| VM 501 (orgon) | $0 (Proxmox) | Сейчас |
| Neon PostgreSQL | $0-25 | Сейчас |
| Cloudflare | $0-20 | Phase 1 |
| Sentry (мониторинг) | $0 (free tier) | Phase 3 |
| Redis (caching) | $0 (self-hosted) | Phase 2 |

---

## Риски и митигация

| Риск | Вероятность | Импакт | Митигация |
|------|------------|--------|-----------|
| Safina API нестабильность | Средняя | Высокий | Circuit breaker, retry logic, fallback |
| Нет клиентов к Phase 4 | Средняя | Критический | Начать outreach с Phase 2, demo-среда для презентаций |
| Регуляторные изменения | Низкая | Высокий | Мониторинг законодательства, гибкая архитектура |
| Конкуренция | Средняя | Средний | Фокус на локализацию и цену (в 3-10x дешевле мировых) |
| Безопасность / взлом | Низкая | Критический | Security audit на Phase 3, pen-test, insurance план |

---

## KPI по фазам

| Метрика | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---------|---------|---------|---------|---------|
| Uptime | 95% | 99% | 99.5% | 99.9% |
| API response (p95) | < 1s | < 500ms | < 300ms | < 200ms |
| Клиентов (орг) | 0 (demo) | 0 (тест) | 2-3 (пилот) | 5-10 |
| Транзакций/день | ~10 (тест) | ~50 | ~200 | ~1000 |
| MRR ($) | $0 | $0 | $1-2K | $5-10K |
| Bug rate | < 20/неделя | < 10 | < 5 | < 2 |

---

*Документ обновляется по мере прохождения фаз. Каждая фаза начинается после приёмки предыдущей.*
