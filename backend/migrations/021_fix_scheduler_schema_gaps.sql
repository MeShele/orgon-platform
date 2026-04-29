-- Migration 021: schema gaps tripped up by APScheduler background jobs
-- Date: 2026-04-29
-- Purpose: Background jobs that run on a 30-60s timer were filling logs
--          with the same four errors:
--            • "column 'event_id' does not exist" — webhook insert
--            • "column 'webhook_url' does not exist" — webhook insert
--            • "relation 'token_balances' does not exist" — balance sync
--            • "relation 'pending_signatures_checked' does not exist"
--                                                  — new-pending check
--            • "column 'synced_at' of relation 'transactions' does not exist"
--                                                  — pending tx check
--
--          All of these are missing schema bits — the runtime code expects
--          them but no migration ever created them. This migration adds
--          them all idempotently.
--
-- Idempotent. Safe to re-run.

BEGIN;

-- ============================================================
-- 1. webhook_events — add event_id + webhook_url
-- ============================================================
ALTER TABLE webhook_events
    ADD COLUMN IF NOT EXISTS event_id   UUID,
    ADD COLUMN IF NOT EXISTS webhook_url TEXT;

CREATE INDEX IF NOT EXISTS idx_webhook_events_event_id ON webhook_events(event_id);

-- ============================================================
-- 2. transactions — add synced_at (the scheduler reads it to skip
--                   already-synced rows)
-- ============================================================
ALTER TABLE transactions
    ADD COLUMN IF NOT EXISTS synced_at TIMESTAMPTZ;

-- ============================================================
-- 3. token_balances — flat per-token balance cache populated by
--                     SyncService.sync_balances every 5 minutes
-- ============================================================
CREATE TABLE IF NOT EXISTS token_balances (
    id          SERIAL PRIMARY KEY,
    token_id    VARCHAR(64),
    wallet_id   VARCHAR(255),
    network     VARCHAR(64),
    token       VARCHAR(64) NOT NULL,
    value       VARCHAR(64),
    decimals    VARCHAR(8),
    value_hex   VARCHAR(128),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_token_balances_wallet ON token_balances(wallet_id);
CREATE INDEX IF NOT EXISTS idx_token_balances_token ON token_balances(token);

-- ============================================================
-- 4. pending_signatures_checked — keeps SignatureService from
--                                  re-emitting "new pending" events
-- ============================================================
CREATE TABLE IF NOT EXISTS pending_signatures_checked (
    tx_unid     VARCHAR(255) PRIMARY KEY,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pending_sig_checked_at
    ON pending_signatures_checked(checked_at DESC);

COMMIT;
