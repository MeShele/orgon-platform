-- 054_monitoring_rules_source.sql
--
-- Tag every `transaction_monitoring_rules` row with where it came
-- from. Enables the compliance officer's `/compliance/rules` UI to
-- distinguish rules edited inside the dashboard from rules pushed by
-- an external orchestrator (asystem-core's admin UI mirroring AML
-- rules via HMAC API).
--
-- Values today:
--   'ui'   — created/edited via /api/v1/compliance/rules (JWT)
--   'api'  — created/edited via /v1/compliance/rules     (HMAC, Wave 34)
--
-- Why a free-text column (not enum): we expect future channels
-- (CSV import, automation script, scheduled-template engine) to land
-- without a schema bump. App-side validates known values; the DB
-- accepts anything truthy so old code never crashes on an unfamiliar
-- value.
--
-- Idempotent.

ALTER TABLE public.transaction_monitoring_rules
    ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'ui';

COMMENT ON COLUMN public.transaction_monitoring_rules.source IS
    'Provisioning channel. ''ui'' = /api/v1/compliance/rules (JWT). ''api'' = /v1/compliance/rules (HMAC). Free-text so future channels land without a schema bump.';

INSERT INTO public.schema_migrations (version, description)
VALUES ('054', 'transaction_monitoring_rules.source — distinguish API-managed rules')
ON CONFLICT (version) DO NOTHING;
