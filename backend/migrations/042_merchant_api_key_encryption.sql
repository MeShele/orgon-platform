-- 042_merchant_api_key_encryption.sql
--
-- Adds at-rest encryption for merchant API secrets.
--
-- bcrypt hash alone makes the secret unrecoverable, but HMAC
-- verification on inbound /v1/* requests needs the plaintext on the
-- server side. We resolve that by *also* storing the secret encrypted
-- with pgcrypto's pgp_sym_encrypt, using a master key sourced from
-- the MERCHANT_KEY_MASTER env var at runtime.
--
-- The bcrypt hash stays — it serves as a tamper-evidence audit trail
-- (any decrypt mismatch can be sanity-checked against the hash) and
-- as a safety net if the encryption key is ever rotated.
--
-- Idempotent.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE public.merchant_api_keys
    ADD COLUMN IF NOT EXISTS secret_encrypted bytea;

COMMENT ON COLUMN public.merchant_api_keys.secret_encrypted IS
    'pgp_sym_encrypt(secret_plain, env::MERCHANT_KEY_MASTER). Decrypted in-memory only when the HMAC middleware needs to verify a request. NULL for keys issued before this migration — they must be rotated to use /v1/*.';
