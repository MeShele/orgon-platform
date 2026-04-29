-- Fix: recreate networks_cache with correct types
DROP TABLE IF EXISTS networks_cache;
CREATE TABLE networks_cache (
    network_id INTEGER PRIMARY KEY,
    network_name VARCHAR(255),
    short_name VARCHAR(100),
    link TEXT,
    address_explorer TEXT,
    tx_explorer TEXT,
    block_explorer TEXT,
    info TEXT,
    status INTEGER DEFAULT 1,
    tokens JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_networks_cache_status ON networks_cache(status);
