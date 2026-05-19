-- 055_deposits_tx_hash_index.sql
--
-- Index supports the `/v1/deposits/lookup?tx_hash=...` query path
-- (Wave 35 — wrong-network rescue tool for support). Without this,
-- a tx_hash lookup falls back to a seq-scan on `deposits` filtered
-- by merchant_id; fine at small scale, painful when a busy merchant
-- has 100k+ rows and support is rapid-firing lookups during an
-- incident.
--
-- Composite (merchant_id, tx_hash) instead of plain (tx_hash) because
-- every supported query path ALSO filters by merchant — the merchant
-- scope is an HMAC invariant. Leading on merchant_id keeps a single
-- index serving both this lookup and merchant-wide deposit listings
-- when filtered by tx_hash.
--
-- Not UNIQUE: `tx_hash` alone is NOT unique across (network, log_index).
-- Existing unique constraint stays on `(network, tx_hash, log_index)`.
--
-- Idempotent.

CREATE INDEX IF NOT EXISTS idx_deposits_merchant_tx_hash
    ON public.deposits (merchant_id, tx_hash);

INSERT INTO public.schema_migrations (version, description)
VALUES ('055', 'deposits (merchant_id, tx_hash) — index for /v1/deposits/lookup')
ON CONFLICT (version) DO NOTHING;
