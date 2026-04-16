-- Migration 008: ASYSTEM B2B Platform Foundation
-- Phase 1: Partner Management, API Keys, Audit Log
-- Date: 2026-02-08

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- PARTNERS TABLE
-- Core B2B partner/tenant management
-- ============================================================================
CREATE TABLE IF NOT EXISTS partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    api_secret_hash VARCHAR(255) NOT NULL,
    tier VARCHAR(50) DEFAULT 'free', -- free, starter, business, enterprise
    rate_limit_per_minute INTEGER DEFAULT 60,
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),
    ec_address VARCHAR(42) UNIQUE NOT NULL, -- Partner's EC address
    status VARCHAR(20) DEFAULT 'active', -- active, suspended, deleted
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for partners
CREATE INDEX idx_partners_status ON partners(status);
CREATE INDEX idx_partners_tier ON partners(tier);
CREATE INDEX idx_partners_ec_address ON partners(ec_address);
CREATE INDEX idx_partners_created_at ON partners(created_at);

-- ============================================================================
-- PARTNER API KEYS TABLE
-- Support multiple API keys per partner (rotation, staging vs prod)
-- ============================================================================
CREATE TABLE IF NOT EXISTS partner_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    api_secret_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255), -- "Production Key", "Test Key", "Mobile App Key"
    scopes TEXT[], -- ['wallets:read', 'wallets:write', 'transactions:send']
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    ip_whitelist TEXT[], -- Optional IP restriction
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for partner_api_keys
CREATE INDEX idx_partner_api_keys_partner_id ON partner_api_keys(partner_id);
CREATE INDEX idx_partner_api_keys_api_key ON partner_api_keys(api_key);
CREATE INDEX idx_partner_api_keys_revoked ON partner_api_keys(revoked_at) WHERE revoked_at IS NULL;
CREATE INDEX idx_partner_api_keys_expires ON partner_api_keys(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- AUDIT LOG TABLE
-- Comprehensive audit trail for compliance
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log_b2b (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    user_id VARCHAR(255), -- ec_address or internal user identifier
    action VARCHAR(100) NOT NULL, -- wallet.create, tx.send, signature.approve
    resource_type VARCHAR(50), -- wallet, transaction, signature, partner
    resource_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    request_id VARCHAR(64),
    changes JSONB, -- {"before": {...}, "after": {...}}
    result VARCHAR(20) DEFAULT 'success', -- success, failure
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for audit_log_b2b
CREATE INDEX idx_audit_log_b2b_partner_id ON audit_log_b2b(partner_id);
CREATE INDEX idx_audit_log_b2b_user_id ON audit_log_b2b(user_id);
CREATE INDEX idx_audit_log_b2b_action ON audit_log_b2b(action);
CREATE INDEX idx_audit_log_b2b_resource ON audit_log_b2b(resource_type, resource_id);
CREATE INDEX idx_audit_log_b2b_timestamp ON audit_log_b2b(timestamp DESC);
CREATE INDEX idx_audit_log_b2b_result ON audit_log_b2b(result);

-- ============================================================================
-- RATE LIMIT TRACKING TABLE
-- Track API usage per partner per time window
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(partner_id, endpoint, window_start)
);

-- Indexes for rate_limit_tracking
CREATE INDEX idx_rate_limit_tracking_partner ON rate_limit_tracking(partner_id);
CREATE INDEX idx_rate_limit_tracking_window ON rate_limit_tracking(window_start);

-- ============================================================================
-- WEBHOOK EVENTS TABLE
-- Queue and track webhook deliveries to partners
-- ============================================================================
CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- wallet.created, tx.confirmed, signature.needed
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed, cancelled
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 10,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    response_code INTEGER,
    response_body TEXT,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for webhook_events
CREATE INDEX idx_webhook_events_partner_id ON webhook_events(partner_id);
CREATE INDEX idx_webhook_events_status ON webhook_events(status);
CREATE INDEX idx_webhook_events_next_retry ON webhook_events(next_retry_at) WHERE status = 'pending';
CREATE INDEX idx_webhook_events_created_at ON webhook_events(created_at DESC);

-- ============================================================================
-- TRANSACTION ANALYTICS TABLE
-- Aggregated transaction data for reporting
-- ============================================================================
CREATE TABLE IF NOT EXISTS transaction_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID REFERENCES partners(id) ON DELETE SET NULL,
    wallet_name VARCHAR(255),
    network_id INTEGER,
    token VARCHAR(50),
    tx_type VARCHAR(20), -- send, receive
    amount_decimal DECIMAL(36, 18),
    amount_usd DECIMAL(18, 2), -- Converted to USD at time of transaction
    fee_decimal DECIMAL(36, 18),
    fee_usd DECIMAL(18, 2),
    status VARCHAR(50),
    tx_hash VARCHAR(255),
    tx_unid VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Indexes for transaction_analytics
CREATE INDEX idx_transaction_analytics_partner ON transaction_analytics(partner_id);
CREATE INDEX idx_transaction_analytics_wallet ON transaction_analytics(wallet_name);
CREATE INDEX idx_transaction_analytics_network ON transaction_analytics(network_id);
CREATE INDEX idx_transaction_analytics_token ON transaction_analytics(token);
CREATE INDEX idx_transaction_analytics_timestamp ON transaction_analytics(timestamp DESC);
CREATE INDEX idx_transaction_analytics_status ON transaction_analytics(status);

-- ============================================================================
-- ADDRESS BOOK (PER PARTNER)
-- Saved addresses with labels and categories
-- ============================================================================
CREATE TABLE IF NOT EXISTS address_book_b2b (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    network_id INTEGER NOT NULL,
    label VARCHAR(100),
    notes TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(partner_id, address, network_id)
);

-- Indexes for address_book_b2b
CREATE INDEX idx_address_book_b2b_partner ON address_book_b2b(partner_id);
CREATE INDEX idx_address_book_b2b_network ON address_book_b2b(network_id);
CREATE INDEX idx_address_book_b2b_favorite ON address_book_b2b(is_favorite) WHERE is_favorite = TRUE;

-- ============================================================================
-- SCHEDULED TRANSACTIONS TABLE
-- One-time and recurring transaction scheduling
-- ============================================================================
CREATE TABLE IF NOT EXISTS scheduled_transactions_b2b (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    wallet_name VARCHAR(255) NOT NULL,
    token VARCHAR(100) NOT NULL,
    to_address VARCHAR(255) NOT NULL,
    amount VARCHAR(50) NOT NULL,
    schedule_type VARCHAR(20) NOT NULL, -- once, daily, weekly, monthly, cron
    schedule_time TIMESTAMP WITH TIME ZONE NOT NULL,
    cron_expression VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending', -- pending, executing, completed, failed, cancelled
    last_executed_at TIMESTAMP WITH TIME ZONE,
    next_execution_at TIMESTAMP WITH TIME ZONE,
    execution_count INTEGER DEFAULT 0,
    max_executions INTEGER, -- null = infinite for recurring
    tx_unid VARCHAR(255), -- Last executed transaction UNID
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for scheduled_transactions_b2b
CREATE INDEX idx_scheduled_tx_b2b_partner ON scheduled_transactions_b2b(partner_id);
CREATE INDEX idx_scheduled_tx_b2b_status ON scheduled_transactions_b2b(status);
CREATE INDEX idx_scheduled_tx_b2b_next_exec ON scheduled_transactions_b2b(next_execution_at) WHERE status = 'pending';
CREATE INDEX idx_scheduled_tx_b2b_wallet ON scheduled_transactions_b2b(wallet_name);

-- ============================================================================
-- TRIGGER: Update updated_at on partners
-- ============================================================================
CREATE OR REPLACE FUNCTION update_partners_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER partners_updated_at
    BEFORE UPDATE ON partners
    FOR EACH ROW
    EXECUTE FUNCTION update_partners_updated_at();

-- ============================================================================
-- TRIGGER: Update updated_at on address_book_b2b
-- ============================================================================
CREATE TRIGGER address_book_b2b_updated_at
    BEFORE UPDATE ON address_book_b2b
    FOR EACH ROW
    EXECUTE FUNCTION update_partners_updated_at();

-- ============================================================================
-- TRIGGER: Update updated_at on scheduled_transactions_b2b
-- ============================================================================
CREATE TRIGGER scheduled_tx_b2b_updated_at
    BEFORE UPDATE ON scheduled_transactions_b2b
    FOR EACH ROW
    EXECUTE FUNCTION update_partners_updated_at();

-- ============================================================================
-- GRANTS (if needed for specific roles)
-- ============================================================================
-- Example: GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO orgon_api_user;

-- ============================================================================
-- COMMENTS (documentation)
-- ============================================================================
COMMENT ON TABLE partners IS 'B2B partners/tenants with API access';
COMMENT ON TABLE partner_api_keys IS 'Multiple API keys per partner for rotation and environments';
COMMENT ON TABLE audit_log_b2b IS 'Comprehensive audit trail for compliance and security';
COMMENT ON TABLE rate_limit_tracking IS 'Track API usage per partner for rate limiting';
COMMENT ON TABLE webhook_events IS 'Queue and delivery tracking for partner webhooks';
COMMENT ON TABLE transaction_analytics IS 'Aggregated transaction data for reporting and analytics';
COMMENT ON TABLE address_book_b2b IS 'Per-partner saved addresses with labels';
COMMENT ON TABLE scheduled_transactions_b2b IS 'Scheduled and recurring transaction management';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
