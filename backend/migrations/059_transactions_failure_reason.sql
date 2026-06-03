-- 059_transactions_failure_reason.sql
--
-- Capture WHY an outbound tx failed.
--
-- Since Safina's 2026-06-03 ETH-Sepolia broadcast fix, a rejected tx no
-- longer hangs forever with `tx=null`: Safina writes a human-readable
-- error string into the `tx` field (e.g.
-- "global: Returned error: EVM error: OutOfFunds"). The sync classifier
-- (`backend/safina/tx_status.classify_safina_tx_status`) now maps such
-- strings to status='failed' instead of leaving the tx stuck in
-- 'signed'. This column persists the verbatim error string so the /v1
-- surface and the `transaction.failed` webhook can surface the reason.
--
-- The `tx_hash` column still only ever holds a real 64-hex hash
-- (clean_tx_hash nulls anything else) — error strings live here, never
-- there. 'failed' is already an allowed status (058), so no CHECK change.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS; the overlay runner executes
-- every overlay on every boot.

ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS failure_reason TEXT;

INSERT INTO public.schema_migrations (version, description)
VALUES ('059_transactions_failure_reason',
        'Add transactions.failure_reason — Safina terminal error string (e.g. EVM error: OutOfFunds) surfaced on /v1 + transaction.failed webhook.')
ON CONFLICT (version) DO NOTHING;
