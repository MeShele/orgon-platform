# Архитектура ORGON Platform

**Дата:** 13 февраля 2026  
**Версия:** 1.0  
**Статус:** Финальная версия  

---

## 🏗️ Обзор архитектуры

ORGON Platform построена как multi-tenant B2B WaaS решение с микросервисной архитектурой, обеспечивающей масштабируемость для 170+ криптообменников Кыргызстана. Платформа интегрируется с Safina API (KAZ.ONE) для кастодиальных услуг и поддерживает строгую изоляцию данных между организациями.

### Архитектурная диаграмма

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
├─────────────────────────┬───────────────────────────────────────┤
│ SuperAdmin Dashboard    │ White-Label Portals (170+ domains)   │
│ (ASYSTEM)               │ ex1.asystem.kg, ex2.asystem.kg       │
│ - Multi-org overview    │ - Organization-specific branding      │
│ - Revenue analytics     │ - Custom domain/subdomain            │
│ - Platform settings     │ - EndUser interfaces                  │
└─────────────────────────┴───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│ Next.js 16 + React 19 + TypeScript                            │
│ - SSR/SSG for SEO optimization                                 │
│ - Real-time updates (WebSocket/SSE)                           │
│ - Multi-language (ru/en/ky)                                   │
│ - Dynamic theming (CSS variables)                             │
│ - PWA capabilities                                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTPS/WSS
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY                              │
├─────────────────────────────────────────────────────────────────┤
│ FastAPI + Uvicorn                                              │
│ - Authentication/Authorization (JWT + RBAC)                   │
│ - Rate limiting (per organization)                            │
│ - API versioning (/api/v1, /api/v2)                          │
│ - Request/Response logging                                     │
│ - OpenAPI documentation                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BUSINESS LOGIC LAYER                        │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│ Organization    │ Wallet          │ Transaction     │ Billing   │
│ Service         │ Service         │ Service         │ Service   │
│ - Tenant mgmt   │ - Safina API    │ - Multi-sig     │ - Usage   │
│ - User mgmt     │ - Balance sync  │ - AML/KYC       │ - Invoices│
│ - RBAC          │ - Hot/Cold      │ - Status track  │ - Payments│
│ - White-label   │ - Multi-chain   │ - Webhooks      │ - Reports │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
│                                                                 │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│ Compliance      │ Analytics       │ Notification    │ Audit     │
│ Service         │ Service         │ Service         │ Service   │
│ - AML rules     │ - Metrics       │ - Email/SMS     │ - Action  │
│ - KYC tracking  │ - Reporting     │ - Push/Webhook  │ - Trail   │
│ - Regulatory    │ - Dashboards    │ - Escalation    │ - Export  │
│ - Risk scoring  │ - Export        │ - Templates     │ - Retention│
└─────────────────┴─────────────────┴─────────────────┴───────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│ PostgreSQL 16 (Primary) + Redis (Cache/Sessions)              │
│ - Row-Level Security (RLS) for multi-tenancy                  │
│ - Async connection pooling (asyncpg)                          │
│ - Backup/Replication                                          │
│ - Audit logging to separate tables                            │
│ - Encrypted sensitive data                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL INTEGRATIONS                       │
├─────────────────┬─────────────────┬─────────────────┬───────────┤
│ Safina API      │ Fiat Gateways   │ AML/KYC         │ Other     │
│ (KAZ.ONE)       │                 │ Providers       │ Services  │
│ - Custody       │ - ELSOM         │ - Chainalysis   │ - Email   │
│ - Wallets       │ - Megapay       │ - Elliptic      │ - SMS     │
│ - Transactions  │ - Banks KR      │ - Sumsub        │ - Push    │
│ - Multi-sig     │ - VISA/MC       │ - Onfido        │ - Backup  │
└─────────────────┴─────────────────┴─────────────────┴───────────┘
```

---

## 🏢 Multi-Tenancy архитектура

### Принцип изоляции данных

ORGON использует **PostgreSQL Row-Level Security (RLS)** для обеспечения строгой изоляции данных между организациями на уровне базы данных.

#### Схема организационной структуры

```sql
-- Основная таблица организаций
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL, -- для поддоменов
    legal_name TEXT NOT NULL,
    license_number TEXT, -- номер лицензии ПУВА
    tax_id TEXT,
    
    -- Тарифный план
    subscription_tier TEXT CHECK (subscription_tier IN ('A', 'B', 'C')),
    monthly_fee DECIMAL(10,2),
    transaction_fee_percent DECIMAL(5,4),
    
    -- Статус
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'archived')),
    
    -- White-label настройки
    brand_logo_url TEXT,
    primary_color TEXT DEFAULT '#3B82F6',
    secondary_color TEXT DEFAULT '#10B981',
    custom_domain TEXT,
    
    -- Даты
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    trial_ends_at TIMESTAMP
);

