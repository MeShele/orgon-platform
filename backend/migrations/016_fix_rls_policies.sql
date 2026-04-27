-- Migration 016: Fix and re-create RLS policies (supersedes broken 005)
-- Date: 2026-04-27
-- Purpose: Migration 005 contained two SQL bugs that prevented every policy
--          from being created:
--            (a) extra ")" + double "::uuid" cast on `wallets`
--            (b) unterminated string literal in
--                `current_setting('app.is_super_admin, true)::boolean ...`
--          As a result, RLS was never actually enforced. Tenant isolation
--          relied entirely on the service layer (`set_tenant_context`).
--
--          This migration drops any partial state from 005 and re-creates
--          all policies with the correct shape, plus ENABLE + FORCE on every
--          tenant-aware table.
--
-- Idempotent: safe to run multiple times.
-- Reversible: see the rollback block at the bottom (commented out).

BEGIN;

-- ============================================================
-- 1. Drop anything 005 may have left in a half-applied state
-- ============================================================
DROP POLICY IF EXISTS wallets_isolation_policy ON wallets;
DROP POLICY IF EXISTS transactions_isolation_policy ON transactions;
DROP POLICY IF EXISTS signatures_isolation_policy ON signatures;
DROP POLICY IF EXISTS contacts_isolation_policy ON contacts;
DROP POLICY IF EXISTS scheduled_transactions_isolation_policy ON scheduled_transactions;
DROP POLICY IF EXISTS audit_logs_isolation_policy ON audit_logs;

-- ============================================================
-- 2. ENABLE + FORCE on every tenant-scoped table
--    (FORCE is what makes RLS apply to the table owner too — without it,
--     migrations and the asyncpg connection user would bypass everything.)
-- ============================================================
ALTER TABLE wallets                ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallets                FORCE  ROW LEVEL SECURITY;
ALTER TABLE transactions           ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions           FORCE  ROW LEVEL SECURITY;
ALTER TABLE signatures             ENABLE ROW LEVEL SECURITY;
ALTER TABLE signatures             FORCE  ROW LEVEL SECURITY;
ALTER TABLE contacts               ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts               FORCE  ROW LEVEL SECURITY;
ALTER TABLE scheduled_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_transactions FORCE  ROW LEVEL SECURITY;
ALTER TABLE audit_logs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs             FORCE  ROW LEVEL SECURITY;

-- ============================================================
-- 3. Predicate helper — the same expression repeats six times so we
--    factor it into a STABLE SQL function. STABLE so the planner can
--    cache the result inside a single statement.
-- ============================================================
CREATE OR REPLACE FUNCTION orgon_current_org_or_super()
RETURNS TABLE (org_id UUID, is_super BOOLEAN)
LANGUAGE sql STABLE AS $$
    SELECT
        NULLIF(current_setting('app.current_organization_id', true), '')::uuid,
        COALESCE(current_setting('app.is_super_admin', true)::boolean, false)
$$;

COMMENT ON FUNCTION orgon_current_org_or_super() IS
    'Returns (current_org_id, is_super_admin) from session settings — used by RLS policies.';

-- ============================================================
-- 4. Re-create policies — same shape, just correct quoting/parens
-- ============================================================
CREATE POLICY wallets_isolation_policy ON wallets
    FOR ALL
    USING (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    )
    WITH CHECK (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    );

CREATE POLICY transactions_isolation_policy ON transactions
    FOR ALL
    USING (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    )
    WITH CHECK (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    );

CREATE POLICY signatures_isolation_policy ON signatures
    FOR ALL
    USING (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    )
    WITH CHECK (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    );

CREATE POLICY contacts_isolation_policy ON contacts
    FOR ALL
    USING (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    )
    WITH CHECK (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    );

CREATE POLICY scheduled_transactions_isolation_policy ON scheduled_transactions
    FOR ALL
    USING (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    )
    WITH CHECK (
        organization_id = (SELECT org_id  FROM orgon_current_org_or_super())
        OR              (SELECT is_super FROM orgon_current_org_or_super())
    );

-- audit_logs is read-only from app's perspective; super-admin sees every org.
-- NULL organization_id means "system-wide" (login attempts, cron jobs) and is
-- visible only to super-admin.
CREATE POLICY audit_logs_isolation_policy ON audit_logs
    FOR SELECT
    USING (
        (SELECT is_super FROM orgon_current_org_or_super())
        OR organization_id = (SELECT org_id FROM orgon_current_org_or_super())
    );

-- ============================================================
-- 5. Sanity check — confirms each policy actually exists
-- ============================================================
DO $$
DECLARE
    expected text[] := ARRAY[
        'wallets_isolation_policy',
        'transactions_isolation_policy',
        'signatures_isolation_policy',
        'contacts_isolation_policy',
        'scheduled_transactions_isolation_policy',
        'audit_logs_isolation_policy'
    ];
    p text;
    cnt int;
BEGIN
    FOREACH p IN ARRAY expected LOOP
        SELECT count(*) INTO cnt FROM pg_policies WHERE policyname = p;
        IF cnt = 0 THEN
            RAISE EXCEPTION 'RLS policy % was not created', p;
        END IF;
    END LOOP;
    RAISE NOTICE 'Migration 016: all 6 RLS policies installed.';
END $$;

COMMIT;

-- ============================================================
-- Rollback (manual): uncomment if you need to disable RLS again.
-- ============================================================
-- BEGIN;
--   DROP POLICY IF EXISTS wallets_isolation_policy ON wallets;
--   DROP POLICY IF EXISTS transactions_isolation_policy ON transactions;
--   DROP POLICY IF EXISTS signatures_isolation_policy ON signatures;
--   DROP POLICY IF EXISTS contacts_isolation_policy ON contacts;
--   DROP POLICY IF EXISTS scheduled_transactions_isolation_policy ON scheduled_transactions;
--   DROP POLICY IF EXISTS audit_logs_isolation_policy ON audit_logs;
--   ALTER TABLE wallets                NO FORCE ROW LEVEL SECURITY;
--   ALTER TABLE wallets                DISABLE  ROW LEVEL SECURITY;
--   ALTER TABLE transactions           NO FORCE ROW LEVEL SECURITY;
--   ALTER TABLE transactions           DISABLE  ROW LEVEL SECURITY;
--   ALTER TABLE signatures             NO FORCE ROW LEVEL SECURITY;
--   ALTER TABLE signatures             DISABLE  ROW LEVEL SECURITY;
--   ALTER TABLE contacts               NO FORCE ROW LEVEL SECURITY;
--   ALTER TABLE contacts               DISABLE  ROW LEVEL SECURITY;
--   ALTER TABLE scheduled_transactions NO FORCE ROW LEVEL SECURITY;
--   ALTER TABLE scheduled_transactions DISABLE  ROW LEVEL SECURITY;
--   ALTER TABLE audit_logs             NO FORCE ROW LEVEL SECURITY;
--   ALTER TABLE audit_logs             DISABLE  ROW LEVEL SECURITY;
-- COMMIT;
