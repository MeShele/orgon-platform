-- 039_wallet_hidden_tombstone.sql
--
-- Wallet `is_hidden` tombstone column.
--
-- Why: ECE-created wallets without `min_signs: "1"` in the slist are
-- not picked up by Safina's on-chain balance monitor — the addr is
-- live, but Safina's `value` field stays 0 forever, which makes them
-- useless for any send flow. We want to hide every such wallet from
-- the UI and prevent the scheduler sync from re-inserting it on the
-- next tick (Safina still returns them in /wallets).
--
-- The fix going forward is auto-injecting `min_signs: "1"` at create
-- time (wallet_service._create_wallet_internal). For the existing
-- ghost wallets in the Asystem Change org, mark them hidden so:
--   * /api/wallets list filters them out
--   * sync_wallets skips them on the next tick instead of resurrecting
--
-- We hide rather than DELETE because Safina still owns these wallets;
-- a hard delete would let the next sync tick re-create them.
--
-- Idempotent.

ALTER TABLE public.wallets
    ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN NOT NULL DEFAULT FALSE;

-- Hide every wallet currently attached to Asystem Change — they were
-- created before min_signs auto-inject existed and are stuck with a
-- broken slist that Safina won't monitor.
UPDATE public.wallets
SET is_hidden = TRUE
WHERE organization_id = 'aabbccdd-1111-2222-3333-aaaabbbbcccc';
