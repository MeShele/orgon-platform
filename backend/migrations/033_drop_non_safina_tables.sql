-- 033_drop_non_safina_tables.sql
--
-- Wave 28 cleanup: drop tables backing the modules that were removed
-- (fiat on-ramp, SaaS billing, B2B partner stack, downstream webhook
-- delivery). Principle: ORGON is an operational layer over Safina,
-- nothing in Safina => nothing here.
--
-- Order matters — child tables first so FKs don't trip. CASCADE picks
-- up anything I missed (orphan indexes, dependent views, etc.).
--
-- audit_log_b2b is dropped here because AuditService was rewritten in
-- the same commit to write/read `audit_log` (the canonical narrower
-- table) instead. /api/audit/logs now reads from `audit_log` directly.
-- No data migration: on prod audit_log_b2b had no operational rows
-- worth preserving (started getting writes only with the JwtAuditMiddleware
-- fix on 2026-05-11; the same handler now targets audit_log).
--
-- Idempotent: IF EXISTS on every drop.

BEGIN;

-- B2B partner stack
DROP TABLE IF EXISTS public.partner_api_keys      CASCADE;
DROP TABLE IF EXISTS public.partner_request_nonces CASCADE;
DROP TABLE IF EXISTS public.partner_webhooks      CASCADE;
DROP TABLE IF EXISTS public.partners              CASCADE;

-- Webhook delivery (was for partner outbound events)
DROP TABLE IF EXISTS public.webhook_events        CASCADE;

-- SaaS billing (Stripe)
DROP TABLE IF EXISTS public.invoice_line_items    CASCADE;
DROP TABLE IF EXISTS public.invoices              CASCADE;
DROP TABLE IF EXISTS public.subscriptions         CASCADE;
DROP TABLE IF EXISTS public.subscription_plans    CASCADE;

-- Fiat on/off-ramp
DROP TABLE IF EXISTS public.fiat_transactions     CASCADE;

-- Billing-orbital tables (left over after CASCADE drops on subscriptions/invoices)
DROP TABLE IF EXISTS public.organization_payment_methods CASCADE;
DROP TABLE IF EXISTS public.organization_subscriptions   CASCADE;
DROP TABLE IF EXISTS public.payment_gateways             CASCADE;
DROP TABLE IF EXISTS public.payments                     CASCADE;
DROP TABLE IF EXISTS public.transaction_fees             CASCADE;

-- NOTE: `audit_log_b2b` is intentionally NOT dropped here. The currently-
-- running AuditService still reads from it. After the new container with
-- the rewritten AuditService (talking to `audit_log` instead) reaches prod,
-- migration 034 drops audit_log_b2b safely.

COMMIT;