-- Пользователи с привязкой к организации
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    
    -- Роль в системе
    role TEXT NOT NULL CHECK (role IN ('super_admin', 'platform_admin', 'company_admin', 'company_operator', 'company_auditor', 'end_user')),
    
    -- Персональные данные
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    
    -- Настройки безопасности
    two_factor_enabled BOOLEAN DEFAULT false,
    two_factor_secret TEXT,
    allowed_ips INET[],
    
    -- Статус
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- RLS политики для таблицы кошельков
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    
    name TEXT NOT NULL,
    network INTEGER NOT NULL,
    wallet_type INTEGER,
    addr TEXT DEFAULT '',
    my_unid TEXT,
    
    -- Локальные метаданные
    label TEXT,
    is_favorite BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    synced_at TIMESTAMP,
    
    UNIQUE(organization_id, name)
);

-- Включение RLS
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;

-- Политика: пользователи видят только кошельки своей организации
CREATE POLICY org_isolation_wallets ON wallets 
    USING (organization_id = current_setting('app.current_organization_id')::UUID);

-- Аналогично для transactions, signatures и других таблиц
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation_transactions ON transactions 
    USING (organization_id = current_setting('app.current_organization_id')::UUID);
```

### Middleware для tenant isolation

```python
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import asyncpg

class TenantMiddleware:
    """Middleware для установки текущей организации в сессии БД."""
    
    async def __call__(self, request: Request, call_next):
        # Извлекаем organization_id из JWT токена или поддомена
        org_id = await self._extract_org_id(request)
        
        if org_id:
            # Устанавливаем текущую организацию в PostgreSQL сессии
            async with get_db().get_connection() as conn:
                await conn.execute(
                    "SET LOCAL app.current_organization_id = $1", 
                    org_id
                )
        
        response = await call_next(request)
        return response
    
    async def _extract_org_id(self, request: Request) -> str:
        # 1. Из JWT токена
        token = request.headers.get("Authorization")
        if token:
            payload = jwt.decode(token)
            return payload.get("organization_id")
        
        # 2. Из поддомена (для white-label)
        host = request.headers.get("host", "")
        if host.endswith(".asystem.kg"):
            subdomain = host.split(".")[0]
            org = await self._get_org_by_slug(subdomain)
            return org["id"] if org else None
        
        return None
```

---

## 👑 Управление SuperAdmin

### Dashboard для ASYSTEM

SuperAdmin (ASYSTEM) имеет специальный интерфейс для управления всей платформой:

#### Главная страница SuperAdmin

```typescript
// components/SuperAdminDashboard.tsx
interface SuperAdminMetrics {
    totalOrganizations: number;
    activeOrganizations: number;
    totalRevenue: number;
    monthlyRecurringRevenue: number;
    totalTransactions: number;
    totalVolume: string; // USD equivalent
    
    // Top performers
    topOrgsByVolume: Organization[];
    topOrgsByTransactions: Organization[];
    
    // System health
    safinaApiStatus: 'healthy' | 'degraded' | 'down';
    systemUptime: number; // percentage
    activeConnections: number;
}

