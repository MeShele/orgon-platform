-- ORGON PostgreSQL Migration Schema
-- Converted from SQLite
-- Date: 2026-02-06

-- Drop existing tables if any
DROP TABLE IF EXISTS signature_history CASCADE;
DROP TABLE IF EXISTS tx_signatures CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS token_balances CASCADE;
DROP TABLE IF EXISTS balance_history CASCADE;
DROP TABLE IF EXISTS networks_cache CASCADE;
DROP TABLE IF EXISTS tokens_info_cache CASCADE;
DROP TABLE IF EXISTS pending_signatures_checked CASCADE;
DROP TABLE IF EXISTS sync_state CASCADE;
DROP TABLE IF EXISTS wallets CASCADE;

-- Wallets
CREATE TABLE wallets (
    id SERIAL PRIMARY KEY,
    wallet_id INTEGER,
    name TEXT UNIQUE NOT NULL,
    network INTEGER NOT NULL,
    wallet_type INTEGER,
    info TEXT,
    addr TEXT DEFAULT '',
    addr_info TEXT,
    my_unid TEXT,
    token_short_names TEXT,
    label TEXT,
    is_favorite INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMPTZ
);

CREATE INDEX idx_wallets_network ON wallets(network);
CREATE INDEX idx_wallets_name ON wallets(name);

-- Transactions
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    safina_id INTEGER,
    tx_hash TEXT,
    token TEXT NOT NULL,
    token_name TEXT,
    to_addr TEXT NOT NULL,
    value TEXT NOT NULL,
    value_hex TEXT,
    unid TEXT UNIQUE NOT NULL,
    init_ts INTEGER,
    min_sign INTEGER,
    status TEXT DEFAULT 'pending',
    info TEXT,
    wallet_name TEXT,
    network INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMPTZ
);

CREATE INDEX idx_transactions_unid ON transactions(unid);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_wallet ON transactions(wallet_name);

-- Transaction Signatures
CREATE TABLE tx_signatures (
    id SERIAL PRIMARY KEY,
    tx_unid TEXT NOT NULL REFERENCES transactions(unid) ON DELETE CASCADE,
    ec_address TEXT NOT NULL,
    sig_type TEXT NOT NULL,
    ec_sign TEXT,
    signed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tx_signatures_tx ON tx_signatures(tx_unid);

-- Sync State
CREATE TABLE sync_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Token Balances
CREATE TABLE token_balances (
    id SERIAL PRIMARY KEY,
    token_id TEXT,
    wallet_id TEXT,
    wallet_name TEXT,
    network TEXT,
    token TEXT NOT NULL,
    value TEXT NOT NULL,
    decimals TEXT,
    value_hex TEXT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_balances_wallet ON token_balances(wallet_name);

-- Networks Cache
CREATE TABLE networks_cache (
    network_id INTEGER PRIMARY KEY,
    network_name TEXT NOT NULL,
    link TEXT,
    address_explorer TEXT,
    tx_explorer TEXT,
    block_explorer TEXT,
    info TEXT,
    status INTEGER,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tokens Info Cache
CREATE TABLE tokens_info_cache (
    token TEXT PRIMARY KEY,
    commission TEXT,
    commission_min TEXT,
    commission_max TEXT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Balance History
CREATE TABLE balance_history (
    id SERIAL PRIMARY KEY,
    token TEXT NOT NULL,
    network TEXT,
    total_value TEXT NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_balance_history_date ON balance_history(recorded_at);

-- Signature History
CREATE TABLE signature_history (
    id SERIAL PRIMARY KEY,
    tx_unid TEXT NOT NULL,
    ec_address TEXT NOT NULL,
    action TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signature_history_tx ON signature_history(tx_unid);
CREATE INDEX idx_signature_history_date ON signature_history(created_at);

-- Pending Signatures Checked (tracking table)
CREATE TABLE pending_signatures_checked (
    tx_unid TEXT PRIMARY KEY,
    last_checked_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
