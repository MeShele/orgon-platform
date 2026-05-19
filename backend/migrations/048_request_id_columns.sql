-- 048_request_id_columns.sql
--
-- Correlation IDs across the pipeline.
--
-- Every /v1/* request gets `request.state.request_id` from
-- RequestIdAndErrorMiddleware (random uuid hex, or echoed from the
-- caller's `X-Request-Id` header if they supplied one). We persist
-- that id at every state-changing fan-out point so an integrator
-- pasting one request-id into support gets us the full trail:
--
--   webhook delivery → which originating /v1/* call produced it
--   signature row    → which dashboard action triggered the sign-step
--
-- Nullable on purpose — pre-048 rows keep NULL, post-048 rows fill in.
-- Indexed lightly because the query pattern is "single point lookup"
-- (grep one id), not aggregation.
--
-- Idempotent.

ALTER TABLE public.webhook_deliveries
    ADD COLUMN IF NOT EXISTS originating_request_id text;

ALTER TABLE public.signature_history
    ADD COLUMN IF NOT EXISTS request_id text;

-- Single-id lookups; partial because the bulk of historical rows have
-- request_id IS NULL and there's no point indexing those.
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_originating_request_id
    ON public.webhook_deliveries (originating_request_id)
    WHERE originating_request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_signature_history_request_id
    ON public.signature_history (request_id)
    WHERE request_id IS NOT NULL;

COMMENT ON COLUMN public.webhook_deliveries.originating_request_id IS
    'X-Request-Id of the /v1/* call that caused this webhook to be enqueued. NULL for events not originated by an API call (cron-driven deposits, manual admin actions).';

COMMENT ON COLUMN public.signature_history.request_id IS
    'X-Request-Id of the API call that produced this signature_history row. NULL for system-generated rows.';

INSERT INTO public.schema_migrations (version, description)
VALUES ('048_request_id_columns',
        'Correlation IDs on webhook_deliveries.originating_request_id and signature_history.request_id.')
ON CONFLICT (version) DO NOTHING;