const SuperAdminDashboard = () => {
    return (
        <div className="super-admin-dashboard">
            {/* Revenue Overview */}
            <div className="grid grid-cols-4 gap-6">
                <MetricCard 
                    title="Monthly Revenue" 
                    value={metrics.monthlyRecurringRevenue}
                    format="currency"
                    trend="+12.5%"
                />
                <MetricCard 
                    title="Active Organizations" 
                    value={metrics.activeOrganizations}
                    total={metrics.totalOrganizations}
                />
                <MetricCard 
                    title="Total Volume (24h)" 
                    value={metrics.totalVolume}
                    format="currency"
                />
                <MetricCard 
                    title="System Uptime" 
                    value={metrics.systemUptime}
                    format="percentage"
                />
            </div>
            
            {/* Organizations Management */}
            <div className="organizations-section">
                <h2>Organizations</h2>
                <OrganizationsTable 
                    data={organizations}
                    actions={['view', 'suspend', 'upgrade']}
                />
            </div>
            
            {/* Revenue Analytics */}
            <div className="revenue-chart">
                <RevenueChart 
                    timeframe="month"
                    breakdown={['saas_fees', 'transaction_fees', 'setup_fees']}
                />
            </div>
        </div>
    );
};
```

#### Управление организациями

```sql
-- Процедуры для SuperAdmin операций
CREATE OR REPLACE FUNCTION create_organization(
    p_name TEXT,
    p_slug TEXT,
    p_legal_name TEXT,
    p_license_number TEXT,
    p_subscription_tier TEXT DEFAULT 'A'
) RETURNS UUID AS $$
DECLARE
    new_org_id UUID;
BEGIN
    -- Создание организации
    INSERT INTO organizations (name, slug, legal_name, license_number, subscription_tier)
    VALUES (p_name, p_slug, p_legal_name, p_license_number, p_subscription_tier)
    RETURNING id INTO new_org_id;
    
    -- Создание базовых настроек
    INSERT INTO organization_settings (organization_id, key, value)
    VALUES 
        (new_org_id, 'fiat_gateway_enabled', 'false'),
        (new_org_id, 'max_daily_withdrawal', '10000'),
        (new_org_id, 'require_2fa', 'true');
    
    -- Создание audit записи
    INSERT INTO audit_log (organization_id, action, details)
    VALUES (new_org_id, 'organization_created', jsonb_build_object('tier', p_subscription_tier));
    
    RETURN new_org_id;
END;
$$ LANGUAGE plpgsql;
```

### Revenue Share с KAZ.ONE

```python
class RevenueCalculatorService:
    """Расчет доходов и revenue share с партнером."""
    
    async def calculate_monthly_revenue(self, org_id: str, month: str) -> dict:
        """Расчет месячного дохода организации."""
        
        # Получение всех транзакций за месяц
        transactions = await self.get_org_transactions(org_id, month)
        
        # Расчет комиссий
        setup_fees = await self.get_setup_fees(org_id, month)
        saas_fees = await self.get_saas_fees(org_id, month) 
        transaction_fees = sum(tx.fee for tx in transactions)
        
        total_revenue = setup_fees + saas_fees + transaction_fees
        
        # Revenue share с KAZ.ONE
        kazine_share = {
            'setup_fees': setup_fees * 0.5,  # 50% партнеру (если с их инженерами)
            'saas_fees': saas_fees * 0.7,    # 70% партнеру  
            'transaction_fees': transaction_fees * 0.5  # 50/50
        }
        
        asystem_share = total_revenue - sum(kazine_share.values())
        
        return {
            'organization_id': org_id,
            'month': month,
            'breakdown': {
                'setup_fees': setup_fees,
                'saas_fees': saas_fees, 
                'transaction_fees': transaction_fees
            },
            'total_revenue': total_revenue,
            'kazine_share': kazine_share,
            'asystem_share': asystem_share,
            'asystem_percentage': (asystem_share / total_revenue * 100) if total_revenue > 0 else 0
        }
```

---

## 🏪 Управление CompanyAdmin

### Настройка организации

CompanyAdmin имеет полный контроль над настройками своей организации:

#### Organization Settings страница

```typescript
interface OrganizationSettings {
    // Basic info
    name: string;
    legalName: string;
    taxId: string;
    licenseNumber: string;
    
    // Contact details  
    address: string;
    phone: string;
    email: string;
    website: string;
    
