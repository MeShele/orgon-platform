# ФАЗА 1: Multi-Tenancy — Детальный план

**Приоритет:** 🔴 КРИТИЧЕСКИЙ  
**Сроки:** 2 недели (2026-02-10 → 2026-02-24)  
**Цель:** Поддержка множества обменников (170+) с изоляцией данных

---

## 📋 Этап 1.1: Database Design (2 дня, до 2026-02-12)

### Задачи

#### 1.1.1 Проектирование multi-tenant schema ✅
- [ ] Выбрать стратегию multi-tenancy:
  - Вариант A: Shared database + Row-Level Security (RLS)
  - Вариант B: Database per tenant
  - Вариант C: Schema per tenant
  - **Решение:** Вариант A (RLS) — проще масштабировать, меньше overhead

- [ ] Спроектировать core таблицы:
  ```sql
  -- Организации (обменники)
  organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    license_number VARCHAR(100),
    status ENUM('active', 'suspended', 'archived'),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
  )
  
  -- Связь пользователей с организациями
  user_organizations (
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    role ENUM('admin', 'operator', 'viewer'),
    PRIMARY KEY (user_id, organization_id)
  )
  
  -- Настройки организации
  organization_settings (
    organization_id UUID PRIMARY KEY REFERENCES organizations(id),
    billing_enabled BOOLEAN DEFAULT true,
    features JSONB, -- {"kyc": true, "fiat": false}
    limits JSONB, -- {"daily_withdrawal": 10000}
    created_at TIMESTAMP
  )
  ```

- [ ] Добавить `organization_id` в существующие таблицы:
  - wallets → organization_id
  - transactions → organization_id
  - signatures → organization_id
  - contacts → organization_id
  - scheduled_transactions → organization_id
  - audit_logs → organization_id

#### 1.1.2 Row-Level Security (RLS) политики
- [ ] Создать RLS политики для каждой таблицы:
  ```sql
  -- Пример для wallets
  ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
  
  CREATE POLICY wallets_isolation_policy ON wallets
    USING (organization_id = current_setting('app.current_organization_id')::uuid);
  ```

- [ ] Тест RLS:
  - Создать 2 тестовые организации
  - Попытаться получить данные чужой организации
  - Убедиться что доступ запрещён

#### 1.1.3 Migration scripts
- [ ] Создать миграции:
  - `001_create_organizations.sql`
  - `002_create_user_organizations.sql`
  - `003_create_organization_settings.sql`
  - `004_add_organization_id_to_existing_tables.sql`
  - `005_enable_rls_policies.sql`

- [ ] Rollback scripts (на случай ошибки)

- [ ] Seed data (тестовые организации):
  - Organization 1: "Test Exchange Alpha"
  - Organization 2: "Test Exchange Beta"
  - Super Admin user для тестов

### Самопроверка этапа 1.1

#### Code Quality
- [ ] SQL миграции проверены на синтаксис
- [ ] Naming conventions соблюдены
- [ ] Indexes добавлены (organization_id во всех таблицах)

#### Testing
- [ ] Миграции применены на dev DB без ошибок
- [ ] Rollback работает корректно
- [ ] RLS тест: изоляция данных работает
- [ ] Performance test: запросы с organization_id быстрые (< 50ms)

#### Security
- [ ] RLS включена на всех чувствительных таблицах
- [ ] Нет способа обойти organization_id фильтр
- [ ] Super Admin может видеть все организации

#### Documentation
- [ ] Схема БД задокументирована (ER diagram)
- [ ] Migration guide написан
- [ ] Комментарии в SQL скриптах

### Deliverables
- ✅ Migrations (5 файлов)
- ✅ ER Diagram (PDF/PNG)
- ✅ Migration guide (MD)
- ✅ Test report (результаты RLS тестов)

---

## 📋 Этап 1.2: Backend API (3 дня, до 2026-02-15)

### Задачи

#### 1.2.1 Organizations CRUD API
- [ ] Endpoints:
  ```
  GET    /api/organizations          (список организаций, Super Admin only)
  POST   /api/organizations          (создание, Super Admin only)
  GET    /api/organizations/:id      (детали организации)
  PUT    /api/organizations/:id      (обновление)
  DELETE /api/organizations/:id      (архивация, не удаление)
  ```

- [ ] Request/Response schemas:
  ```typescript
  // Request
  interface CreateOrganizationRequest {
    name: string;
    slug: string;
    license_number?: string;
  }
  
  // Response
  interface Organization {
    id: string;
    name: string;
    slug: string;
    license_number?: string;
    status: 'active' | 'suspended' | 'archived';
    created_at: string;
    updated_at: string;
  }
  ```

- [ ] Validation:
  - name: обязательно, 3-255 символов
  - slug: обязательно, уникальный, lowercase, a-z0-9-
  - license_number: опционально, формат КР лицензии

