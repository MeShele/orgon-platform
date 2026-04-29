-- Migration: Add missing tables and constraints for PostgreSQL

-- sync_state table (was only in SQLite)
CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- networks cache table
CREATE TABLE IF NOT EXISTS networks (
    network_id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    short_name VARCHAR(50),
    tokens JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- tokens cache table
CREATE TABLE IF NOT EXISTS tokens (
    token VARCHAR(255) PRIMARY KEY,
    network_id INTEGER,
    name VARCHAR(255),
    short_name VARCHAR(50),
    decimals INTEGER DEFAULT 18,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add UNIQUE constraints needed for ON CONFLICT
ALTER TABLE wallets ADD CONSTRAINT wallets_name_unique UNIQUE (name);
ALTER TABLE transactions ADD CONSTRAINT transactions_unid_unique UNIQUE (tx_unid);

-- Add unique constraint for tx_signatures
ALTER TABLE tx_signatures ADD CONSTRAINT tx_signatures_tx_ec_unique UNIQUE (tx_unid, signer_address);
