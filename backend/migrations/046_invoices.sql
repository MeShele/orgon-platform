-- 046_invoices.sql
--
-- Monthly invoice ledger.
--
-- One row per (merchant_id, billing_period). billing_period is the
-- first day of the calendar month being billed (UTC). amount + items
-- are computed from merchant_usage_daily at generation time and
-- frozen into the row — even if usage rows are later edited /
-- pruned, the invoice stays reproducible.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.invoices (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    -- First day of the month being billed (e.g. 2026-04-01 for the
    -- April 2026 invoice generated on 2026-05-01).
    billing_period  date NOT NULL,
    plan            text NOT NULL,
    currency        text NOT NULL DEFAULT 'USD',
    -- Frozen at generation time: sum of base + overage fees.
    amount_total    numeric(18, 2) NOT NULL DEFAULT 0,
    -- Per-line breakdown as JSON so we can render it later without
    -- recomputing. Example shape:
    --   [{"label":"Starter plan","amount":99.00},
    --    {"label":"API calls overage","qty":12345,"unit":0.001,"amount":12.34}]
    items           jsonb NOT NULL DEFAULT '[]'::jsonb,
    -- Aggregates we report on the invoice. Frozen.
    api_calls_total integer NOT NULL DEFAULT 0,
    tx_count_total  integer NOT NULL DEFAULT 0,
    -- Lifecycle.
    status          text NOT NULL DEFAULT 'open',  -- 'open'|'paid'|'void'
    issued_at       timestamptz NOT NULL DEFAULT now(),
    paid_at         timestamptz,
    UNIQUE (merchant_id, billing_period)
);

CREATE INDEX IF NOT EXISTS idx_invoices_merchant ON public.invoices (merchant_id, billing_period DESC);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON public.invoices (status) WHERE status = 'open';