    // Business settings
    businessHours: {
        timezone: string;
        workdays: string[];
        startTime: string;
        endTime: string;
    };
    
    // Financial settings
    defaultCurrency: string;
    fiatGateways: FiatGateway[];
    withdrawalLimits: {
        daily: number;
        monthly: number;
        perTransaction: number;
    };
    
    // Security settings
    require2FA: boolean;
    ipWhitelist: string[];
    sessionTimeout: number; // minutes
    
    // Compliance settings
    amlProvider: 'chainalysis' | 'elliptic' | 'internal';
    kycRequired: boolean;
    suspiciousThreshold: number; // USD
    
    // White-label branding
    branding: {
        logo: string; // URL
        primaryColor: string;
        secondaryColor: string;
        customDomain: string;
        favicon: string;
    };
}

const OrganizationSettingsPage = () => {
    const [settings, setSettings] = useState<OrganizationSettings>();
    const [isLoading, setIsLoading] = useState(false);
    
    return (
        <div className="org-settings-page">
            <h1>Organization Settings</h1>
            
            <Tabs defaultValue="general">
                <TabsList>
                    <TabsTrigger value="general">General</TabsTrigger>
                    <TabsTrigger value="financial">Financial</TabsTrigger>
                    <TabsTrigger value="security">Security</TabsTrigger>
                    <TabsTrigger value="compliance">Compliance</TabsTrigger>
                    <TabsTrigger value="branding">Branding</TabsTrigger>
                </TabsList>
                
                <TabsContent value="general">
                    <GeneralSettingsForm settings={settings} />
                </TabsContent>
                
                <TabsContent value="financial">
                    <FiatGatewaySettings gateways={settings?.fiatGateways} />
                    <WithdrawalLimitsForm limits={settings?.withdrawalLimits} />
                </TabsContent>
                
                <TabsContent value="branding">
                    <BrandingCustomization branding={settings?.branding} />
                </TabsContent>
            </Tabs>
        </div>
    );
};
```

#### Управление пользователями организации

```sql
-- Процедуры для управления пользователями в организации
CREATE OR REPLACE FUNCTION invite_user_to_organization(
    p_org_id UUID,
    p_email TEXT,
    p_role TEXT,
    p_invited_by UUID
) RETURNS UUID AS $$
DECLARE
    new_user_id UUID;
    invite_token TEXT;
BEGIN
    -- Проверка прав приглашающего
    IF NOT EXISTS (
        SELECT 1 FROM users 
        WHERE id = p_invited_by 
        AND organization_id = p_org_id 
        AND role IN ('company_admin', 'super_admin')
    ) THEN
        RAISE EXCEPTION 'Insufficient permissions to invite users';
    END IF;
    
    -- Генерация invite token
    invite_token := encode(gen_random_bytes(32), 'hex');
    
    -- Создание pending invitation
    INSERT INTO user_invitations (
        organization_id,
        email,
        role,
        invited_by,
        token,
        expires_at
    ) VALUES (
        p_org_id,
        p_email,
        p_role,
        p_invited_by,
        invite_token,
        NOW() + INTERVAL '7 days'
    ) RETURNING id INTO new_user_id;
    
    -- Audit log
    INSERT INTO audit_log (organization_id, user_id, action, details)
    VALUES (p_org_id, p_invited_by, 'user_invited', jsonb_build_object(
        'email', p_email,
        'role', p_role,
        'token', invite_token
    ));
    
    RETURN new_user_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 👨‍💼 Интерфейс EndUser

### White-label портал для клиентов обменника

Каждый обменник получает собственный поддомен с персонализированным интерфейсом:

#### Архитектура white-label

```
Основной домен: app.orgon.space (ASYSTEM интерфейс)
                     ↓
White-label домены: 
├── ex1.asystem.kg (Обменник "Быстрый криптообмен")
├── ex2.asystem.kg (Обменник "CryptoHub")  
├── bitcoinkg.com  (Кастомный домен)
└── alamedaexchange.kg (Кастомный домен)

Каждый поддомен:
├── Уникальный брендинг (logo, colors, favicon)
├── Кастомизированные тексты (Welcome message)
├── Локальные контакты (support email/phone)
├── Интеграция с фиат-шлюзами обменника
└── Отдельная база клиентов (EndUser accounts)
```

