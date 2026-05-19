-- 056_transactions_uncertain_emitted_at.sql
--
-- Track whether `transaction.uncertain` (Wave 37) has already been
-- emitted for a given tx. The uncertain event fires once per tx, at
-- the ~10-minute mark of being stuck in `status='signed'` without a
-- `tx_hash`, to give the merchant's UI a "we're checking — usually
-- this finishes in a minute, sometimes longer; contact support if it
-- worries you" signal **well before** the 24h `transaction.failed`
-- sweep concludes the tx is dead.
--
-- Why a per-row column (not a separate `tx_event_log` table):
--   The uncertain sweep needs at-most-once-per-row semantics. The
--   simplest atomic gate is `WHERE ... AND uncertain_emitted_at IS
--   NULL` paired with `SET uncertain_emitted_at = now()` in the same
--   UPDATE…RETURNING. A side table would require a second statement +
--   a JOIN on every sweep tick, with no audit win — the audit log
--   already records every webhook delivery via webhook_deliveries.
--
-- NULL = "not yet emitted". Non-NULL timestamp = "emitted; do not
-- re-fire". Rows that get to `status='failed'` via the 24h sweep keep
-- their uncertain_emitted_at — handy for forensic timing analysis
-- ("did we warn the merchant before we declared this dead?").
--
-- Idempotent.

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS uncertain_emitted_at timestamptz;

COMMENT ON COLUMN public.transactions.uncertain_emitted_at IS
    'Timestamp when transaction.uncertain webhook was emitted for this row. NULL = not yet emitted. At-most-once gate for the uncertain sweep (Wave 37).';

-- Partial index — only meaningful rows matter for the sweep.
-- Rows that already emitted uncertain (non-NULL) or are not in the
-- 'signed' state never need a sweep visit.
CREATE INDEX IF NOT EXISTS idx_transactions_uncertain_sweep
    ON public.transactions (status, updated_at)
    WHERE uncertain_emitted_at IS NULL AND status = 'signed';

INSERT INTO public.schema_migrations (version, description)
VALUES ('056', 'transactions.uncertain_emitted_at — at-most-once gate for transaction.uncertain sweep')
ON CONFLICT (version) DO NOTHING;
