-- 040_asystem_wallet_state_repair.sql
--
-- Repair the Asystem Change wallet state that migration 039 over-
-- killed. 039 set is_hidden=TRUE for *every* Asystem wallet, but the
-- intent was only to hide the legacy ECE-ghost wallets (no
-- min_signs in slist → Safina never registers them in its balance
-- monitor). Valid activated wallets (those with on-chain addr) got
-- swept up too and disappeared from the UI.
--
-- Parallel issue: legacy ghost wallets (name = my_unid, addr empty)
-- crept back into the table as is_hidden=FALSE after a manual
-- duplicate cleanup, because sync no longer had a "skip pre-
-- activation untracked" guard. This migration removes them; the
-- guard is restored in code so they won't come back.
--
-- Idempotent.

-- 1. Un-hide every Asystem wallet that has a real on-chain addr —
--    those are legitimate and should be visible.
UPDATE public.wallets
SET is_hidden = FALSE
WHERE organization_id = 'aabbccdd-1111-2222-3333-aaaabbbbcccc'
  AND addr IS NOT NULL
  AND TRIM(addr) <> '';

-- 2. Hard-delete every Asystem wallet without addr — they're either
--    pre-activation ghosts (Safina won't activate them) or stale
--    placeholder rows from old create flows. The restored sync guard
--    prevents Safina's /wallets response from re-inserting them.
DELETE FROM public.wallets
WHERE organization_id = 'aabbccdd-1111-2222-3333-aaaabbbbcccc'
  AND (addr IS NULL OR TRIM(addr) = '');
