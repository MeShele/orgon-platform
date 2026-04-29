-- Migration 006: Billing System
-- Created: 2026-02-11
-- Description: Subscription plans, subscriptions, invoices, payments, transaction fees

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLE: subscription_plans
-- ============================================
-- Tariff plans for organizations (Starter, Professional, Enterprise, etc.)

CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(50) NOT NULL UNIQUE, -- starter, professional, enterprise
    description TEXT,
    
    -- Pricing
    price_monthly DECIMAL(10, 2) NOT NULL, -- Monthly price in USD
    price_yearly DECIMAL(10, 2), -- Yearly price (optional, with discount)
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Features (JSON for flexibility)
    features JSONB NOT NULL DEFAULT '{}', -- {"max_users": 10, "max_wallets": 50, "api_calls_per_month": 10000}
    
    -- Limits
    max_users INTEGER, -- Maximum users per organization
    max_wallets INTEGER, -- Maximum wallets
    max_transactions_per_month INTEGER, -- Transaction limit
    
    -- Trial
    trial_days INTEGER DEFAULT 14, -- Free trial period
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_public BOOLEAN DEFAULT true, -- Visible in plan selector
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subscription_plans_slug ON subscription_plans(slug);
CREATE INDEX idx_subscription_plans_active ON subscription_plans(is_active);

COMMENT ON TABLE subscription_plans IS 'Tariff plans for organizations';
COMMENT ON COLUMN subscription_plans.features IS 'JSON object with plan features and limits';
COMMENT ON COLUMN subscription_plans.trial_days IS 'Number of days for free trial';

-- ============================================
-- TABLE: subscriptions
-- ============================================
-- Active subscriptions for organizations

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'trial', -- trial, active, past_due, cancelled, expired
    
    -- Dates
    trial_start_date TIMESTAMP,
    trial_end_date TIMESTAMP,
    start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_period_start TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    current_period_end TIMESTAMP NOT NULL,
    cancelled_at TIMESTAMP,
    ended_at TIMESTAMP,
    
    -- Billing
    billing_cycle VARCHAR(10) DEFAULT 'monthly', -- monthly, yearly
    next_billing_date TIMESTAMP,
    
    -- Usage tracking (for metered billing)
    current_usage JSONB DEFAULT '{}', -- {"users": 5, "wallets": 20, "api_calls": 500}
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT subscriptions_organization_unique UNIQUE(organization_id), -- One active subscription per org
    CONSTRAINT subscriptions_status_check CHECK (status IN ('trial', 'active', 'past_due', 'cancelled', 'expired'))
);

CREATE INDEX idx_subscriptions_organization ON subscriptions(organization_id);
CREATE INDEX idx_subscriptions_plan ON subscriptions(plan_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_next_billing ON subscriptions(next_billing_date);

COMMENT ON TABLE subscriptions IS 'Active subscriptions for organizations';
COMMENT ON COLUMN subscriptions.status IS 'trial: free trial, active: paid, past_due: payment failed, cancelled: user cancelled, expired: ended';
COMMENT ON COLUMN subscriptions.current_usage IS 'JSON object with current usage metrics for metered billing';

-- ============================================
-- TABLE: invoices
-- ============================================
-- Invoices for subscriptions and one-time charges

CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_number VARCHAR(20) NOT NULL UNIQUE, -- INV-2026-001234
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'draft', -- draft, open, paid, void, uncollectible
    
    -- Amounts
    subtotal DECIMAL(10, 2) NOT NULL DEFAULT 0,
    tax DECIMAL(10, 2) DEFAULT 0,
    discount DECIMAL(10, 2) DEFAULT 0,
    total DECIMAL(10, 2) NOT NULL,
    amount_paid DECIMAL(10, 2) DEFAULT 0,
    amount_due DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Dates
    issue_date DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    paid_at TIMESTAMP,
    voided_at TIMESTAMP,
    
    -- Billing period (for subscription invoices)
    period_start DATE,
    period_end DATE,
    
    -- Notes
    description TEXT, -- Optional description
    notes TEXT, -- Internal notes
    
    -- PDF generation
    pdf_url TEXT, -- S3/R2 URL to generated PDF
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT invoices_status_check CHECK (status IN ('draft', 'open', 'paid', 'void', 'uncollectible')),
    CONSTRAINT invoices_amount_check CHECK (total >= 0 AND amount_due >= 0)
);

