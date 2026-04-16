# Multi-Tenant Database Schema — ORGON

**Версия:** 1.0  
**Дата:** 2026-02-10  
**Стратегия:** Shared Database + Row-Level Security (PostgreSQL RLS)

---

## 🎯 Цели

1. **Изоляция данных:** Каждая организация видит только свои данные
2. **Масштабируемость:** Поддержка 170+ организаций без performance degradation
3. **Безопасность:** RLS на уровне базы данных (не полагаемся только на app logic)
4. **Простота:** Одна база данных, простой deploy и backup

---

## 📊 Core Tables (Новые)

### 1. organizations

**Назначение:** Обменники (tenants)

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    license_number VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'archived')),
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    
    -- Indexes
    CONSTRAINT organizations_slug_format 
        CHECK (slug ~ '^[a-z0-9-]+$')
);

CREATE INDEX idx_organizations_status ON organizations(status);
CREATE INDEX idx_organizations_slug ON organizations(slug);
```

**Примеры:**
- Organization 1: name="Test Exchange Alpha", slug="test-exchange-alpha"
- Organization 2: name="Fiatex КР", slug="fiatex-kr"

---

### 2. user_organizations

**Назначение:** Связь пользователей с организациями (many-to-many + роли)

```sql
CREATE TABLE user_organizations (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin', 'operator', 'viewer')),
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    
    PRIMARY KEY (user_id, organization_id)
);

CREATE INDEX idx_user_organizations_user ON user_organizations(user_id);
CREATE INDEX idx_user_organizations_org ON user_organizations(organization_id);
```

**Роли:**
- `admin`: полный доступ к организации (создание кошельков, пользователей, настройки)
- `operator`: создание транзакций, подписей (рабочий обменника)
- `viewer`: только просмотр (аудитор, бухгалтер)

---

### 3. organization_settings

**Назначение:** Настройки организации

```sql
CREATE TABLE organization_settings (
    organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Feature flags
    billing_enabled BOOLEAN NOT NULL DEFAULT true,
    kyc_enabled BOOLEAN NOT NULL DEFAULT false,
    fiat_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Features (flexible JSON)
    features JSONB NOT NULL DEFAULT '{}',
    -- Example: {"auto_withdrawal": true, "2fa_required": true}
    
    -- Limits
    limits JSONB NOT NULL DEFAULT '{}',
    -- Example: {"daily_withdrawal_usdt": 10000, "monthly_transactions": 1000}
    
    -- Branding (для White Label)
    branding JSONB DEFAULT '{}',
    -- Example: {"logo_url": "...", "primary_color": "#1E40AF"}
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organization_settings_org ON organization_settings(organization_id);
```

---

## 📊 Existing Tables (Изменения)

### Добавить organization_id во все tenant-specific таблицы

```sql
-- 1. wallets
ALTER TABLE wallets 
    ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- 2. transactions
ALTER TABLE transactions 
    ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- 3. signatures
ALTER TABLE signatures 
    ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- 4. contacts
ALTER TABLE contacts 
    ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- 5. scheduled_transactions
ALTER TABLE scheduled_transactions 
    ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- 6. audit_logs
ALTER TABLE audit_logs 
    ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
    -- SET NULL потому что audit logs глобальные (Super Admin должен видеть все)
```

**Indexes:**
```sql
CREATE INDEX idx_wallets_organization ON wallets(organization_id);
CREATE INDEX idx_transactions_organization ON transactions(organization_id);
CREATE INDEX idx_signatures_organization ON signatures(organization_id);
CREATE INDEX idx_contacts_organization ON contacts(organization_id);
CREATE INDEX idx_scheduled_transactions_organization ON scheduled_transactions(organization_id);
CREATE INDEX idx_audit_logs_organization ON audit_logs(organization_id);
```

---

## 🔐 Row-Level Security (RLS)

### Включение RLS на таблицах

```sql
-- Enable RLS
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE signatures ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
```

---

### RLS Policies

#### Стратегия:
- **Regular users:** Видят только данные своей организации
- **Super Admin:** Видят все данные (обходят RLS)

```sql
-- 1. Wallets
CREATE POLICY wallets_isolation_policy ON wallets
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

-- 2. Transactions
CREATE POLICY transactions_isolation_policy ON transactions
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

-- 3. Signatures
CREATE POLICY signatures_isolation_policy ON signatures
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

-- 4. Contacts
CREATE POLICY contacts_isolation_policy ON contacts
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

-- 5. Scheduled Transactions
CREATE POLICY scheduled_transactions_isolation_policy ON scheduled_transactions
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

-- 6. Audit Logs (только чтение, Super Admin видит все)
CREATE POLICY audit_logs_isolation_policy ON audit_logs
    FOR SELECT
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );
```

---

### Как работает RLS

#### Backend middleware устанавливает контекст:

```sql
-- Для обычного пользователя
SET app.current_organization_id = '123e4567-e89b-12d3-a456-426614174000';
SET app.is_super_admin = false;