#### EndUser Dashboard

```typescript
interface EndUserDashboard {
    // Персональная информация
    user: {
        fullName: string;
        email: string;
        phone: string;
        kycStatus: 'pending' | 'verified' | 'rejected';
        tier: 'basic' | 'verified' | 'premium';
    };
    
    // Кошельки пользователя
    wallets: {
        id: string;
        currency: string;
        balance: number;
        address: string;
        qrCode: string;
    }[];
    
    // Лимиты
    limits: {
        dailyWithdrawal: number;
        monthlyWithdrawal: number;
        remainingDaily: number;
        remainingMonthly: number;
    };
    
    // Последние операции
    recentTransactions: Transaction[];
}

const EndUserDashboard = () => {
    return (
        <div className="enduser-dashboard">
            {/* Welcome section с брендингом обменника */}
            <WelcomeSection 
                exchangeName={org.name}
                logo={org.branding.logo}
                colors={org.branding.colors}
            />
            
            {/* Portfolio overview */}
            <PortfolioSummary 
                totalBalance={portfolio.totalUSD}
                assets={portfolio.breakdown}
            />
            
            {/* Quick actions */}
            <QuickActions>
                <BuyButton />  {/* Интеграция с фиат-шлюзом */}
                <SellButton />
                <SendButton />
                <ReceiveButton />
            </QuickActions>
            
            {/* Recent activity */}
            <TransactionHistory 
                transactions={recentTransactions}
                limit={5}
            />
        </div>
    );
};
```

---

## 💰 Биллинг система

### Расчет использования (usage tracking)

```python
class UsageTrackingService:
    """Сервис для отслеживания использования ресурсов организацией."""
    
    async def track_api_call(self, org_id: str, endpoint: str, user_id: str):
        """Отслеживание API вызовов для rate limiting и биллинга."""
        await self.redis.hincrby(f"usage:{org_id}:{date.today()}", "api_calls", 1)
        await self.redis.hincrby(f"usage:{org_id}:{date.today()}", f"endpoint:{endpoint}", 1)
    
    async def track_transaction(self, org_id: str, amount_usd: float, network: str):
        """Отслеживание транзакций для комиссионного биллинга."""
        usage_key = f"usage:{org_id}:{date.today()}"
        
        await self.redis.hincrbyfloat(usage_key, "transaction_volume", amount_usd)
        await self.redis.hincrby(usage_key, "transaction_count", 1)
        await self.redis.hincrby(usage_key, f"network:{network}", 1)
    
    async def track_wallet_creation(self, org_id: str, wallet_type: str):
        """Отслеживание создания кошельков."""
        await self.redis.hincrby(f"usage:{org_id}:{date.today()}", "wallets_created", 1)
        await self.redis.hincrby(f"usage:{org_id}:{date.today()}", f"wallet_type:{wallet_type}", 1)
    
    async def get_monthly_usage(self, org_id: str, month: str) -> dict:
        """Получение статистики использования за месяц."""
        days_in_month = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
        
        total_usage = {}
        for day in range(1, days_in_month + 1):
            day_key = f"usage:{org_id}:{month}-{day:02d}"
            daily_usage = await self.redis.hgetall(day_key)
            
            for key, value in daily_usage.items():
                total_usage[key] = total_usage.get(key, 0) + float(value)
        
        return total_usage
```

### Выставление счетов

