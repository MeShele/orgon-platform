-- Migration 009: Fiat Integration Tables
-- Phase: 3.2 Fiat Integration
-- Date: 2026-02-12
-- Description: On-ramp/off-ramp, bank accounts, payment gateways

-- ============================================================
-- FIAT TABLES
-- ============================================================

-- 1. Fiat Transactions (on-ramp/off-ramp)
CREATE TABLE fiat_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Transaction type
    transaction_type VARCHAR(20) NOT NULL,  -- onramp/offramp
    
    -- Amounts
    fiat_amount NUMERIC(12,2) NOT NULL,
    fiat_currency VARCHAR(3) NOT NULL,  -- USD/EUR/GBP
    
    crypto_amount NUMERIC(20,8),  -- May be NULL until confirmed
    crypto_currency VARCHAR(10),  -- BTC/ETH/USDT/TRX
    
    exchange_rate NUMERIC(12,6),  -- Fiat per 1 crypto
    
    -- Payment details
    payment_method VARCHAR(50),  -- stripe/paypal/bank_transfer
    payment_gateway VARCHAR(50),  -- stripe/paypal/manual
    gateway_transaction_id VARCHAR(255),  -- External payment ID
    
    -- Bank account (for off-ramp)
    bank_account_id UUID,  -- FK added after bank_accounts table created
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    -- pending/processing/completed/failed/cancelled/refunded
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT fiat_txn_valid_type CHECK (transaction_type IN ('onramp', 'offramp')),
    CONSTRAINT fiat_txn_valid_status 
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'refunded'))
);

CREATE INDEX idx_fiat_txn_org ON fiat_transactions(organization_id);
CREATE INDEX idx_fiat_txn_user ON fiat_transactions(user_id);
CREATE INDEX idx_fiat_txn_type ON fiat_transactions(transaction_type);
CREATE INDEX idx_fiat_txn_status ON fiat_transactions(status);
CREATE INDEX idx_fiat_txn_gateway_id ON fiat_transactions(gateway_transaction_id);
CREATE INDEX idx_fiat_txn_created ON fiat_transactions(created_at DESC);

-- 2. Bank Accounts (for withdrawals)
CREATE TABLE bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Bank details
    account_holder_name VARCHAR(255) NOT NULL,
    bank_name VARCHAR(255),
    
    -- Account number (encrypted in production)
    account_number_last4 VARCHAR(4),  -- Last 4 digits for display
    account_number_encrypted TEXT,  -- Full number encrypted
    
    -- Routing
    routing_number VARCHAR(50),  -- US ACH
    iban VARCHAR(34),  -- International
    swift_code VARCHAR(11),  -- SWIFT/BIC
    
    -- Address
    bank_country VARCHAR(2),  -- ISO 3166-1 alpha-2
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Verification
    verification_status VARCHAR(20) DEFAULT 'pending',
    -- pending/verified/rejected
    
    verification_method VARCHAR(50),  -- micro_deposits/instant/manual
    verified_at TIMESTAMPTZ,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT bank_account_valid_verification 
        CHECK (verification_status IN ('pending', 'verified', 'rejected'))
);

CREATE INDEX idx_bank_accounts_org ON bank_accounts(organization_id);
CREATE INDEX idx_bank_accounts_user ON bank_accounts(user_id);
CREATE INDEX idx_bank_accounts_status ON bank_accounts(verification_status);

CREATE TRIGGER update_bank_accounts_updated_at 
    BEFORE UPDATE ON bank_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add FK constraint to fiat_transactions now that bank_accounts exists
ALTER TABLE fiat_transactions
    ADD CONSTRAINT fk_fiat_txn_bank_account
    FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id) ON DELETE SET NULL;

-- 3. Payment Gateways Configuration
CREATE TABLE payment_gateways (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Gateway details
    gateway_name VARCHAR(50) NOT NULL,  -- stripe/paypal/bank_transfer
    gateway_type VARCHAR(20) NOT NULL,  -- card/bank/crypto
    
    -- Configuration (API keys, etc. - encrypted)
    config JSONB NOT NULL DEFAULT '{}',
    -- Example: {"publishable_key": "pk_...", "secret_key": "sk_..."}
    
    -- Fees
    fee_percentage NUMERIC(5,2) DEFAULT 0,  -- % fee
    fee_fixed NUMERIC(12,2) DEFAULT 0,  -- Fixed fee in fiat_currency
    fiat_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Limits
    min_amount NUMERIC(12,2),
    max_amount NUMERIC(12,2),
    daily_limit NUMERIC(12,2),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_test_mode BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(organization_id, gateway_name)
);

CREATE INDEX idx_payment_gateways_org ON payment_gateways(organization_id);
CREATE INDEX idx_payment_gateways_active ON payment_gateways(is_active);

CREATE TRIGGER update_payment_gateways_updated_at 
    BEFORE UPDATE ON payment_gateways
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Crypto Exchange Rates (cache)
CREATE TABLE crypto_exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Pair
    crypto_currency VARCHAR(10) NOT NULL,  -- BTC/ETH/USDT
    fiat_currency VARCHAR(3) NOT NULL,  -- USD/EUR/GBP
    
    -- Rate
    rate NUMERIC(12,6) NOT NULL,  -- Fiat per 1 crypto
    
    -- Source
    source VARCHAR(50) DEFAULT 'coingecko',  -- coingecko/safina/binance
    
    -- Timestamp
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(crypto_currency, fiat_currency, source)
);

CREATE INDEX idx_exchange_rates_pair ON crypto_exchange_rates(crypto_currency, fiat_currency);
CREATE INDEX idx_exchange_rates_fetched ON crypto_exchange_rates(fetched_at DESC);

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE fiat_transactions IS 'Fiat on-ramp/off-ramp transactions';
COMMENT ON TABLE bank_accounts IS 'User bank accounts for fiat withdrawals';
COMMENT ON TABLE payment_gateways IS 'Payment gateway configurations (Stripe, PayPal, etc.)';
COMMENT ON TABLE crypto_exchange_rates IS 'Cached crypto-to-fiat exchange rates';

-- ============================================================
-- SEED DATA
-- ============================================================

-- Default payment gateways (system-wide)
-- Organizations can enable/configure these via API