#### 1.2.2 Tenant Middleware
- [ ] Middleware для установки `app.current_organization_id`:
  ```typescript
  async function setTenantContext(req, res, next) {
    const user = req.user; // из auth middleware
    const organizationId = req.headers['x-organization-id'] || user.default_organization_id;
    
    // Проверить что пользователь имеет доступ к этой организации
    const hasAccess = await checkUserOrgAccess(user.id, organizationId);
    if (!hasAccess) {
      return res.status(403).json({ error: 'Access denied' });
    }
    
    // Установить контекст для RLS
    await db.query("SET app.current_organization_id = $1", [organizationId]);
    
    req.organization_id = organizationId;
    next();
  }
  ```

- [ ] Применить middleware ко всем защищенным routes

#### 1.2.3 User-Organization Management
- [ ] Endpoints:
  ```
  GET    /api/organizations/:id/users         (список пользователей орг.)
  POST   /api/organizations/:id/users         (добавить пользователя)
  DELETE /api/organizations/:id/users/:userId (удалить пользователя)
  PUT    /api/organizations/:id/users/:userId (изменить роль)
  ```

- [ ] Roles:
  - `admin`: полный доступ к организации
  - `operator`: создание транзакций, подписей
  - `viewer`: только просмотр

#### 1.2.4 Authentication Update
- [ ] Обновить login response:
  ```typescript
  interface LoginResponse {
    token: string;
    user: User;
    organizations: Array<{
      id: string;
      name: string;
      role: 'admin' | 'operator' | 'viewer';
    }>;
    default_organization_id: string;
  }
  ```

### Самопроверка этапа 1.2

#### Code Quality
- [ ] TypeScript: No errors, strict mode
- [ ] ESLint: No warnings
- [ ] API consistent naming (RESTful)

#### Testing
- [ ] Unit tests для всех endpoints (80%+ coverage)
- [ ] Integration tests:
  - Создание организации
  - Tenant isolation (User A не видит данных User B)
  - Role-based access (operator не может удалить пользователя)
- [ ] Postman collection с примерами

#### Security
- [ ] Authorization checks на всех endpoints
- [ ] Input validation (XSS, SQL injection prevention)
- [ ] Rate limiting (100 req/min per org)

#### Performance
- [ ] Tenant middleware: < 10ms overhead
- [ ] Organizations API: < 100ms response time

#### Documentation
- [ ] OpenAPI/Swagger spec
- [ ] API guide (примеры curl/fetch)

### Deliverables
- ✅ Organizations API (5 endpoints)
- ✅ Tenant middleware
- ✅ User-Org Management API (4 endpoints)
- ✅ Tests (unit + integration)
- ✅ OpenAPI spec
- ✅ Postman collection

---

## 📋 Этап 1.3: Frontend UI (3 дня, до 2026-02-18)

### Задачи

#### 1.3.1 Organizations Page (Список)
- [ ] Route: `/organizations`
- [ ] Компонент: `app/(authenticated)/organizations/page.tsx`
- [ ] Функционал:
  - Таблица организаций (name, license, status, created_at)
  - Поиск по имени
  - Фильтр по статусу (active/suspended/archived)
  - Сортировка
  - Пагинация
  - Кнопка "Create Organization" (Super Admin only)

- [ ] UI:
  - Адаптивный дизайн (мобильные, планшеты)
  - Loading states
  - Empty state ("Нет организаций")
  - Error handling

#### 1.3.2 Create/Edit Organization Modal
- [ ] Форма:
  - Name (input)
  - Slug (input, auto-generate из name)
  - License Number (input, optional)
  - Status (select: active/suspended/archived)

- [ ] Validation:
  - Real-time validation
  - Error messages
  - Success notification

#### 1.3.3 Organization Profile Page
- [ ] Route: `/organizations/:id`
- [ ] Sections:
  - Profile (name, license, status)
  - Users (список с ролями)
  - Settings (OrganizationSettings)
  - Statistics (кошельки, транзакции, баланс)

- [ ] Actions:
  - Edit profile
  - Add/Remove users
  - Suspend/Archive organization

#### 1.3.4 Tenant Selector (Header)
- [ ] Компонент: `TenantSelector.tsx`
- [ ] Функционал:
  - Dropdown с списком организаций пользователя
  - Текущая организация (выделена)
  - Переключение → обновление контекста → reload данных

- [ ] Позиция: Header (рядом с user menu)

#### 1.3.5 Tooltips для Organizations
- [ ] Добавить в `help-content.ts`:
  - organizationsList
  - createOrganization
  - organizationProfile
  - tenantSelector

### Самопроверка этапа 1.3

#### Code Quality
- [ ] TypeScript: No errors
- [ ] React best practices (hooks, memo)
- [ ] Accessible (ARIA labels, keyboard navigation)

