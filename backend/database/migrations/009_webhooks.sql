-- Migration 009: Webhooks & Events
-- Purpose: Real-time event notifications for B2B partners
-- Date: 2026-02-08

-- ============================================================================
-- WEBHOOK EVENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_events (
    id SERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,                      -- Idempotency key
    partner_id UUID NOT NULL REFERENCES partners(partner_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,                    -- wallet.created, tx.confirmed, etc.
    payload JSONB NOT NULL,                             -- Event data
    webhook_url TEXT NOT NULL,                          -- Delivery endpoint
    status VARCHAR(20) NOT NULL DEFAULT 'pending',      -- pending, delivered, failed, cancelled
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    next_retry_at TIMESTAMPTZ,
    last_error TEXT,
    signature VARCHAR(128),                             -- HMAC-SHA256 signature
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ
);

-- Indexes for webhook_events
CREATE INDEX IF NOT EXISTS idx_webhook_events_status_retry 
    ON webhook_events(status, next_retry_at) 
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_webhook_events_partner_created 
    ON webhook_events(partner_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_webhook_events_event_type 
    ON webhook_events(event_type);

CREATE INDEX IF NOT EXISTS idx_webhook_events_event_id 
    ON webhook_events(event_id);

-- Comments
COMMENT ON TABLE webhook_events IS 'Event queue for webhook delivery to partners';
COMMENT ON COLUMN webhook_events.event_id IS 'Unique event identifier for idempotency';
COMMENT ON COLUMN webhook_events.payload IS 'Event data (JSON)';
COMMENT ON COLUMN webhook_events.status IS 'pending | delivered | failed | cancelled';
COMMENT ON COLUMN webhook_events.attempts IS 'Number of delivery attempts';
COMMENT ON COLUMN webhook_events.next_retry_at IS 'Next retry timestamp (exponential backoff)';
COMMENT ON COLUMN webhook_events.signature IS 'HMAC-SHA256 signature for verification';

-- ============================================================================
-- PARTNER WEBHOOKS TABLE (Configuration)
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_webhooks (
    id SERIAL PRIMARY KEY,
    partner_id UUID NOT NULL REFERENCES partners(partner_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    event_types TEXT[] NOT NULL,                       -- ['wallet.*', 'transaction.confirmed']
    is_active BOOLEAN NOT NULL DEFAULT true,
    secret TEXT,                                        -- Optional custom secret (overrides API secret)
    description TEXT,                                   -- Partner-provided description
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_delivery_at TIMESTAMPTZ,
    success_count INT NOT NULL DEFAULT 0,
    failure_count INT NOT NULL DEFAULT 0,
    UNIQUE(partner_id, url)
);

-- Indexes for partner_webhooks
CREATE INDEX IF NOT EXISTS idx_partner_webhooks_partner 
    ON partner_webhooks(partner_id);

CREATE INDEX IF NOT EXISTS idx_partner_webhooks_active 
    ON partner_webhooks(is_active) 
    WHERE is_active = true;

-- Comments
COMMENT ON TABLE partner_webhooks IS 'Partner webhook endpoint configurations';
COMMENT ON COLUMN partner_webhooks.event_types IS 'Array of event type patterns (supports wildcards)';
COMMENT ON COLUMN partner_webhooks.secret IS 'Custom HMAC secret (optional, defaults to API secret)';
COMMENT ON COLUMN partner_webhooks.success_count IS 'Total successful deliveries';
COMMENT ON COLUMN partner_webhooks.failure_count IS 'Total failed deliveries';

-- ============================================================================
-- WEBHOOK DELIVERY STATS (Aggregated)
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhook_stats (
    id SERIAL PRIMARY KEY,
    partner_id UUID NOT NULL REFERENCES partners(partner_id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    delivered_count INT NOT NULL DEFAULT 0,
    failed_count INT NOT NULL DEFAULT 0,
    avg_delivery_ms INT,                                -- Average delivery time
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(partner_id, event_type, date)
);

-- Index for webhook_stats
CREATE INDEX IF NOT EXISTS idx_webhook_stats_partner_date 
    ON webhook_stats(partner_id, date DESC);

-- Comments
COMMENT ON TABLE webhook_stats IS 'Daily webhook delivery statistics per partner';
COMMENT ON COLUMN webhook_stats.avg_delivery_ms IS 'Average delivery time in milliseconds';

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function: Update partner_webhooks updated_at on modification
CREATE OR REPLACE FUNCTION update_partner_webhooks_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER partner_webhooks_update_timestamp
    BEFORE UPDATE ON partner_webhooks
    FOR EACH ROW
    EXECUTE FUNCTION update_partner_webhooks_timestamp();

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Add webhook configuration for test partner (if exists)
-- DO $$
-- BEGIN
--     IF EXISTS (SELECT 1 FROM partners WHERE name = 'Test Exchange Ltd') THEN
--         INSERT INTO partner_webhooks (partner_id, url, event_types, description)
--         SELECT 
--             partner_id, 
--             'http://localhost:9000/webhooks/orgon',
--             ARRAY['wallet.*', 'transaction.*', 'signature.*'],
--             'Test webhook receiver'
--         FROM partners 
--         WHERE name = 'Test Exchange Ltd'
--         ON CONFLICT (partner_id, url) DO NOTHING;
--     END IF;
-- END $$;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Verify tables created
SELECT 'Migration 009: Webhooks & Events - Complete' AS status,
       COUNT(*) FILTER (WHERE tablename = 'webhook_events') AS webhook_events_table,
       COUNT(*) FILTER (WHERE tablename = 'partner_webhooks') AS partner_webhooks_table,
       COUNT(*) FILTER (WHERE tablename = 'webhook_stats') AS webhook_stats_table
FROM pg_tables
WHERE schemaname = 'public' 
  AND tablename IN ('webhook_events', 'partner_webhooks', 'webhook_stats');