```python
class BillingService:
    """Сервис для генерации счетов и обработки платежей."""
    
    async def generate_monthly_invoice(self, org_id: str, month: str) -> dict:
        """Генерация ежемесячного счета для организации."""
        
        org = await self.org_service.get_organization(org_id)
        usage = await self.usage_service.get_monthly_usage(org_id, month)
        
        # Расчет стоимости по тарифному плану
        invoice_items = []
        
        # SaaS абонентская плата
        if org.subscription_tier == 'A':
            base_fee = min(usage.get('transaction_volume', 0) * 0.002, 200)  # 0.2%, макс $200
        elif org.subscription_tier == 'B':
            base_fee = 1500  # Фиксированная плата $1500
        else:  # Enterprise
            base_fee = org.custom_monthly_fee
        
        invoice_items.append({
            'description': f'SaaS Platform Fee ({org.subscription_tier})',
            'amount': base_fee,
            'quantity': 1
        })
        
        # Комиссии за транзакции
        if org.subscription_tier == 'A':
            tx_fee = usage.get('transaction_volume', 0) * 0.001  # 0.1%
        elif org.subscription_tier == 'B':
            tx_fee = usage.get('transaction_volume', 0) * 0.0005  # 0.05%
        else:
            tx_fee = 0  # Enterprise - только AUC комиссия
        
        if tx_fee > 0:
            invoice_items.append({
                'description': f'Transaction Fees ({usage.get("transaction_count", 0)} transactions)',
                'amount': tx_fee,
                'quantity': 1
            })
        
        # Комиссия за хранение (только Enterprise)
        if org.subscription_tier == 'C':
            auc_fee = await self.calculate_auc_fee(org_id, month)
            if auc_fee > 0:
                invoice_items.append({
                    'description': 'Assets Under Custody Fee (25 bps annual)',
                    'amount': auc_fee,
                    'quantity': 1
                })
        
        total_amount = sum(item['amount'] for item in invoice_items)
        
        # Создание записи в БД
        invoice = await self.create_invoice_record(org_id, month, invoice_items, total_amount)
        
        return {
            'invoice_id': invoice.id,
            'organization': org,
            'period': month,
            'items': invoice_items,
            'subtotal': total_amount,
            'tax': 0,  # НДС в КР не облагается для IT услуг
            'total': total_amount,
            'due_date': invoice.due_date,
            'status': 'pending'
        }
```

---

## 🛡️ Compliance система

### AML/KYT pipeline

```python
class ComplianceService:
    """Сервис для AML/KYT мониторинга и регуляторной отчетности."""
    
    async def analyze_transaction(self, transaction: Transaction) -> dict:
        """Анализ транзакции на соответствие AML требованиям."""
        
        risk_score = 0
        flags = []
        
        # 1. Проверка адресов через Chainalysis/Elliptic
        sender_risk = await self.check_address_risk(transaction.from_address)
        recipient_risk = await self.check_address_risk(transaction.to_address)
        
        if sender_risk.risk_level == 'high':
            risk_score += 50
            flags.append(f"High-risk sender: {sender_risk.reason}")
        
        if recipient_risk.risk_level == 'high':
            risk_score += 50
            flags.append(f"High-risk recipient: {recipient_risk.reason}")
        
        # 2. Проверка суммы (крупные операции)
        if transaction.amount_usd > 10000:
            risk_score += 20
            flags.append("Large transaction amount")
        
        # 3. Проверка паттернов (структурирование)
        recent_txs = await self.get_recent_transactions(
            transaction.organization_id, 
            hours=24
        )
        
        if len([tx for tx in recent_txs if tx.amount_usd > 9000]) > 3:
            risk_score += 30
            flags.append("Potential structuring pattern")
        
        # 4. Геолокационная проверка
        if await self.is_sanctioned_country(transaction.ip_address):
            risk_score += 40
            flags.append("Transaction from sanctioned country")
        
        # 5. KYC статус пользователя
        user_kyc = await self.get_user_kyc_status(transaction.user_id)
        if user_kyc.status != 'verified':
            risk_score += 25
            flags.append("User not verified")
        
        # Определение итогового уровня риска
        if risk_score >= 70:
            risk_level = 'high'
            action = 'block'
        elif risk_score >= 40:
            risk_level = 'medium'
            action = 'review'
        else:
            risk_level = 'low'
            action = 'approve'
        
        # Сохранение результатов анализа
        await self.save_compliance_record(transaction.id, {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'flags': flags,
            'action': action,
            'analyzed_at': datetime.utcnow()
        })
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'flags': flags,
            'recommended_action': action
        }
    
    async def generate_pуva_report(self, org_id: str, period: str) -> bytes:
        """Генерация отчета для Финнадзор КР."""
        
        # Получение всех транзакций организации за период
        transactions = await self.get_org_transactions(org_id, period)
        
        # Группировка данных для отчета
        report_data = {
            'organization': await self.org_service.get_organization(org_id),
            'period': period,
            'summary': {
                'total_transactions': len(transactions),
                'total_volume_usd': sum(tx.amount_usd for tx in transactions),
                'suspicious_transactions': len([tx for tx in transactions if tx.risk_score > 40]),
                'blocked_transactions': len([tx for tx in transactions if tx.status == 'blocked'])
            },
            'transactions': transactions,
            'compliance_actions': await self.get_compliance_actions(org_id, period)
        }
        
        # Генерация PDF отчета
        pdf_content = await self.render_puva_report_template(report_data)
        
        return pdf_content
```

