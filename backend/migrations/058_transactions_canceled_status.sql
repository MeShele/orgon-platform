-- 058_transactions_canceled_status.sql
--
-- Two-part fix for the false-confirmation bug (verified 2026-05-27).
--
-- Safina overwrites a transaction's `tx` field with a human-readable
-- string ("Transaction canceled, 1 day limit.") when it abandons a
-- signed tx after ~24h. `transaction_service.sync_transactions` used
-- `if tx.tx: status = "confirmed"` and stored that string as `tx_hash`,
-- so canceled txs showed as `confirmed` and fired false
-- transaction.broadcasted/confirmed webhooks. Of 30 demo txs, 26 were
-- mislabeled this way (only 2 had real on-chain hashes).
--
-- Part 1: `canceled` is the correct terminal status for these, but it
-- was missing from the status CHECK (see 028/029) — storing it would
-- crash the per-minute sync loop. Add it.
--
-- Part 2: heal rows already poisoned by the bug — null the garbage
-- tx_hash and set status='canceled'. Idempotent; safe to re-run (the
-- overlay runner executes every overlay on every boot).

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
        'on_hold',
        'canceled'
    ));

-- Heal: any tx_hash that is a Safina status string (not a 64-hex hash)
-- is garbage left by the pre-058 sync. Null it and mark canceled.
UPDATE public.transactions
   SET status = 'canceled',
       tx_hash = NULL,
       updated_at = now()
 WHERE tx_hash IS NOT NULL
   AND tx_hash !~ '^(0x)?[0-9a-fA-F]{64}$'
   AND (
        lower(tx_hash) LIKE '%cancel%'
        OR lower(tx_hash) LIKE '%limit%'
        OR lower(tx_hash) LIKE '%failed%'
   );

-- Belt-and-suspenders: any remaining non-hash tx_hash (unexpected
-- Safina string we didn't anticipate) must not masquerade as a hash.
-- Null it but leave status untouched so we can spot it in logs/audit.
UPDATE public.transactions
   SET tx_hash = NULL,
       updated_at = now()
 WHERE tx_hash IS NOT NULL
   AND tx_hash !~ '^(0x)?[0-9a-fA-F]{64}$';

INSERT INTO public.schema_migrations (version, description)
VALUES ('058_transactions_canceled_status',
        'Add canceled status; null Safina cancellation strings mis-stored as tx_hash (false-confirmation fix).')
ON CONFLICT (version) DO NOTHING;
