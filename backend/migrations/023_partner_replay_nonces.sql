-- Migration 023: replay-protection nonces for B2B Partner API
-- Date: 2026-04-29
-- Purpose: pair every partner request with a one-shot nonce + bounded
--          timestamp so a captured request can't be replayed. Middleware
--          rejects:
--             • requests outside ±5 min of server time
--             • requests whose (partner_id, nonce) was seen recently
--
--          Rows live for `replay_window_minutes` (default 60) and are
--          pruned by an APScheduler job. The partial UNIQUE index is the
--          source of truth — even if the in-memory check is bypassed
--          somehow, the DB rejects the second insert.
--
-- Idempotent.

BEGIN;

CREATE TABLE IF NOT EXISTS partner_request_nonces (
    partner_id UUID         NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    nonce      VARCHAR(128) NOT NULL,
    seen_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (partner_id, nonce)
);

-- Used by the periodic prune job.
CREATE INDEX IF NOT EXISTS idx_partner_request_nonces_seen_at
    ON partner_request_nonces(seen_at);

COMMENT ON TABLE partner_request_nonces IS
    'B2B replay-protection — one row per (partner_id, nonce). Pruned hourly.';

COMMIT;
