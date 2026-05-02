-- Migration 028 — transactions.status enum + signer-mismatch indexing
-- Wave 22, Story 2.7. Idempotent — safe to re-run.

-- The canonical schema currently has no CHECK constraint on
-- `transactions.status` (varchar(50) is open). Wave 22 introduces
-- `rejected_signer_mismatch` for transactions blocked by local
-- signer-verification (ORGON_SAFINA_VERIFY_MODE=enforce). Adding the
-- CHECK now both:
--   1. documents the allowed values for compliance auditors,
--   2. prevents typos from silently creating "almost-rejected" rows.
--
-- We DROP-IF-EXISTS first so the migration re-applies cleanly on
-- environments that picked up an earlier ad-hoc constraint with the
-- same name.

ALTER TABLE public.transactions
    DROP CONSTRAINT IF EXISTS transactions_status_check;

ALTER TABLE public.transactions
    ADD CONSTRAINT transactions_status_check
    CHECK (status IN (
        'pending',
        'signed',
        'submitted',
        'confirmed',
        'failed',
        'rejected_signer_mismatch'
    ));

-- Index for the compliance-audit query "every tx blocked by signer
-- verification". Partial keeps it tiny (rejected-mismatch is rare).
CREATE INDEX IF NOT EXISTS idx_transactions_status_signer_mismatch
    ON public.transactions (created_at DESC)
    WHERE status = 'rejected_signer_mismatch';
