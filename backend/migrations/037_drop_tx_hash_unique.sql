-- 037_drop_tx_hash_unique.sql
--
-- transactions.tx_hash had a UNIQUE constraint on the assumption that
-- once a transaction broadcasts, the blockchain returns a unique hash.
-- True for confirmed transactions — but Safina also uses this field
-- to surface state markers for expired/canceled txs, e.g.
-- "Transaction canceled, 1 day limit." as a literal string. Two of
-- those collide and the whole sync_transactions tick crashed every
-- minute on:
--   ERROR: duplicate key value violates unique constraint "transactions_tx_hash_key"
--   DETAIL: Key (tx_hash)=(Transaction canceled, 1 day limit.) already exists.
--
-- Dropping the UNIQUE keeps the btree index for lookup (we kept the
-- non-unique idx_transactions_hash). Unique-by-unid is already
-- enforced (transactions_unid_key) and that's the actual tx identity.
--
-- Idempotent.

ALTER TABLE public.transactions
    DROP CONSTRAINT IF EXISTS transactions_tx_hash_key;
