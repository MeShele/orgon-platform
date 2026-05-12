-- 032_webhook_events_delivered_at.sql
--
-- `webhook_service.py` reads/writes `delivered_at` column (5+ sites:
-- UPDATE on successful delivery, SELECT in event listing). But the
-- canonical schema (000_canonical_schema.sql) only declared `sent_at`
-- — semantically different: `sent_at` is "outgoing HTTP fired",
-- `delivered_at` is "remote confirmed 2xx". As a result:
--
--   GET /api/v1/partner/webhooks/events  →  500
--   ERROR: column "delivered_at" of relation "webhook_events" does not exist
--
-- This is a schema drift bug — same class as the `transactions.info`
-- bug found in Wave 27. Adding the column matches code intent.
-- Idempotent via IF NOT EXISTS.

ALTER TABLE public.webhook_events
    ADD COLUMN IF NOT EXISTS delivered_at timestamp with time zone;

COMMENT ON COLUMN public.webhook_events.delivered_at IS
    'Timestamp of remote-confirmed (2xx) delivery. NULL until partner ack received. Distinct from sent_at (HTTP fired).';
