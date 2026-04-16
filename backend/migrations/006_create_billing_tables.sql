-- Migration 006: Billing System Tables
-- Phase: 2.1 Billing System
-- Date: 2026-02-11
-- Description: Subscription management, invoices, payments, transaction fees

-- ============================================================
-- BILLING TABLES
-- ============================================================

-- 1. Subscription Plans (pricing tiers for organizations)
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,  -- Free, Pro, Enterprise
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    
    -- Pricing
    monthly_price NUMERIC(10,2) NOT NULL DEFAULT 0,
    yearly_price NUMERIC(10,2),  -- Annual pricing (optional discount)
    
    -- Features
    features JSONB DEFAULT '{}',
    -- Example: {"max_wallets": 10, "max_transactions_per_month": 1000, "api_access": true}
    
    -- Limits
    max_organizations INT,  -- NULL = unlimited
    max_wallets INT,
    max_monthly_transactions INT,
    max_monthly_volume_usd NUMERIC(15,2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscription_plans_slug ON subscription_plans(slug);
CREATE INDEX idx_subscription_plans_active ON subscription_plans(is_active);

-- Trigger for updated_at
CREATE TRIGGER update_subscription_plans_updated_at 
    BEFORE UPDATE ON subscription_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2. Organization Subscriptions
CREATE TABLE organization_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    
    -- Billing cycle
    billing_cycle VARCHAR(20) DEFAULT 'monthly',  -- monthly/yearly
    start_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_date TIMESTAMPTZ,  -- NULL = active/ongoing
    
    -- Status
    status VARCHAR(20) DEFAULT 'active',  -- active/suspended/cancelled/expired
    -- active: paying and working
    -- suspended: payment failed, grace period
    -- cancelled: user cancelled, working until end_date
    -- expired: end_date passed, no renewal
    
    -- Pricing (captured at subscription time, may differ from current plan price)
    price NUMERIC(10,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Trial
    trial_end_date TIMESTAMPTZ,
    is_trial BOOLEAN DEFAULT FALSE,
    
    -- Auto-renewal
    auto_renew BOOLEAN DEFAULT TRUE,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_org_subscriptions_org ON organization_subscriptions(organization_id);
CREATE INDEX idx_org_subscriptions_plan ON organization_subscriptions(plan_id);
CREATE INDEX idx_org_subscriptions_status ON organization_subscriptions(status);
CREATE INDEX idx_org_subscriptions_end_date ON organization_subscriptions(end_date);

CREATE TRIGGER update_org_subscriptions_updated_at 
    BEFORE UPDATE ON organization_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 3. Invoices
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES organization_subscriptions(id) ON DELETE SET NULL,
    
    -- Invoice details
    invoice_number VARCHAR(50) UNIQUE NOT NULL,  -- Auto-generated: INV-2026-0001
    issue_date TIMESTAMPTZ DEFAULT NOW(),
    due_date TIMESTAMPTZ NOT NULL,
    
    -- Amounts
    subtotal NUMERIC(12,2) NOT NULL,
    tax_rate NUMERIC(5,2) DEFAULT 0,  -- Percentage (e.g., 18.00 for 18%)
    tax_amount NUMERIC(12,2) DEFAULT 0,
    total NUMERIC(12,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft/sent/paid/overdue/cancelled
    paid_at TIMESTAMPTZ,
    
    -- Payment
    payment_method VARCHAR(50),  -- card/bank_transfer/crypto
    payment_reference VARCHAR(100),  -- Transaction ID from payment gateway
    
    -- Line items (detailed breakdown)
    line_items JSONB DEFAULT '[]',
    -- Example: [{"description": "Pro Plan - Jan 2026", "quantity": 1, "unit_price": 99.00, "total": 99.00}]
    
    -- Notes
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_org ON invoices(organization_id);
CREATE INDEX idx_invoices_subscription ON invoices(subscription_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_invoices_number ON invoices(invoice_number);

CREATE TRIGGER update_invoices_updated_at 
    BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    
    -- Payment details
    payment_reference VARCHAR(100) UNIQUE NOT NULL,  -- From payment gateway
    amount NUMERIC(12,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    
    -- Method
    payment_method VARCHAR(50) NOT NULL,  -- card/bank_transfer/crypto/balance
    payment_gateway VARCHAR(50),  -- stripe/paypal/crypto_gateway
    
    -- Card details (if applicable, encrypted)
    card_last4 VARCHAR(4),
    card_brand VARCHAR(20),  -- visa/mastercard/amex
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending/completed/failed/refunded
    completed_at TIMESTAMPTZ,
    failed_reason TEXT,
    
    -- Refund
    refunded_at TIMESTAMPTZ,
    refund_amount NUMERIC(12,2),
    refund_reason TEXT,
    
    -- Gateway response
    gateway_response JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_org ON payments(organization_id);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_reference ON payments(payment_reference);
CREATE INDEX idx_payments_status ON payments(status);

CREATE TRIGGER update_payments_updated_at 
    BEFORE UPDATE ON payments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. Transaction Fees (blockchain transaction commissions)
CREATE TABLE transaction_fees (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    
    -- Fee details
    network VARCHAR(20) NOT NULL,  -- tron/bsc/ethereum
    transaction_hash VARCHAR(100),
    
    -- Amounts
    amount NUMERIC(20,6) NOT NULL,  -- Fee amount in native token (TRX/BNB/ETH)
    token VARCHAR(20) NOT NULL DEFAULT 'TRX',
    amount_usd NUMERIC(12,2),  -- USD equivalent at time of transaction
    
    -- Rate
    exchange_rate NUMERIC(12,6),  -- Token to USD rate
    
    -- Type
    fee_type VARCHAR(30) DEFAULT 'transaction',  -- transaction/contract_call/token_transfer
    
    -- Billing
    billable BOOLEAN DEFAULT TRUE,
    billed_in_invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transaction_fees_org ON transaction_fees(organization_id);
CREATE INDEX idx_transaction_fees_transaction ON transaction_fees(transaction_id);
CREATE INDEX idx_transaction_fees_network ON transaction_fees(network);
CREATE INDEX idx_transaction_fees_billable ON transaction_fees(billable);
CREATE INDEX idx_transaction_fees_invoice ON transaction_fees(billed_in_invoice_id);

-- 6. Payment Methods (saved cards, bank accounts for org)
CREATE TABLE organization_payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Method details
    type VARCHAR(20) NOT NULL,  -- card/bank_account
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Card (if type=card)
    card_last4 VARCHAR(4),
    card_brand VARCHAR(20),
    card_exp_month INT,
    card_exp_year INT,
    card_holder_name VARCHAR(100),
    
    -- Bank account (if type=bank_account)
    bank_name VARCHAR(100),
    account_last4 VARCHAR(4),
    account_holder_name VARCHAR(100),
    
    -- Gateway
    payment_gateway VARCHAR(50),  -- stripe/paypal
    gateway_payment_method_id VARCHAR(100),  -- ID in payment gateway
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_org_payment_methods_org ON organization_payment_methods(organization_id);
CREATE INDEX idx_org_payment_methods_default ON organization_payment_methods(is_default);

CREATE TRIGGER update_org_payment_methods_updated_at 
    BEFORE UPDATE ON organization_payment_methods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- CONSTRAINTS & CHECKS
-- ============================================================

-- Ensure only one default payment method per organization
CREATE UNIQUE INDEX idx_org_payment_methods_one_default 
    ON organization_payment_methods(organization_id) 
    WHERE is_default = TRUE;

-- Invoice number format check
ALTER TABLE invoices 
    ADD CONSTRAINT invoices_number_format 
    CHECK (invoice_number ~ '^INV-[0-9]{4}-[0-9]{4,6}$');

-- Positive amounts
ALTER TABLE invoices 
    ADD CONSTRAINT invoices_positive_amounts 
    CHECK (subtotal >= 0 AND total >= 0);

ALTER TABLE payments 
    ADD CONSTRAINT payments_positive_amount 
    CHECK (amount >= 0);

-- Valid statuses
ALTER TABLE organization_subscriptions 
    ADD CONSTRAINT org_subscriptions_valid_status 
    CHECK (status IN ('active', 'suspended', 'cancelled', 'expired'));

ALTER TABLE invoices 
    ADD CONSTRAINT invoices_valid_status 
    CHECK (status IN ('draft', 'sent', 'paid', 'overdue', 'cancelled'));

ALTER TABLE payments 
    ADD CONSTRAINT payments_valid_status 
    CHECK (status IN ('pending', 'completed', 'failed', 'refunded'));

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE subscription_plans IS 'Pricing tiers (Free, Pro, Enterprise)';
COMMENT ON TABLE organization_subscriptions IS 'Active subscriptions for organizations';
COMMENT ON TABLE invoices IS 'Monthly invoices for subscriptions and fees';
COMMENT ON TABLE payments IS 'Payment records (card, bank transfer, crypto)';
COMMENT ON TABLE transaction_fees IS 'Blockchain transaction fees to bill';
COMMENT ON TABLE organization_payment_methods IS 'Saved payment methods for organizations';

-- ============================================================
-- SEED DATA
-- ============================================================

-- Default subscription plans
INSERT INTO subscription_plans (name, slug, description, monthly_price, yearly_price, features, max_wallets, max_monthly_transactions, max_monthly_volume_usd) VALUES
('Free', 'free', 'For testing and small exchanges', 0, 0, '{"api_access": false, "support": "community"}', 5, 100, 10000),
('Pro', 'pro', 'For growing exchanges', 99.00, 990.00, '{"api_access": true, "support": "email", "custom_branding": false}', 50, 10000, 500000),
('Enterprise', 'enterprise', 'For large exchanges (170+ like Asystem)', 499.00, 4990.00, '{"api_access": true, "support": "priority", "custom_branding": true, "white_label": true}', NULL, NULL, NULL);
