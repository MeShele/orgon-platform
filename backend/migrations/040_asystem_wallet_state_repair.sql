-- 040_asystem_wallet_state_repair.sql
--
-- ONE-TIME repair of the Asystem Change wallet state that migration
-- 039 over-killed. The original body did:
--
--   UPDATE public.wallets SET is_hidden = FALSE
--     WHERE organization_id = 'aabbccdd-1111-2222-3333-aaaabbbbcccc'
--       AND addr IS NOT NULL AND TRIM(addr) <> '';
--   DELETE FROM public.wallets
--     WHERE organization_id = 'aabbccdd-1111-2222-3333-aaaabbbbcccc'
--       AND (addr IS NULL OR TRIM(addr) = '');
--
-- That ran successfully against the live DB in May 2026.
--
-- It is RETIRED here (no-op body) because `backend/entrypoint.sh` runs
-- every overlay migration on every container startup when
-- ORGON_AUTO_MIGRATE=1 (no per-file marker check beyond canonical).
-- Leaving the destructive UPDATE/DELETE in place meant:
--
--   1. Any operator-managed `is_hidden = TRUE` tombstone on an Asystem
--      wallet got reset to FALSE on every deploy, resurrecting hidden
--      legacy rows in the UI (observed 2026-05-18 — UI showed 22
--      wallets after deploy instead of the 9 active ones).
--   2. The original DELETE would re-fire if Safina's /wallets sync
--      ever brought back a row without an on-chain addr.
--
-- Replacing the body with a no-op keeps the file in place (so file
-- ordering and any external tooling that lists overlays stays
-- consistent) but stops the destructive re-application.
--
-- If a similar repair is ever needed again, write a NEW migration
-- (e.g. 0NN_wallet_state_repair_<date>.sql) — don't reuse this slot.

DO $$
BEGIN
    -- No-op (see header).
END $$;
