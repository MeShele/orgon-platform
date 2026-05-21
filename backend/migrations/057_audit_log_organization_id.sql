-- 057_audit_log_organization_id.sql
--
-- TD-1 Phase A — start tagging new `audit_log` rows with the
-- organization that produced them.
--
-- Why now: `audit_log` is currently a tenant-undifferentiated heap.
-- RBAC keeps merchants out of `/api/audit/*` today, but the moment we
-- surface audit endpoints on `/v1/*` (planned for the institutional
-- pilot), the heap would leak cross-merchant actions. See
-- `docs/TECH_DEBT.md#TD-1`.
--
-- Phase A (this file): purely additive. New column nullable. Existing
-- rows stay NULL — they cannot be backfilled here because the table
-- carries an append-only trigger (`orgon_immutable_audit_log`) that
-- RAISE EXCEPTION on UPDATE. Backfill needs its own change window
-- and is tracked as TD-1 Phase B.
--
-- Safe to re-run. No data rewrite — Postgres treats `ADD COLUMN
-- ... uuid NULL` as a metadata-only operation; instant on tables of
-- any size.

ALTER TABLE public.audit_log
    ADD COLUMN IF NOT EXISTS organization_id uuid;

-- Partial index — historical rows are NULL by construction; indexing
-- only the populated rows keeps the index dense and small without
-- touching the existing query plans (the read side hasn't been
-- updated yet; that lands with Phase B).
CREATE INDEX IF NOT EXISTS idx_audit_log_organization_id
    ON public.audit_log (organization_id)
    WHERE organization_id IS NOT NULL;

COMMENT ON COLUMN public.audit_log.organization_id IS
    'Tenant scoping for audit rows. Populated for AML alerts, monitoring-rule mutations, and self-service merchant onboarding from 2026-05-21 onward. Pre-cutover rows and UI/JWT-driven middleware writes are NULL until TD-1 Phase B backfill lifts the append-only trigger and joins via users → organizations.';

INSERT INTO public.schema_migrations (version, description)
VALUES ('057_audit_log_organization_id',
        'TD-1 Phase A — additive organization_id column on audit_log. Phase B backfill pending.')
ON CONFLICT (version) DO NOTHING;
