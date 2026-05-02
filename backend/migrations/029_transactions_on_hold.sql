-- Migration 029 — `on_hold` status for in-house rule engine
-- Wave 23, Story 2.8. Idempotent.

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
        'rejected_signer_mismatch',
        'on_hold'
    ));

-- Compliance-audit query "every tx an in-house rule held".
CREATE INDEX IF NOT EXISTS idx_transactions_status_on_hold
    ON public.transactions (created_at DESC)
    WHERE status = 'on_hold';
