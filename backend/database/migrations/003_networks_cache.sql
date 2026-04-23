-- Migration: Create networks_cache table

CREATE TABLE IF NOT EXISTS networks_cache (
    network_id INTEGER PRIMARY KEY,
    name VARCHAR(255),
    short_name VARCHAR(100),
    status VARCHAR(50) DEFAULT 'active',
    tokens JSONB DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_networks_cache_status ON networks_cache(status);
