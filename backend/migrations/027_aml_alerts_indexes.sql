-- Migration 027 — AML alerts triage indexes (Wave 21, Story 2.6)
-- Idempotent. No data changes — only index creation for triage UI.

-- Listing index — default sort is "newest first within an org".
-- Composite (org_id, created_at DESC, id DESC) supports both filtered
-- listing and keyset pagination (cursor = (created_at, id)).
CREATE INDEX IF NOT EXISTS idx_aml_alerts_org_created
    ON public.aml_alerts (organization_id, created_at DESC, id DESC);

-- Filter-by-status index — the hot path is "open alerts for this org",
-- which is what the AML tab loads on every page-open.
CREATE INDEX IF NOT EXISTS idx_aml_alerts_org_status_created
    ON public.aml_alerts (organization_id, status, created_at DESC);

-- Drill-down JOIN — "show every alert against this transaction".
-- Partial index keeps it small (most rows have NULL transaction_id).
CREATE INDEX IF NOT EXISTS idx_aml_alerts_transaction_id
    ON public.aml_alerts (transaction_id)
    WHERE transaction_id IS NOT NULL;

-- Audit trail lookup — "what did anyone do with alert X". Audit-log is
-- append-mostly; partial index keeps non-AML rows out.
CREATE INDEX IF NOT EXISTS idx_audit_log_aml_alert
    ON public.audit_log (resource_id, created_at DESC)
    WHERE resource_type = 'aml_alert';
