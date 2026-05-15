-- 045_deposit_cursor_rename.sql
--
-- Rename last_seen_ts_trc20 → last_seen_ts_tokens. The cursor pattern
-- (native stream + token stream) is the same for ERC20 on Ethereum
-- and TRC20 on Tron; using a chain-neutral name avoids a fresh
-- column per chain.
--
-- Idempotent: only renames if the source column still exists.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'deposit_watch_cursors'
           AND column_name = 'last_seen_ts_trc20'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'deposit_watch_cursors'
           AND column_name = 'last_seen_ts_tokens'
    ) THEN
        ALTER TABLE public.deposit_watch_cursors
            RENAME COLUMN last_seen_ts_trc20 TO last_seen_ts_tokens;
    END IF;
END $$;