-- Теперь все запросы автоматически фильтруются:
SELECT * FROM wallets;
-- Вернет только wallets с organization_id = '123e4567-...'

-- Для Super Admin
SET app.is_super_admin = true;

-- Теперь видит все:
SELECT * FROM wallets;
-- Вернет все wallets
```

---

## 📝 Migration Scripts

### Migration 001: Create organizations table

```sql
-- File: migrations/001_create_organizations.sql

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    license_number VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'archived')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    CONSTRAINT organizations_slug_format CHECK (slug ~ '^[a-z0-9-]+$')
);

CREATE INDEX idx_organizations_status ON organizations(status);
CREATE INDEX idx_organizations_slug ON organizations(slug);

-- Trigger для updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_organizations_updated_at 
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Rollback:**
```sql
DROP TRIGGER IF EXISTS update_organizations_updated_at ON organizations;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP TABLE IF EXISTS organizations CASCADE;
```

---

### Migration 002: Create user_organizations table

```sql
-- File: migrations/002_create_user_organizations.sql

CREATE TABLE user_organizations (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin', 'operator', 'viewer')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    PRIMARY KEY (user_id, organization_id)
);

CREATE INDEX idx_user_organizations_user ON user_organizations(user_id);
CREATE INDEX idx_user_organizations_org ON user_organizations(organization_id);
```

**Rollback:**
```sql
DROP TABLE IF EXISTS user_organizations CASCADE;
```

---

### Migration 003: Create organization_settings table

```sql
-- File: migrations/003_create_organization_settings.sql

CREATE TABLE organization_settings (
    organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    billing_enabled BOOLEAN NOT NULL DEFAULT true,
    kyc_enabled BOOLEAN NOT NULL DEFAULT false,
    fiat_enabled BOOLEAN NOT NULL DEFAULT false,
    features JSONB NOT NULL DEFAULT '{}',
    limits JSONB NOT NULL DEFAULT '{}',
    branding JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_organization_settings_org ON organization_settings(organization_id);

CREATE TRIGGER update_organization_settings_updated_at 
    BEFORE UPDATE ON organization_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**Rollback:**
```sql
DROP TRIGGER IF EXISTS update_organization_settings_updated_at ON organization_settings;
DROP TABLE IF EXISTS organization_settings CASCADE;
```

---

### Migration 004: Add organization_id to existing tables

```sql
-- File: migrations/004_add_organization_id_to_existing_tables.sql

-- Add columns
ALTER TABLE wallets ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE transactions ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE signatures ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE contacts ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE scheduled_transactions ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE audit_logs ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

-- Add indexes
CREATE INDEX idx_wallets_organization ON wallets(organization_id);
CREATE INDEX idx_transactions_organization ON transactions(organization_id);
CREATE INDEX idx_signatures_organization ON signatures(organization_id);
CREATE INDEX idx_contacts_organization ON contacts(organization_id);
CREATE INDEX idx_scheduled_transactions_organization ON scheduled_transactions(organization_id);
CREATE INDEX idx_audit_logs_organization ON audit_logs(organization_id);
```

**Rollback:**
```sql
DROP INDEX IF EXISTS idx_audit_logs_organization;
DROP INDEX IF EXISTS idx_scheduled_transactions_organization;
DROP INDEX IF EXISTS idx_contacts_organization;
DROP INDEX IF EXISTS idx_signatures_organization;
DROP INDEX IF EXISTS idx_transactions_organization;
DROP INDEX IF EXISTS idx_wallets_organization;

