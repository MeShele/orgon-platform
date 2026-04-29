-- Migration: Create wallets and transactions tables for PostgreSQL
-- These tables match the service layer expectations

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS wallets (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER,
    name VARCHAR(255) NOT NULL,
    network INTEGER NOT NULL,
    wallet_type INTEGER,
    info TEXT,
    addr VARCHAR(255) DEFAULT '',
    addr_info TEXT,
    my_unid VARCHAR(255),
    token_short_names TEXT,
    label TEXT,
    is_favorite BOOLEAN DEFAULT false,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ,
    created_by INTEGER REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_wallets_network ON wallets(network);
CREATE INDEX IF NOT EXISTS idx_wallets_name ON wallets(name);
CREATE INDEX IF NOT EXISTS idx_wallets_org ON wallets(organization_id);

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    wallet_name VARCHAR(255),
    tx_hash VARCHAR(255),
    tx_unid VARCHAR(255),
    from_address VARCHAR(255),
    to_address VARCHAR(255),
    amount_decimal DECIMAL(36, 18),
    network INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    fee DECIMAL(36, 18),
    info TEXT,
    json_info JSONB,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_transactions_hash ON transactions(tx_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_wallet ON transactions(wallet_name);
CREATE INDEX IF NOT EXISTS idx_transactions_org ON transactions(organization_id);

CREATE TABLE IF NOT EXISTS tx_signatures (
    id SERIAL PRIMARY KEY,
    tx_unid VARCHAR(255) NOT NULL,
    signer_address VARCHAR(255),
    signature TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    signer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tx_signatures_tx ON tx_signatures(tx_unid);
CREATE INDEX IF NOT EXISTS idx_tx_signatures_status ON tx_signatures(status);
