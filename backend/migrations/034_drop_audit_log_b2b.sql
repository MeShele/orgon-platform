-- 034_drop_audit_log_b2b.sql
--
-- Drop the parallel B2B audit table. AuditService was rewritten to talk
-- to the single `audit_log` table; once the new container is live in
-- prod, this drop is safe.
--
-- ORDER OF OPERATIONS (must follow):
--   1. Deploy commit with the rewritten backend/services/audit_service.py
--      and the migration 033 (drops the partner/fiat/billing tables).
--   2. Verify /api/audit/logs returns 200 (the new code reads audit_log,
--      not audit_log_b2b).
--   3. Apply this migration (or wait for entrypoint.sh to pick it up on
--      next restart — overlay loader runs all 0*.sql in order).
--
-- If you apply this before the new container is up, the running backend
-- will 500 on /api/audit/logs because it still tries to SELECT FROM
-- audit_log_b2b.

DROP TABLE IF EXISTS public.audit_log_b2b CASCADE;