CREATE INDEX idx_invoices_organization ON invoices(organization_id);
CREATE INDEX idx_invoices_subscription ON invoices(subscription_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_number ON invoices(invoice_number);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);

COMMENT ON TABLE invoices IS 'Invoices for subscriptions and one-time charges';
COMMENT ON COLUMN invoices.invoice_number IS 'Human-readable invoice number (INV-YYYY-NNNNNN)';
COMMENT ON COLUMN invoices.status IS 'draft: not finalized, open: awaiting payment, paid: fully paid, void: cancelled, uncollectible: write-off';

-- ============================================
-- TABLE: invoice_line_items
-- ============================================
-- Line items for invoices (subscription, fees, one-time charges)

CREATE TABLE IF NOT EXISTS invoice_line_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    
    -- Item details
    description VARCHAR(255) NOT NULL, -- "Professional Plan - February 2026"
    item_type VARCHAR(50) NOT NULL, -- subscription, transaction_fee, one_time_charge, adjustment
    
    -- Pricing
    quantity DECIMAL(10, 2) DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL, -- quantity * unit_price
    
    -- Tax
    tax_rate DECIMAL(5, 2) DEFAULT 0, -- Percentage (e.g., 12.00 for 12%)
    tax_amount DECIMAL(10, 2) DEFAULT 0,
    
    -- Period (for recurring items)
    period_start DATE,
    period_end DATE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}', -- Additional data (e.g., {"transaction_id": "..."})
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_invoice_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX idx_invoice_line_items_type ON invoice_line_items(item_type);

COMMENT ON TABLE invoice_line_items IS 'Line items for invoices (subscription, fees, charges)';
COMMENT ON COLUMN invoice_line_items.item_type IS 'subscription, transaction_fee, one_time_charge, adjustment';

-- ============================================
-- TABLE: payments
-- ============================================
-- Payments made for invoices

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_number VARCHAR(20) NOT NULL UNIQUE, -- PAY-2026-001234
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Amount
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, succeeded, failed, refunded
    
    -- Payment method
    payment_method VARCHAR(50), -- card, bank_transfer, crypto, manual
    payment_gateway VARCHAR(50), -- stripe, paypal, manual, etc.
    gateway_transaction_id VARCHAR(100), -- External transaction ID
    
    -- Dates
    paid_at TIMESTAMP,
    failed_at TIMESTAMP,
    refunded_at TIMESTAMP,
    
    -- Failure details
    failure_reason TEXT,
    
    -- Refund
    refund_amount DECIMAL(10, 2) DEFAULT 0,
    refund_reason TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}', -- Gateway-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT payments_status_check CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded')),
    CONSTRAINT payments_amount_check CHECK (amount > 0)
);

CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_organization ON payments(organization_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_number ON payments(payment_number);
CREATE INDEX idx_payments_gateway_txn ON payments(gateway_transaction_id);

COMMENT ON TABLE payments IS 'Payments made for invoices';
COMMENT ON COLUMN payments.payment_method IS 'card, bank_transfer, crypto, manual';
COMMENT ON COLUMN payments.status IS 'pending: processing, succeeded: completed, failed: payment failed, refunded: money returned';

-- ============================================
-- TABLE: transaction_fees
-- ============================================
-- Fees charged for transactions (withdrawals, exchanges, etc.)

CREATE TABLE IF NOT EXISTS transaction_fees (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Transaction details
    transaction_type VARCHAR(50) NOT NULL, -- withdrawal, deposit, exchange, transfer
    transaction_id UUID, -- Reference to actual transaction (if exists in other tables)
    
    -- Fee details
    fee_type VARCHAR(50) NOT NULL, -- percentage, fixed, tiered
    fee_amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    
    -- Calculation
    base_amount DECIMAL(10, 2), -- Original transaction amount
    fee_rate DECIMAL(5, 4), -- If percentage-based (e.g., 0.0250 for 2.5%)
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, invoiced, paid
    invoice_id UUID REFERENCES invoices(id) ON DELETE SET NULL, -- Link to invoice when billed
    
    -- Dates
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    invoiced_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}', -- Additional transaction details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT transaction_fees_status_check CHECK (status IN ('pending', 'invoiced', 'paid'))
);