---

## 🎨 White-label кастомизация

### Что кастомизируется

```typescript
interface WhiteLabelConfig {
    // Визуальное оформление
    branding: {
        logo: {
            primary: string;      // URL логотипа для header
            favicon: string;      // Favicon
            darkMode?: string;    // Логотип для темной темы
        };
        colors: {
            primary: string;      // Основной цвет (кнопки, ссылки)
            secondary: string;    // Дополнительный цвет
            accent: string;       // Акцентный цвет
            background: string;   // Цвет фона
            text: string;         // Основной цвет текста
        };
        typography: {
            fontFamily: string;   // Основной шрифт
            headingFont?: string; // Шрифт заголовков
        };
    };
    
    // Текстовый контент
    content: {
        companyName: string;
        welcomeMessage: string;
        footerText: string;
        supportEmail: string;
        supportPhone: string;
        termsOfServiceUrl?: string;
        privacyPolicyUrl?: string;
    };
    
    // Функциональные настройки
    features: {
        enabledCurrencies: string[];     // Доступные валюты
        enabledPaymentMethods: string[]; // Способы пополнения
        enabledLanguages: string[];      // Языки интерфейса
        showAdvancedFeatures: boolean;   // Показывать расширенные функции
    };
    
    // Интеграции
    integrations: {
        fiatGateways: FiatGatewayConfig[];
        kycProvider?: string;
        analyticsTracking?: {
            googleAnalytics?: string;
            facebookPixel?: string;
        };
    };
}
```

### Динамическая загрузка конфигурации

```python
class WhiteLabelService:
    """Сервис для управления white-label конфигурацией."""
    
    async def get_config_by_domain(self, domain: string) -> WhiteLabelConfig:
        """Получение конфигурации по домену."""
        
        # 1. Поиск по кастомному домену
        org = await self.org_service.get_by_custom_domain(domain)
        
        if not org:
            # 2. Поиск по поддомену asystem.kg
            if domain.endswith('.asystem.kg'):
                subdomain = domain.split('.')[0]
                org = await self.org_service.get_by_slug(subdomain)
        
        if not org:
            # 3. Возврат дефолтной конфигурации ORGON
            return await self.get_default_config()
        
        # 4. Формирование кастомной конфигурации
        return WhiteLabelConfig(
            branding={
                'logo': {
                    'primary': org.brand_logo_url or '/default-logo.svg',
                    'favicon': f'/api/organizations/{org.id}/favicon.ico'
                },
                'colors': {
                    'primary': org.primary_color or '#3B82F6',
                    'secondary': org.secondary_color or '#10B981',
                    'accent': org.accent_color or '#F59E0B',
                    'background': '#FFFFFF',
                    'text': '#1F2937'
                }
            },
            content={
                'companyName': org.name,
                'welcomeMessage': f'Добро пожаловать в {org.name}',
                'supportEmail': org.support_email or 'support@asystem.kg',
                'supportPhone': org.support_phone or '+996 XXX XXX XXX'
            },
            features={
                'enabledCurrencies': org.enabled_currencies or ['BTC', 'ETH', 'USDT'],
                'enabledPaymentMethods': org.enabled_payment_methods or ['bank_transfer'],
                'enabledLanguages': ['ru', 'ky', 'en']
            },
            integrations={
                'fiatGateways': await self.get_org_fiat_gateways(org.id),
                'kycProvider': org.kyc_provider
            }
        )
    
    async def apply_runtime_customization(self, config: WhiteLabelConfig) -> dict:
        """Применение кастомизации в runtime (CSS variables, JS config)."""
        
        css_variables = f"""
        :root {{
            --primary-color: {config.branding.colors.primary};
            --secondary-color: {config.branding.colors.secondary}; 
            --accent-color: {config.branding.colors.accent};
            --background-color: {config.branding.colors.background};
            --text-color: {config.branding.colors.text};
            --font-family: {config.branding.typography.fontFamily};
        }}
        """
        
        js_config = {
            'companyName': config.content.companyName,
            'features': config.features,
            'integrations': config.integrations,
            'supportContact': {
                'email': config.content.supportEmail,
                'phone': config.content.supportPhone
            }
        }
        
        return {
            'css': css_variables,
            'config': js_config,
            'meta': {
                'title': f'{config.content.companyName} - Криптообменник',
                'favicon': config.branding.logo.favicon
            }
        }
```

