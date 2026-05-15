-- 041_b2b_merchant_foundation.sql
--
-- Foundation for the dfns-style B2B merchant platform.
--
-- ORGON evolves from "one organization runs the UI" into a multi-
-- tenant API platform where merchants (exchangers, banks, exchanges)
-- onboard their own end-users, and each end-user gets per-network
-- custodial wallets lazily on demand.
--
-- This migration only adds schema — no business code yet. Existing
-- `organizations`, `wallets`, `users`, `transactions` keep working
-- exactly as before; new columns default to NULL / sensible values.
--
-- Hierarchy after this migration:
--
--   organizations  ← merchant (existing row)
--     │
--     ├─ merchant_api_keys      ← (this file) public + secret-hash pair
--     ├─ merchant_users         ← (existing `users`, internal staff)
--     └─ end_users              ← (this file) merchant's customers
--          └─ wallets           ← (existing `wallets`, now FK-linked)
--               └─ transactions
--
-- Idempotent: every CREATE/ADD uses IF NOT EXISTS.

-- ---------------------------------------------------------------------
-- 1. organizations → merchants metadata
-- ---------------------------------------------------------------------
ALTER TABLE public.organizations
    ADD COLUMN IF NOT EXISTS merchant_kind text,           -- 'exchanger' | 'bank' | 'exchange' | 'internal'
    ADD COLUMN IF NOT EXISTS webhook_url text,
    ADD COLUMN IF NOT EXISTS webhook_secret text,          -- HMAC secret we sign webhook payloads with
    ADD COLUMN IF NOT EXISTS pricing_plan text,            -- 'sandbox' | 'starter' | 'growth' | 'enterprise'
    ADD COLUMN IF NOT EXISTS sandbox boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN public.organizations.merchant_kind IS
    'Classification of the merchant tenant. NULL = legacy/internal org.';
COMMENT ON COLUMN public.organizations.sandbox IS
    'True merchants always live on testnet networks; their /v1/* calls land on TRX-Nile / ETH-Sepolia / BTC-test only.';

-- ---------------------------------------------------------------------
-- 2. API keys for B2B inbound auth (HMAC-signed requests)
-- ---------------------------------------------------------------------
-- One merchant can hold several keys at once (e.g. one for prod, one
-- in rotation). We never store the secret in plaintext — only its
-- argon2/bcrypt hash. The public id is what the client puts in
-- X-ORGON-Key headers; we lookup the hash by that id, recompute HMAC
-- over the request, and compare.
CREATE TABLE IF NOT EXISTS public.merchant_api_keys (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id       uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    key_pub           text NOT NULL UNIQUE,           -- e.g. "ok_live_abc123…"
    secret_hash       text NOT NULL,                  -- argon2(secret)
    label             text,                           -- human label: "prod", "rotation 2026Q3"
    scopes            text[] NOT NULL DEFAULT '{}',   -- 'wallets:read', 'wallets:write', 'tx:send', …
    last_used_at      timestamptz,
    expires_at        timestamptz,
    revoked_at        timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    created_by        integer
);
CREATE INDEX IF NOT EXISTS idx_merchant_api_keys_merchant ON public.merchant_api_keys (merchant_id);
CREATE INDEX IF NOT EXISTS idx_merchant_api_keys_active ON public.merchant_api_keys (key_pub) WHERE revoked_at IS NULL;

-- ---------------------------------------------------------------------
-- 3. Replay-protection nonces for HMAC requests
-- ---------------------------------------------------------------------
-- Each signed inbound request carries a UUID nonce + unix-ms timestamp;
-- we reject if (nonce, key_pub) was seen before, and if the timestamp
-- drifts by more than ±60s from server time. Rows are pruned hourly.
CREATE TABLE IF NOT EXISTS public.merchant_request_nonces (
    key_pub      text NOT NULL,
    nonce        text NOT NULL,
    seen_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (key_pub, nonce)
);
CREATE INDEX IF NOT EXISTS idx_merchant_nonces_seen_at ON public.merchant_request_nonces (seen_at);

-- ---------------------------------------------------------------------
-- 4. end_users — merchant's customers (millions of rows expected)
-- ---------------------------------------------------------------------
-- external_id is the merchant's own user id (their authoritative key);
-- we keep it both for idempotent POST /v1/users (same external_id →
-- same row) and so merchants can search their own users without
-- learning our UUIDs.
-- email is the address we put into Safina's slist for that user's
-- wallets. KYC status is informational — Safina-side compliance
-- is the merchant's responsibility (#4 from product Q&A).
CREATE TABLE IF NOT EXISTS public.end_users (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id    uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    external_id    text NOT NULL,
    email          text NOT NULL,
    kyc_status     text,                              -- 'pending' | 'approved' | 'rejected' | NULL
    metadata       jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (merchant_id, external_id),
    UNIQUE (merchant_id, email)
);
CREATE INDEX IF NOT EXISTS idx_end_users_merchant ON public.end_users (merchant_id);
CREATE INDEX IF NOT EXISTS idx_end_users_email ON public.end_users (lower(email));

-- ---------------------------------------------------------------------
-- 5. wallets → link to end_user + classify by purpose
-- ---------------------------------------------------------------------
-- end_user_id is NULL for treasury/fee wallets owned by the merchant
-- itself. purpose tells the UI / billing whose hands the wallet is in.
ALTER TABLE public.wallets
    ADD COLUMN IF NOT EXISTS end_user_id uuid REFERENCES public.end_users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS purpose text;            -- 'treasury' | 'fee' | 'hot' | 'cold' | 'user_deposit'

CREATE INDEX IF NOT EXISTS idx_wallets_end_user ON public.wallets (end_user_id) WHERE end_user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_wallets_purpose ON public.wallets (organization_id, purpose);

-- ---------------------------------------------------------------------
-- 6. Webhook delivery queue
-- ---------------------------------------------------------------------
-- We persist every event we owe a merchant before attempting delivery,
-- so retries survive backend restarts. last_status is the HTTP code
-- from their endpoint; next_retry_at is set by the retry policy
-- (exponential backoff). delivered_at is non-null on first 2xx.
CREATE TABLE IF NOT EXISTS public.webhook_deliveries (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id     uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    event_type      text NOT NULL,                    -- 'wallet.activated', 'transaction.confirmed', …
    payload         jsonb NOT NULL,
    attempts        integer NOT NULL DEFAULT 0,
    last_status     integer,
    last_error      text,
    next_retry_at   timestamptz,
    delivered_at    timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending
    ON public.webhook_deliveries (next_retry_at)
    WHERE delivered_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_merchant
    ON public.webhook_deliveries (merchant_id, created_at DESC);

-- ---------------------------------------------------------------------
-- 7. Daily usage counters (drives monthly invoice in sprint 5)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.merchant_usage_daily (
    merchant_id    uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    day            date NOT NULL,
    api_calls      integer NOT NULL DEFAULT 0,
    active_users   integer NOT NULL DEFAULT 0,
    tx_count       integer NOT NULL DEFAULT 0,
    PRIMARY KEY (merchant_id, day)
);