CREATE INDEX idx_transaction_fees_organization ON transaction_fees(organization_id);
CREATE INDEX idx_transaction_fees_type ON transaction_fees(transaction_type);
CREATE INDEX idx_transaction_fees_status ON transaction_fees(status);
CREATE INDEX idx_transaction_fees_invoice ON transaction_fees(invoice_id);
CREATE INDEX idx_transaction_fees_date ON transaction_fees(transaction_date);

COMMENT ON TABLE transaction_fees IS 'Fees charged for transactions (withdrawals, exchanges, etc.)';
COMMENT ON COLUMN transaction_fees.transaction_type IS 'withdrawal, deposit, exchange, transfer';
COMMENT ON COLUMN transaction_fees.fee_type IS 'percentage, fixed, tiered';
COMMENT ON COLUMN transaction_fees.status IS 'pending: not billed yet, invoiced: added to invoice, paid: invoice paid';

-- ============================================
-- RLS POLICIES
-- ============================================
-- Enable RLS on all billing tables

ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE transaction_fees ENABLE ROW LEVEL SECURITY;

-- Subscription Plans: Everyone can read (for plan selection), only super_admin can write
CREATE POLICY subscription_plans_select ON subscription_plans
    FOR SELECT
    USING (true); -- Public plans visible to all

CREATE POLICY subscription_plans_insert ON subscription_plans
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = current_setting('app.current_user_id')::UUID 
            AND users.role = 'super_admin'
        )
    );

CREATE POLICY subscription_plans_update ON subscription_plans
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = current_setting('app.current_user_id')::UUID 
            AND users.role = 'super_admin'
        )
    );

-- Subscriptions: Org members can read their subscription, super_admin can read all
CREATE POLICY subscriptions_select ON subscriptions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = subscriptions.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
        )
    );

CREATE POLICY subscriptions_insert ON subscriptions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = subscriptions.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
            AND user_organizations.role = 'admin'
        )
        )
    );

CREATE POLICY subscriptions_update ON subscriptions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = subscriptions.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
            AND user_organizations.role = 'admin'
        )
        )
    );

-- Invoices: Org members can read their invoices
CREATE POLICY invoices_select ON invoices
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = invoices.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
        )
    );

-- Invoice Line Items: Accessible through invoice
CREATE POLICY invoice_line_items_select ON invoice_line_items
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM invoices
            JOIN user_organizations ON user_organizations.organization_id = invoices.organization_id
            WHERE invoices.id = invoice_line_items.invoice_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
        )
    );

-- Payments: Org members can read their payments
CREATE POLICY payments_select ON payments
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = payments.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
        )
    );

-- Transaction Fees: Org members can read their fees
CREATE POLICY transaction_fees_select ON transaction_fees
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = transaction_fees.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
        )
    );

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function: Generate invoice number (INV-YYYY-NNNNNN)
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS VARCHAR(20) AS $$
DECLARE
    current_year INTEGER;
    next_number INTEGER;
    invoice_num VARCHAR(20);
BEGIN
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    
    -- Get next number for this year
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(invoice_number FROM 10) AS INTEGER)
    ), 0) + 1 INTO next_number
    FROM invoices
    WHERE SUBSTRING(invoice_number FROM 5 FOR 4) = current_year::TEXT;
    
    -- Format: INV-2026-001234
    invoice_num := 'INV-' || current_year || '-' || LPAD(next_number::TEXT, 6, '0');
    
    RETURN invoice_num;
END;
$$ LANGUAGE plpgsql;

