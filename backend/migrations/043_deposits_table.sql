-- 043_deposits_table.sql
--
-- Incoming on-chain deposits to merchant wallets.
--
-- The existing `transactions` table holds OUTBOUND transfers we
-- initiated through Safina (it mirrors Safina's /tx endpoint, which
-- explicitly excludes external transfers per their wiki). For
-- inbound deposits we need our own watcher reading chain explorers
-- (TronGrid for Tron, Esplora for BTC, Alchemy for ETH).
--
-- Identity: (network, tx_hash, log_index) — log_index handles the
-- rare case of multiple TRC20 transfers to the same address inside
-- one tx; for native TRX/ETH/BTC the log_index is 0.
--
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.deposits (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    wallet_id       uuid NOT NULL REFERENCES public.wallets(id) ON DELETE CASCADE,
    end_user_id     uuid REFERENCES public.end_users(id) ON DELETE SET NULL,
    network         integer NOT NULL,
    tx_hash         text NOT NULL,
    log_index       integer NOT NULL DEFAULT 0,
    from_address    text,
    to_address      text NOT NULL,
    asset           text NOT NULL,           -- 'TRX' | 'USDT' | 'BTC' | 'ETH' | …
    amount          numeric(38, 18) NOT NULL,
    confirmations   integer NOT NULL DEFAULT 0,
    block_number    bigint,
    block_timestamp timestamptz,
    discovered_at   timestamptz NOT NULL DEFAULT now(),
    -- Where in the lifecycle this row currently sits:
    --   'pending'   — first observed, awaiting enough confirmations
    --   'confirmed' — passed the network-specific threshold
    --   'orphaned'  — block reorganized; row kept for audit
    status          text NOT NULL DEFAULT 'pending',
    webhook_sent    boolean NOT NULL DEFAULT false,
    UNIQUE (network, tx_hash, log_index)
);

CREATE INDEX IF NOT EXISTS idx_deposits_wallet ON public.deposits (wallet_id, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_deposits_merchant ON public.deposits (merchant_id, discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_deposits_status ON public.deposits (status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_deposits_webhook_pending ON public.deposits (id) WHERE webhook_sent = false;

-- Sync cursor: per-wallet last scanned timestamp so the watcher
-- doesn't replay history on every tick. Stored separately so we
-- can reset it independently of the deposits rows themselves.
CREATE TABLE IF NOT EXISTS public.deposit_watch_cursors (
    wallet_id      uuid PRIMARY KEY REFERENCES public.wallets(id) ON DELETE CASCADE,
    last_seen_ts   timestamptz,
    last_polled_at timestamptz NOT NULL DEFAULT now(),
    error_streak   integer NOT NULL DEFAULT 0,
    last_error     text
);