ALTER TABLE audit_logs DROP COLUMN IF EXISTS organization_id;
ALTER TABLE scheduled_transactions DROP COLUMN IF EXISTS organization_id;
ALTER TABLE contacts DROP COLUMN IF EXISTS organization_id;
ALTER TABLE signatures DROP COLUMN IF EXISTS organization_id;
ALTER TABLE transactions DROP COLUMN IF EXISTS organization_id;
ALTER TABLE wallets DROP COLUMN IF EXISTS organization_id;
```

---

### Migration 005: Enable RLS policies

```sql
-- File: migrations/005_enable_rls_policies.sql

-- Enable RLS
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE signatures ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create policies
CREATE POLICY wallets_isolation_policy ON wallets
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

CREATE POLICY transactions_isolation_policy ON transactions
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

CREATE POLICY signatures_isolation_policy ON signatures
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

CREATE POLICY contacts_isolation_policy ON contacts
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

CREATE POLICY scheduled_transactions_isolation_policy ON scheduled_transactions
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );

CREATE POLICY audit_logs_isolation_policy ON audit_logs
    FOR SELECT
    USING (
        organization_id = current_setting('app.current_organization_id', true)::uuid
        OR current_setting('app.is_super_admin', true)::boolean = true
    );
```

**Rollback:**
```sql
DROP POLICY IF EXISTS audit_logs_isolation_policy ON audit_logs;
DROP POLICY IF EXISTS scheduled_transactions_isolation_policy ON scheduled_transactions;
DROP POLICY IF EXISTS contacts_isolation_policy ON contacts;
DROP POLICY IF EXISTS signatures_isolation_policy ON signatures;
DROP POLICY IF EXISTS transactions_isolation_policy ON transactions;
DROP POLICY IF EXISTS wallets_isolation_policy ON wallets;

ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE contacts DISABLE ROW LEVEL SECURITY;
ALTER TABLE signatures DISABLE ROW LEVEL SECURITY;
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;
ALTER TABLE wallets DISABLE ROW LEVEL SECURITY;
```

---

## 🧪 Testing Strategy

### 1. RLS Isolation Test

```sql
-- Setup: Create 2 organizations
INSERT INTO organizations (id, name, slug) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Org Alpha', 'org-alpha'),
    ('22222222-2222-2222-2222-222222222222', 'Org Beta', 'org-beta');

-- Create wallets for each
INSERT INTO wallets (id, organization_id, name) VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'Alpha Wallet'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', 'Beta Wallet');

-- Test: User from Org Alpha should only see Alpha Wallet
SET app.current_organization_id = '11111111-1111-1111-1111-111111111111';
SET app.is_super_admin = false;

SELECT * FROM wallets;
-- Expected: Only 'Alpha Wallet' returned

-- Test: Super Admin should see both
SET app.is_super_admin = true;

SELECT * FROM wallets;
-- Expected: Both wallets returned
```

### 2. Performance Test

```sql
-- Create 1000 organizations, 10 wallets each
-- Measure query time:
EXPLAIN ANALYZE
SELECT * FROM wallets 
WHERE organization_id = '11111111-1111-1111-1111-111111111111';

-- Expected: < 50ms with proper index
```

---

## 📈 ER Diagram

```
organizations (1) ────< (M) user_organizations (M) >──── (1) users
     │ (1)
     │
     └──< (1) organization_settings
     │
     └──< (M) wallets
     └──< (M) transactions
     └──< (M) signatures
     └──< (M) contacts
     └──< (M) scheduled_transactions
     └──< (M) audit_logs
```

---

## ✅ Completion Checklist

- [ ] Migrations 001-005 написаны
- [ ] Rollback scripts готовы
- [ ] ER diagram создан
- [ ] RLS тест прошел успешно
- [ ] Performance тест (< 50ms)
- [ ] Seed data (2 тестовые организации)
- [ ] Documentation complete

---

**Статус:** 🔄 В РАБОТЕ  
**ETA завершения:** 2026-02-12  
**Автор:** Forge 🔥