-- Function: Generate payment number (PAY-YYYY-NNNNNN)
CREATE OR REPLACE FUNCTION generate_payment_number()
RETURNS VARCHAR(20) AS $$
DECLARE
    current_year INTEGER;
    next_number INTEGER;
    payment_num VARCHAR(20);
BEGIN
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    
    -- Get next number for this year
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(payment_number FROM 10) AS INTEGER)
    ), 0) + 1 INTO next_number
    FROM payments
    WHERE SUBSTRING(payment_number FROM 5 FOR 4) = current_year::TEXT;
    
    -- Format: PAY-2026-001234
    payment_num := 'PAY-' || current_year || '-' || LPAD(next_number::TEXT, 6, '0');
    
    RETURN payment_num;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate subscription next billing date
CREATE OR REPLACE FUNCTION calculate_next_billing_date(
    start_date TIMESTAMP,
    billing_cycle VARCHAR(10)
)
RETURNS TIMESTAMP AS $$
BEGIN
    IF billing_cycle = 'monthly' THEN
        RETURN start_date + INTERVAL '1 month';
    ELSIF billing_cycle = 'yearly' THEN
        RETURN start_date + INTERVAL '1 year';
    ELSE
        RETURN start_date + INTERVAL '1 month'; -- Default to monthly
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

-- Trigger: Auto-generate invoice number on insert
CREATE OR REPLACE FUNCTION trigger_generate_invoice_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.invoice_number IS NULL THEN
        NEW.invoice_number := generate_invoice_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_insert_invoice_number
BEFORE INSERT ON invoices
FOR EACH ROW
EXECUTE FUNCTION trigger_generate_invoice_number();

-- Trigger: Auto-generate payment number on insert
CREATE OR REPLACE FUNCTION trigger_generate_payment_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.payment_number IS NULL THEN
        NEW.payment_number := generate_payment_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_insert_payment_number
BEFORE INSERT ON payments
FOR EACH ROW
EXECUTE FUNCTION trigger_generate_payment_number();

-- Trigger: Update invoice updated_at on change
CREATE OR REPLACE FUNCTION trigger_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER before_update_invoices_timestamp
BEFORE UPDATE ON invoices
FOR EACH ROW
EXECUTE FUNCTION trigger_update_timestamp();

CREATE TRIGGER before_update_subscriptions_timestamp
BEFORE UPDATE ON subscriptions
FOR EACH ROW
EXECUTE FUNCTION trigger_update_timestamp();

CREATE TRIGGER before_update_subscription_plans_timestamp
BEFORE UPDATE ON subscription_plans
FOR EACH ROW
EXECUTE FUNCTION trigger_update_timestamp();

CREATE TRIGGER before_update_payments_timestamp
BEFORE UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION trigger_update_timestamp();

-- ============================================
-- SEED DATA
-- ============================================

-- Insert sample subscription plans
INSERT INTO subscription_plans (name, slug, description, price_monthly, price_yearly, features, max_users, max_wallets, max_transactions_per_month, trial_days)
VALUES
    (
        'Starter',
        'starter',
        'Perfect for small crypto exchanges starting out',
        99.00,
        990.00, -- 2 months free
        '{"api_calls_per_month": 10000, "support": "email", "custom_branding": false, "white_label": false}'::jsonb,
        10,
        50,
        1000,
        14
    ),
    (
        'Professional',
        'professional',
        'For growing exchanges with advanced needs',
        299.00,
        2990.00, -- 2 months free
        '{"api_calls_per_month": 100000, "support": "priority", "custom_branding": true, "white_label": false, "advanced_analytics": true}'::jsonb,
        50,
        500,
        10000,
        14
    ),
    (
        'Enterprise',
        'enterprise',
        'Full white-label solution for large exchanges',
        999.00,
        9990.00, -- 2 months free
        '{"api_calls_per_month": -1, "support": "24/7", "custom_branding": true, "white_label": true, "advanced_analytics": true, "dedicated_account_manager": true}'::jsonb,
        NULL, -- Unlimited
        NULL, -- Unlimited
        NULL, -- Unlimited
        30
    );

-- Grant usage on sequences (for testing)
-- Note: UUID generation doesn't use sequences, so this is just for completeness