---

## 🔧 Техническая архитектура

### Масштабируемость

```yaml
# docker-compose.production.yml
version: '3.8'

services:
  # Load Balancer
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - backend-1
      - backend-2
      - backend-3

  # Backend instances (horizontal scaling)
  backend-1:
    build: .
    environment:
      - INSTANCE_ID=backend-1
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
  
  backend-2:
    build: .
    environment:
      - INSTANCE_ID=backend-2
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    deploy:
      resources:
        limits:
          cpus: '1.0' 
          memory: 1G
          
  backend-3:
    build: .
    environment:
      - INSTANCE_ID=backend-3
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  # Database cluster
  postgres-primary:
    image: postgres:16-alpine
    environment:
      - POSTGRES_REPLICATION_MODE=master
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=${REPLICATION_PASSWORD}
    volumes:
      - postgres-primary-data:/var/lib/postgresql/data

  postgres-replica:
    image: postgres:16-alpine
    environment:
      - POSTGRES_REPLICATION_MODE=slave
      - POSTGRES_MASTER_HOST=postgres-primary
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=${REPLICATION_PASSWORD}
    depends_on:
      - postgres-primary

  # Redis cluster
  redis-master:
    image: redis:7-alpine
    command: redis-server --save 20 1 --loglevel warning
    
  redis-replica:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379
    depends_on:
      - redis-master

  # Background workers
  worker-notifications:
    build: .
    command: python -m workers.notifications
    environment:
      - WORKER_TYPE=notifications
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}

  worker-billing:
    build: .
    command: python -m workers.billing
    environment:
      - WORKER_TYPE=billing
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}

  # Monitoring
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3001:3000"
    volumes:
      - grafana-data:/var/lib/grafana
```

### Performance мониторинг

```python
# metrics/collector.py
from prometheus_client import Counter, Histogram, Gauge
import time
import asyncio

# Метрики для мониторинга
REQUEST_COUNT = Counter('orgon_requests_total', 'Total requests', ['method', 'endpoint', 'organization'])
REQUEST_DURATION = Histogram('orgon_request_duration_seconds', 'Request duration', ['endpoint'])
ACTIVE_CONNECTIONS = Gauge('orgon_active_connections', 'Active DB connections')
SAFINA_API_STATUS = Gauge('orgon_safina_api_status', 'Safina API health (1=up, 0=down)')

class MetricsCollector:
    """Коллектор метрик для мониторинга performance."""
    
    def __init__(self):
        self.start_time = time.time()
        
    async def collect_system_metrics(self):
        """Сбор системных метрик каждые 30 секунд."""
        while True:
            try:
                # Database connections
                active_conns = await self.get_active_connections()
                ACTIVE_CONNECTIONS.set(active_conns)
                
                # Safina API health
                safina_health = await self.check_safina_health()
                SAFINA_API_STATUS.set(1 if safina_health else 0)
                
                # Memory usage
                memory_usage = await self.get_memory_usage()
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(30)
```

Данная архитектура обеспечивает масштабируемость, безопасность и compliance требования для обслуживания 170+ криптообменников с полной изоляцией данных и возможностью white-label кастомизации для каждого клиента.