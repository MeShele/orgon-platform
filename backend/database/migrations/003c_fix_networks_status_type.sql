-- Fix: networks_cache.status should be INTEGER, not VARCHAR
ALTER TABLE networks_cache ALTER COLUMN status TYPE INTEGER USING status::integer;

-- Add missing columns if needed
ALTER TABLE networks_cache ADD COLUMN IF NOT EXISTS network_name VARCHAR(255);
ALTER TABLE networks_cache ADD COLUMN IF NOT EXISTS link TEXT;
ALTER TABLE networks_cache ADD COLUMN IF NOT EXISTS address_explorer TEXT;
ALTER TABLE networks_cache ADD COLUMN IF NOT EXISTS tx_explorer TEXT;
ALTER TABLE networks_cache ADD COLUMN IF NOT EXISTS block_explorer TEXT;
ALTER TABLE networks_cache ADD COLUMN IF NOT EXISTS info TEXT;
