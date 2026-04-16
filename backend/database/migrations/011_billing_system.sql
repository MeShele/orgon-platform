-- Migration 011: Billing System — Subscription Plans, Invoices, Payments
-- ORGON B2B Platform billing for tariff plans A/B/C
-- Date: 2026-02-14

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- SUBSCRIPTION PLANS TABLE
-- Tariff plans: A (Start), B (Business), C (Enterprise)
-- ============================================================================
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    monthly_price DECIMAL(12, 2) NOT NULL DEFAULT 0,
    yearly_price DECIMAL(12, 2),
    currency VARCHAR(10) DEFAULT 'KGS',
    features JSONB DEFAULT '{}',
    max_organizations INTEGER,
    max_wallets INTEGER,
    max_monthly_transactions INTEGER,
    max_monthly_volume_usd DECIMAL(18, 2),
    margin_min DECIMAL(5, 2),  -- minimum margin % for this plan
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- ORGANIZATION SUBSCRIPTIONS TABLE
-- Links partner/org to a plan
-- ============================================================================
CREATE TABLE IF NOT EXISTS organization_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending',  -- active, pending, expired, cancelled, suspended
    price DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KGS',
    is_trial BOOLEAN DEFAULT FALSE,
    trial_end_date TIMESTAMP WITH TIME ZONE,
    auto_renew BOOLEAN DEFAULT TRUE,
    payment_method VARCHAR(50),  -- manual, card, crypto, balance
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancellation_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_org_subscriptions_org ON organization_subscriptions(organization_id);
CREATE INDEX idx_org_subscriptions_status ON organization_subscriptions(status);
CREATE INDEX idx_org_subscriptions_end_date ON organization_subscriptions(end_date);

-- ============================================================================
-- INVOICES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES organization_subscriptions(id),
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    issue_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date TIMESTAMP WITH TIME ZONE,
    subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0,
    tax_rate DECIMAL(5, 2) DEFAULT 0,
    tax_amount DECIMAL(12, 2) DEFAULT 0,
    total DECIMAL(12, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'KGS',
    status VARCHAR(20) DEFAULT 'draft',  -- draft, sent, paid, overdue, cancelled
    line_items JSONB DEFAULT '[]',
    notes TEXT,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(255),
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_invoices_org ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);

-- ============================================================================
-- PAYMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id),
    payment_reference VARCHAR(255) UNIQUE NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'KGS',
    payment_method VARCHAR(50) NOT NULL,  -- manual, card, crypto, balance
    payment_gateway VARCHAR(50),  -- stripe, paybox, null for manual
    card_last4 VARCHAR(4),
    card_brand VARCHAR(20),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed, failed, refunded
    completed_at TIMESTAMP WITH TIME ZONE,
    failed_reason TEXT,
    gateway_response JSONB,
    admin_confirmed_by UUID,  -- for manual payments, which admin confirmed
    admin_confirmed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_payments_org ON payments(organization_id);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_status ON payments(status);

-- ============================================================================
-- TRANSACTION FEES TABLE (blockchain fees tracking for billing)
-- ============================================================================
CREATE TABLE IF NOT EXISTS transaction_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    transaction_id UUID,
    network VARCHAR(50),
    transaction_hash VARCHAR(255),
    amount DECIMAL(36, 18),
    token VARCHAR(50),
    amount_usd DECIMAL(18, 2),
    exchange_rate DECIMAL(18, 8),
    fee_type VARCHAR(50) DEFAULT 'blockchain',
    billable BOOLEAN DEFAULT TRUE,
    billed_in_invoice_id UUID REFERENCES invoices(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_transaction_fees_org ON transaction_fees(organization_id);
CREATE INDEX idx_transaction_fees_unbilled ON transaction_fees(organization_id, billable) WHERE billed_in_invoice_id IS NULL;

-- ============================================================================
-- SEED: Default subscription plans (A/B/C)
-- ============================================================================
INSERT INTO subscription_plans (name, slug, description, monthly_price, yearly_price, currency, margin_min, features, sort_order) VALUES
(
    'Start',
    'start',
    'Для малых обменников и финтех. AUC до $100K, оборот до $50K/мес.',
    50000, 540000, 'KGS', 3.0,
    '{"basic_support": true, "max_wallets": 1000, "max_transactions": 5000, "kyc_price": 1.0, "tx_commission": "0.2-0.5%", "crypto_acquiring": "0.8-1.2%"}'::jsonb,
    1
),
(
    'Business',
    'business',
    'Для средних бирж и брокеров. AUC $100K-$10M, оборот $100K-$1M/мес.',
    100000, 1080000, 'KGS', 2.0,
    '{"priority_support": true, "api_access": true, "white_label": true, "max_wallets": 50000, "max_transactions": 100000, "kyc_price": 0.5, "tx_commission": "0.1-0.3%", "crypto_acquiring": "0.6-0.9%"}'::jsonb,
    2
),
(
    'Enterprise',
    'enterprise',
    'Для банков и крупных бирж. AUC $10M+, оборот $1M+/мес.',
    200000, 2160000, 'KGS', 1.5,
    '{"dedicated_support": true, "api_access": true, "white_label": true, "sla_24_7": true, "dedicated_manager": true, "unlimited_wallets": true, "unlimited_transactions": true, "kyc_price": 0.3, "tx_commission": "0.05-0.15%", "crypto_acquiring": "0.4-0.7%"}'::jsonb,
    3
);
