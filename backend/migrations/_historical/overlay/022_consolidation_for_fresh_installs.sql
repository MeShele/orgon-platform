-- Migration 022: consolidation — make a fresh prod / dev DB roll up cleanly
-- Date: 2026-04-29
-- Purpose: While verifying the live Safina integration we patched several
--          things on the local DB by hand because earlier migrations
--          rolled back or were never applied. Without those bits a fresh
--          install fails in subtle ways:
--
--            • set_tenant_context / clear_tenant_context functions —
--              migration 005 rolled back due to its own SQL bugs, the
--              functions never got created. RLSMiddleware calls them on
--              every request and silently fails.
--            • partner_webhooks table — migration 009_webhooks.sql
--              referenced partners(partner_id) but the actual column is
--              partners(id). The CREATE TABLE failed and the table never
--              existed. Service layer 500's on `/api/v1/partner/webhooks`.
--            • balance_history table — runtime code expects it, no
--              migration creates it.
--
--          This migration installs all of them. Idempotent — every
--          object is created with IF NOT EXISTS / OR REPLACE so re-running
--          is a no-op.

BEGIN;

-- ============================================================
-- 1. RLS helper functions (replace whatever 005 left or didn't leave)
-- ============================================================
CREATE OR REPLACE FUNCTION set_tenant_context(org_id UUID, is_admin BOOLEAN DEFAULT false)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_organization_id', org_id::text, false);
    PERFORM set_config('app.is_super_admin', is_admin::text, false);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_tenant_context()
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_organization_id', '', false);
    PERFORM set_config('app.is_super_admin', 'false', false);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION set_tenant_context(UUID, BOOLEAN) IS
    'Set Postgres session vars consumed by RLS policies. Called by RLSMiddleware on each request.';
COMMENT ON FUNCTION clear_tenant_context() IS
    'Clear session vars at request end so a recycled connection does not leak tenancy.';

-- ============================================================
-- 2. partner_webhooks (was broken in 009 — wrong FK column)
-- ============================================================
CREATE TABLE IF NOT EXISTS partner_webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    url VARCHAR(500) NOT NULL,
    event_types TEXT[] NOT NULL DEFAULT '{}',
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    secret VARCHAR(255),
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_partner_webhooks_partner_id ON partner_webhooks(partner_id);
CREATE INDEX IF NOT EXISTS idx_partner_webhooks_active ON partner_webhooks(is_active);

-- ============================================================
-- 3. balance_history — periodic balance snapshots for the dashboard chart
-- ============================================================
CREATE TABLE IF NOT EXISTS balance_history (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) NOT NULL,
    total_value NUMERIC(36, 18) NOT NULL DEFAULT 0,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_balance_history_recorded_at
    ON balance_history(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_balance_history_org
    ON balance_history(organization_id, recorded_at DESC);

COMMIT;
