-- 050_audit_query_indexes.sql
--
-- Indexes that make `/api/audit/events` keyset queries fast.
--
-- The canonical schema already ships single-column indexes on
-- (action), (user_id), (created_at DESC), and (resource_type,
-- resource_id). Those work, but compose poorly: a request like
-- "all `transaction.signed` events on the last 7 days, paginated"
-- has to either pick `idx_audit_log_action` and post-filter time
-- in memory, or pick `idx_audit_log_created_at` and post-filter
-- on action. Neither is ideal once the table crosses a million
-- rows.
--
-- These two composite indexes add cheap covering scans for the
-- two most common audit drill-downs:
--
--   1. "All events of a given action over time"
--      → idx_audit_log_action_created
--   2. "All events by a specific actor over time"
--      → idx_audit_log_user_created
--
-- Both end with `(id DESC)` so the keyset cursor
-- `(created_at DESC, id DESC)` has a deterministic tie-break when
-- two rows share a millisecond.
--
-- Idempotent.

CREATE INDEX IF NOT EXISTS idx_audit_log_action_created
    ON public.audit_log (action, created_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_created
    ON public.audit_log (user_id, created_at DESC, id DESC)
    WHERE user_id IS NOT NULL;

COMMENT ON INDEX public.idx_audit_log_action_created IS
    'Covers `WHERE action = X ORDER BY created_at DESC, id DESC` with keyset cursors.';
COMMENT ON INDEX public.idx_audit_log_user_created IS
    'Covers actor drill-down: `WHERE user_id = X ORDER BY created_at DESC, id DESC`. Partial — system events (NULL user_id) skip.';

INSERT INTO public.schema_migrations (version, description)
VALUES ('050_audit_query_indexes',
        'Composite (action, created_at, id) and (user_id, created_at, id) for keyset audit queries.')
ON CONFLICT (version) DO NOTHING;
