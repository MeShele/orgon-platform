CREATE TABLE IF NOT EXISTS scheduled_transactions (
    id SERIAL PRIMARY KEY,
    
    -- Transaction details
    token TEXT NOT NULL,
    to_address TEXT NOT NULL,
    value TEXT NOT NULL,
    info TEXT,
    json_info TEXT,
    
    -- Scheduling
    scheduled_at TIMESTAMPTZ NOT NULL,
    recurrence_rule TEXT,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    tx_unid TEXT UNIQUE,
    error_message TEXT,
    
    -- Metadata
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    next_run_at TIMESTAMPTZ
);

-- Index for scheduler queries
CREATE INDEX IF NOT EXISTS idx_scheduled_tx_status_time 
ON scheduled_transactions(status, scheduled_at);

-- Index for recurring jobs
CREATE INDEX IF NOT EXISTS idx_scheduled_tx_next_run 
ON scheduled_transactions(status, next_run_at);