#### Testing
- [ ] Component tests (Jest + React Testing Library)
- [ ] Visual regression tests (опционально)
- [ ] Manual testing (desktop, mobile, tablet)

#### UX/UI
- [ ] Design consistent с остальным приложением
- [ ] Loading states (skeleton screens)
- [ ] Error states (friendly messages)
- [ ] Success feedback (toasts)

#### Performance
- [ ] Bundle size < 50KB для нового раздела
- [ ] Lighthouse score > 90

#### Documentation
- [ ] Component docs (props, usage)
- [ ] User guide (как создать организацию)

### Deliverables
- ✅ Organizations page
- ✅ Create/Edit modal
- ✅ Profile page
- ✅ Tenant selector
- ✅ Tooltips
- ✅ Component tests
- ✅ User guide

---

## 📋 Этап 1.4: Integration & Testing (2 дня, до 2026-02-20)

### Задачи

#### 1.4.1 End-to-End Tests
- [ ] Сценарий 1: Создание организации
  1. Super Admin логинится
  2. Переходит в /organizations
  3. Создает новую организацию "Test Exchange Gamma"
  4. Проверяет что организация в списке
  
- [ ] Сценарий 2: Добавление пользователя
  1. Admin организации логинится
  2. Переходит в /organizations/:id
  3. Добавляет нового пользователя с ролью "operator"
  4. Проверяет что пользователь появился в списке

- [ ] Сценарий 3: Tenant Isolation
  1. User A (Organization 1) логинится
  2. Создает кошелек
  3. User B (Organization 2) логинится
  4. Проверяет что не видит кошелек User A

- [ ] Сценарий 4: Tenant Switching
  1. User с доступом к 2 организациям логинится
  2. Видит данные Organization 1
  3. Переключается на Organization 2 (tenant selector)
  4. Видит данные Organization 2

#### 1.4.2 Performance Testing
- [ ] Load test: 100 параллельных запросов к /api/organizations
- [ ] Stress test: 1000 организаций в базе, проверка скорости запросов
- [ ] Database query optimization:
  - EXPLAIN ANALYZE для main queries
  - Добавить indexes если нужно

#### 1.4.3 Security Audit
- [ ] Checklist:
  - [ ] RLS работает корректно (нет утечек данных)
  - [ ] Authorization проверяется на всех endpoints
  - [ ] Input validation (XSS, SQL injection)
  - [ ] CSRF protection
  - [ ] Rate limiting работает
  - [ ] Sensitive data не логируется

- [ ] Penetration testing (basic):
  - Попытка SQL injection
  - Попытка XSS
  - Попытка обхода RLS

#### 1.4.4 Documentation
- [ ] Migration guide:
  - Как применить миграции
  - Как rollback если что-то пошло не так
  - Как перенести существующие данные в multi-tenant

- [ ] API documentation update
- [ ] User guide:
  - Как создать организацию
  - Как добавить пользователя
  - Как переключаться между организациями

- [ ] Architecture documentation:
  - Диаграмма multi-tenancy
  - RLS strategy
  - Security considerations

### Самопроверка этапа 1.4

#### Testing
- [ ] E2E tests: All passing (4/4 сценариев)
- [ ] Performance tests: Meet targets (< 200ms)
- [ ] Security tests: No vulnerabilities found

#### Documentation
- [ ] Migration guide complete
- [ ] API docs updated
- [ ] User guide complete
- [ ] Architecture docs complete

#### Deployment
- [ ] Staging deploy успешен
- [ ] Smoke tests на staging passed
- [ ] Rollback plan готов

### Deliverables
- ✅ E2E tests (4 сценария)
- ✅ Performance report
- ✅ Security audit report
- ✅ Complete documentation
- ✅ Staging deployment

---

## ✅ Phase 1 Completion Criteria

### Functionality
- ✅ Можно создать организацию (Super Admin)
- ✅ Можно добавить пользователя в организацию
- ✅ Данные изолированы между организациями
- ✅ Пользователь может переключаться между организациями (если есть доступ)
- ✅ Super Admin видит все организации

### Quality
- ✅ Test coverage > 80%
- ✅ No critical bugs
- ✅ Performance targets met
- ✅ Security audit passed

### Documentation
- ✅ API documented
- ✅ User guide written
- ✅ Migration guide ready

### Deployment
- ✅ Staging deployment successful
- ✅ Rollback tested

---

## 🚀 Готовность к Фазе 2

После завершения Фазы 1:
- Multi-tenancy foundation готова
- Можно добавлять функции для каждого tenant (billing, compliance)
- Инфраструктура для масштабирования на 170+ обменников

**Дата завершения:** 2026-02-24  
**Следующая фаза:** Фаза 2 (Billing & Compliance)

---

**Автор:** Forge 🔥  
**Обновлено:** 2026-02-10 06:07 GMT+6
