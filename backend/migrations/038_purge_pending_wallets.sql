-- 038_purge_pending_wallets.sql
--
-- Empty-addr wallets are pre-activation ghosts from Safina: a wallet
-- created without a proper `slist` stays in their backend without ever
-- producing an on-chain address. We were caching those rows locally,
-- which surfaced them in the UI as broken "no address" entries.
--
-- One-shot cleanup. Going forward:
--   * `_create_wallet_internal` no longer inserts the local row pre-
--     activation — the scheduler picks the wallet up only after Safina
--     publishes an addr.
--   * `sync_wallets` skips inserting Safina-side wallets that come back
--     with an empty addr unless we already have the row (so legitimate
--     activations still flow through `ON CONFLICT DO UPDATE`).
--
-- Idempotent.

DELETE FROM wallets
WHERE addr IS NULL OR TRIM(addr) = '';
