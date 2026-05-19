-- 049_webhook_retention.sql
--
-- Retention horizon for webhook_deliveries.
--
-- Rationale: queue table grows linearly with traffic; without
-- horizon-pruning even the cheap query plan eventually pulls in
-- millions of "delivered six months ago" rows on every retry tick.
--
-- A nightly job (scheduler.py) DELETEs rows older than 90 days
-- THAT ARE TERMINAL — delivered_at IS NOT NULL, or attempts >= 6
-- (gave-up sentinel). In-flight rows (pending + still under attempt
-- ceiling) are NEVER deleted by the retention job — under the worst
-- legitimate retry schedule (v2) the row stays in-flight for ~24h,
-- well inside the 90-day horizon.
--
-- This index makes the retention sweep a fast bitmap-scan on
-- (created_at, delivered_at, attempts) and stays small because of
-- the partial filter.
--
-- Idempotent.

CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retention_sweep
    ON public.webhook_deliveries (created_at)
    WHERE delivered_at IS NOT NULL OR attempts >= 6;

COMMENT ON INDEX public.idx_webhook_deliveries_retention_sweep IS
    'Partial index: terminal rows only. Drives the 90-day retention sweep in scheduler.';

INSERT INTO public.schema_migrations (version, description)
VALUES ('049_webhook_retention',
        'Partial index for the 90-day webhook_deliveries retention sweep.')
ON CONFLICT (version) DO NOTHING;
