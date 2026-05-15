-- 044_deposit_watcher_trc20.sql
--
-- Splits the deposit watch cursor into native vs TRC20 streams.
-- TronGrid exposes /v1/accounts/{addr}/transactions for native TRX
-- and /v1/accounts/{addr}/transactions/trc20 for TRC20 tokens
-- (USDT, USDC, etc.) — each has independent pagination, so a single
-- shared cursor would either miss TRC20 events or replay them.
--
-- Idempotent.

ALTER TABLE public.deposit_watch_cursors
    ADD COLUMN IF NOT EXISTS last_seen_ts_native timestamptz,
    ADD COLUMN IF NOT EXISTS last_seen_ts_trc20  timestamptz;

-- Backfill: existing rows used the merged `last_seen_ts` for native.
UPDATE public.deposit_watch_cursors
   SET last_seen_ts_native = last_seen_ts
 WHERE last_seen_ts IS NOT NULL
   AND last_seen_ts_native IS NULL;
