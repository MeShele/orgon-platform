-- 035_wallet_tenant_backfill.sql
--
-- Pre-multi-tenancy era: wallets and transactions were created
-- via Safina sync with organization_id = NULL. After the org-filter
-- fix (cad7c07) those rows became invisible to any tenant.
--
-- One-shot backfill: any wallet/tx still at NULL gets attached to the
-- seed organization "Safina Exchange KG" so the existing 29 wallets
-- and 27 historical transactions stay visible to demo-admin.
--
-- Future inserts route organization_id through routes_wallets.py
-- and transaction_service — this migration is only for legacy state.
--
-- Idempotent: only touches NULL rows.

UPDATE wallets
   SET organization_id = '123e4567-e89b-12d3-a456-426614174000'
 WHERE organization_id IS NULL;

UPDATE transactions
   SET organization_id = '123e4567-e89b-12d3-a456-426614174000'
 WHERE organization_id IS NULL;
