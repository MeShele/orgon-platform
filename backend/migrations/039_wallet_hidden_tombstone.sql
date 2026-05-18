-- 039_wallet_hidden_tombstone.sql
--
-- Wallet `is_hidden` tombstone column (the schema part, kept).
--
-- Original migration also did a one-time tombstone of every
-- pre-min_signs Asystem Change wallet:
--
--   UPDATE public.wallets SET is_hidden = TRUE
--     WHERE organization_id = 'aabbccdd-1111-2222-3333-aaaabbbbcccc';
--
-- That repair ran against the live DB in May 2026. It is RETIRED
-- here for the same reason migration 040's body is retired:
-- `backend/entrypoint.sh` re-runs every overlay on every container
-- boot (ORGON_AUTO_MIGRATE=1). Leaving the destructive UPDATE in
-- place means every deploy re-tombstones every wallet in the org —
-- including the post-fix legit wallets — and the UI goes empty.
-- Observed exactly this 2026-05-18 right after deploy w13u30jd:
-- "каждая организация пустая".
--
-- The `is_hidden` column itself is still added below (DDL stays —
-- without it later migrations/code that reads `is_hidden` would
-- error on a fresh DB).
--
-- If a similar bulk tombstone is ever needed again, write a NEW
-- migration (e.g. 0NN_wallet_tombstone_<date>.sql), don't reuse this
-- slot.
--
-- Idempotent.

ALTER TABLE public.wallets
    ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

-- (Original bulk-tombstone body retired — see header.)
