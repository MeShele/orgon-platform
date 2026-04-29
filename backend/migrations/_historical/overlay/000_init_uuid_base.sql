-- 000_init_uuid_base.sql
-- Initialize base tables with UUID primary keys (for multi-tenant compatibility)
-- This replaces the old schema/ files that used SERIAL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Helper function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 1. Users (base for multi-tenant)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'viewer',  -- admin/signer/viewer
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2. Wallets
CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    address TEXT UNIQUE NOT NULL,
    network TEXT NOT NULL DEFAULT 'tron',
    blockchain TEXT NOT NULL DEFAULT 'tron',
    balance_trx NUMERIC(20,6) DEFAULT 0,
    balance_usdt NUMERIC(20,6) DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wallets_address ON wallets(address);
CREATE INDEX IF NOT EXISTS idx_wallets_network ON wallets(network);
CREATE INDEX IF NOT EXISTS idx_wallets_status ON wallets(status);

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 3. Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    type TEXT NOT NULL,  -- send/receive/internal
    amount NUMERIC(20,6) NOT NULL,
    token TEXT DEFAULT 'TRX',
    to_address TEXT,
    from_address TEXT,
    status TEXT DEFAULT 'pending',
    tx_hash TEXT UNIQUE,
    fee NUMERIC(20,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_wallet ON transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_tx_hash ON transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at DESC);

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Signatures (multi-sig support)
CREATE TABLE IF NOT EXISTS signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id) ON DELETE CASCADE,
    signer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status TEXT DEFAULT 'pending',  -- pending/approved/rejected
    signature_data TEXT,
    signed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signatures_transaction ON signatures(transaction_id);
CREATE INDEX IF NOT EXISTS idx_signatures_signer ON signatures(signer_id);
CREATE INDEX IF NOT EXISTS idx_signatures_status ON signatures(status);

-- 5. Contacts (address book)
CREATE TABLE IF NOT EXISTS contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    network TEXT NOT NULL DEFAULT 'tron',
    category TEXT,
    notes TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contacts_address ON contacts(address);
CREATE INDEX IF NOT EXISTS idx_contacts_network ON contacts(network);
CREATE INDEX IF NOT EXISTS idx_contacts_category ON contacts(category);
CREATE INDEX IF NOT EXISTS idx_contacts_favorite ON contacts(is_favorite);

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 6. Scheduled Transactions
CREATE TABLE IF NOT EXISTS scheduled_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id) ON DELETE CASCADE,
    to_address TEXT NOT NULL,
    amount NUMERIC(20,6) NOT NULL,
    token TEXT DEFAULT 'TRX',
    schedule_type TEXT NOT NULL,  -- once/daily/weekly/monthly
    schedule_time TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/executed/cancelled/failed
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_wallet ON scheduled_transactions(wallet_id);
CREATE INDEX IF NOT EXISTS idx_scheduled_status ON scheduled_transactions(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_time ON scheduled_transactions(schedule_time);

CREATE TRIGGER update_scheduled_transactions_updated_at BEFORE UPDATE ON scheduled_transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id UUID,
    description TEXT,
    ip_address TEXT,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);

-- 8. User Sessions (JWT refresh tokens)
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(refresh_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- 9. Sync State (blockchain sync tracking)
CREATE TABLE IF NOT EXISTS sync_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    network TEXT UNIQUE NOT NULL,
    last_block BIGINT DEFAULT 0,
    last_sync_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'syncing'
);

CREATE INDEX IF NOT EXISTS idx_sync_state_network ON sync_state(network);

-- Comments
COMMENT ON TABLE users IS 'Multi-user support with RBAC';
COMMENT ON TABLE wallets IS 'Cryptocurrency wallets (Tron/BNB/ETH)';
COMMENT ON TABLE transactions IS 'Transaction history (send/receive)';
COMMENT ON TABLE signatures IS 'Multi-signature approvals';
COMMENT ON TABLE contacts IS 'Address book for frequent recipients';
COMMENT ON TABLE scheduled_transactions IS 'Recurring/scheduled payments';
COMMENT ON TABLE audit_logs IS 'Security audit trail';
COMMENT ON TABLE user_sessions IS 'JWT refresh token storage';
COMMENT ON TABLE sync_state IS 'Blockchain sync tracking';

-- Initial data
INSERT INTO sync_state (network, last_block, status) VALUES
    ('tron', 0, 'syncing'),
    ('bsc', 0, 'syncing'),
    ('ethereum', 0, 'syncing')
ON CONFLICT (network) DO NOTHING;
