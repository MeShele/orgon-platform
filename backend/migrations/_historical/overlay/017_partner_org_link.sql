-- Migration 017: link `partners` to `organizations`
-- Date: 2026-04-27
-- Purpose: B2B partner endpoints (routes_partner*.py) currently call
--          WalletService/TransactionService with no tenancy filter, so any
--          partner's API key returns every other partner's wallets and
--          transactions. The service layer already supports `org_ids=[…]`
--          filtering — we just had no link from a partner to an organization.
--
--          This migration:
--            1. Adds nullable `partners.organization_id` (NULL = legacy /
--               internal partner with no scoping).
--            2. Creates an index for the JOIN.
--            3. Backfills demo partners from `partners.metadata->>org_id`
--               when present (no-op if metadata empty).
--
-- Idempotent. Reversible: see rollback block at the bottom.

BEGIN;

ALTER TABLE partners
    ADD COLUMN IF NOT EXISTS organization_id UUID
        REFERENCES organizations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_partners_organization_id
    ON partners(organization_id)
    WHERE organization_id IS NOT NULL;

COMMENT ON COLUMN partners.organization_id IS
    'Organization this B2B partner is scoped to. NULL = unscoped (legacy or platform-admin).';

-- Best-effort backfill from metadata (demo data has it; older rows do not).
UPDATE partners
   SET organization_id = (metadata->>'org_id')::uuid
 WHERE organization_id IS NULL
   AND metadata ? 'org_id'
   AND (metadata->>'org_id') ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';

COMMIT;

-- Rollback (manual):
-- BEGIN;
--   DROP INDEX IF EXISTS idx_partners_organization_id;
--   ALTER TABLE partners DROP COLUMN IF EXISTS organization_id;
-- COMMIT;
