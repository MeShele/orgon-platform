-- 060_transactions_confirmation.sql
--
-- Real on-chain confirmation for OUTBOUND transactions.
--
-- `transaction.broadcasted` fires the moment Safina returns a tx_hash
-- (money left toward the chain). Until now `transaction.confirmed`
-- co-fired in the SAME tick — so it was never a real confirmation, just
-- a duplicate of broadcasted. asystem-core marks an order `completed` on
-- `transaction.confirmed`, so a premature confirmed = order completed
-- before the chain actually included the tx (DFNS, by contrast, fires
-- confirmed only on real on-chain confirmation + block_number).
--
-- This decouples them: the lifecycle emit now fires ONLY broadcasted;
-- a new confirmation sweep polls the public explorer for the tx_hash and
-- fires `transaction.confirmed` (with block_number) once the tx is
-- actually in a block. These two additive columns back that sweep —
-- NO change to the operator-facing `status` machine or its CHECK.
--
--   block_number          — populated when on-chain confirmation observed
--   confirmed_emitted_at   — at-most-once gate for the confirmed webhook
--
-- Idempotent: ADD COLUMN IF NOT EXISTS; overlay runner re-runs each boot.

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS block_number bigint;

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS confirmed_emitted_at timestamptz;

-- Sweep selects on (tx_hash present, confirmed_emitted_at IS NULL,
-- organization_id present) — partial index keeps that scan cheap.
CREATE INDEX IF NOT EXISTS idx_transactions_pending_confirmation
    ON public.transactions (updated_at)
    WHERE tx_hash IS NOT NULL
      AND confirmed_emitted_at IS NULL
      AND organization_id IS NOT NULL;

INSERT INTO public.schema_migrations (version, description)
VALUES ('060_transactions_confirmation',
        'Add transactions.block_number + confirmed_emitted_at for real outbound on-chain confirmation (decouples transaction.confirmed from broadcasted).')
ON CONFLICT (version) DO NOTHING;
