-- 047_idempotency_keys.sql
--
-- Per-merchant idempotency cache for the public /v1/* surface.
--
-- When a merchant includes `X-ORGON-Idempotency-Key: <opaque-id>` on
-- a mutating call (POST/PATCH/PUT/DELETE), the HMAC middleware will,
-- on a successful 2xx, freeze (status, body, content-type) keyed by
-- (merchant_id, idem_key). A subsequent call with the same key — even
-- after the original network blip that prompted the retry — replays
-- the original response byte-for-byte.
--
-- request_hash = sha256("METHOD\n/path\n" || raw_body). It is recorded
-- but NEVER causes a hard reject on mismatch — dfns-style: a client
-- retry after a half-broken transport may legitimately re-serialize
-- the body (json key order, whitespace) and we'd be punishing the
-- caller for our own non-determinism. Instead the middleware logs the
-- discrepancy and returns the cached response unchanged.
--
-- TTL = 24h. Cleanup runs hourly via the scheduler.
--
-- Idempotent: IF NOT EXISTS everywhere; ON CONFLICT DO NOTHING on
-- the schema_migrations marker row.

CREATE TABLE IF NOT EXISTS public.merchant_idempotency_keys (
    merchant_id       uuid    NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    idem_key          text    NOT NULL,
    -- sha256(method|path|body) — for drift detection in logs, not enforcement
    request_hash      text    NOT NULL,
    response_status   integer NOT NULL,
    response_body     bytea   NOT NULL,
    response_headers  jsonb   NOT NULL DEFAULT '{}'::jsonb,
    created_at        timestamptz NOT NULL DEFAULT now(),
    expires_at        timestamptz NOT NULL DEFAULT (now() + interval '24 hours'),
    PRIMARY KEY (merchant_id, idem_key)
);

-- Cleanup driver — scheduler does WHERE expires_at < now().
CREATE INDEX IF NOT EXISTS idx_merchant_idempotency_expires
    ON public.merchant_idempotency_keys (expires_at);

COMMENT ON TABLE public.merchant_idempotency_keys IS
    'Cache of frozen /v1/* responses keyed by (merchant_id, X-ORGON-Idempotency-Key). 24h TTL.';

INSERT INTO public.schema_migrations (version, description)
VALUES ('047_idempotency_keys',
        'Per-merchant idempotency cache for /v1/* mutating endpoints (24h TTL).')
ON CONFLICT (version) DO NOTHING;
