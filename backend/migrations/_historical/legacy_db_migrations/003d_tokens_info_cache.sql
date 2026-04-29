-- Create tokens_info_cache table
CREATE TABLE IF NOT EXISTS tokens_info_cache (
    token VARCHAR(255) PRIMARY KEY,
    commission TEXT,
    commission_min TEXT,
    commission_max TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
