-- 053_organizations_provisioning_source.sql
--
-- Tag every `organizations` row with where it came from. Enables the
-- platform-admin dashboard to distinguish operators onboarded manually
-- (by us via /api/admin/merchants) from operators self-provisioned via
-- the new platform API (/platform/merchants), without inferring it from
-- `created_by IS NULL` (which is fragile — other flows insert with NULL
-- and the proxy breaks silently).
--
-- Values today:
--   'manual' — created via /api/admin/merchants (JWT, human operator)
--   'api'    — created via /platform/merchants (platform master key)
--
-- Future values will land here when other sources appear (CSV import,
-- self-onboarding wizard, ...). Keep nullable=false with a default so
-- back-fill of historical rows lands cleanly during boot.

ALTER TABLE public.organizations
    ADD COLUMN IF NOT EXISTS provisioning_source text NOT NULL DEFAULT 'manual';

COMMENT ON COLUMN public.organizations.provisioning_source IS
    'Where this merchant row came from. ''manual'' = /api/admin/merchants (JWT). ''api'' = /platform/merchants (platform master key). Free-text so future channels (CSV import, wizard) can land without a schema bump.';

-- Track which Wave shipped this overlay.
INSERT INTO public.schema_migrations (version, description)
VALUES ('053', 'organizations.provisioning_source — distinguish API-onboarded merchants')
ON CONFLICT (version) DO NOTHING;
