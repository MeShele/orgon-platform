-- Migration 002: Add organization_id to existing tables
-- Phase: 1.1 Database Design
-- Date: 2026-02-10
-- Description: Add tenant isolation column to all tenant-specific tables

-- 1. Wallets
ALTER TABLE wallets 
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_wallets_organization ON wallets(organization_id);

-- 2. Transactions
ALTER TABLE transactions 
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_transactions_organization ON transactions(organization_id);

-- 3. Signatures
ALTER TABLE signatures 
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_signatures_organization ON signatures(organization_id);

-- 4. Contacts
ALTER TABLE contacts 
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_contacts_organization ON contacts(organization_id);

-- 5. Scheduled Transactions
ALTER TABLE scheduled_transactions 
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_scheduled_transactions_organization ON scheduled_transactions(organization_id);

-- 6. Audit Logs (SET NULL because Super Admin should see all logs)
ALTER TABLE audit_logs 
    ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_audit_logs_organization ON audit_logs(organization_id);

-- Comments
COMMENT ON COLUMN wallets.organization_id IS 'Tenant isolation: wallet belongs to this organization';
COMMENT ON COLUMN transactions.organization_id IS 'Tenant isolation: transaction belongs to this organization';
COMMENT ON COLUMN signatures.organization_id IS 'Tenant isolation: signature belongs to this organization';
COMMENT ON COLUMN contacts.organization_id IS 'Tenant isolation: contact belongs to this organization';
COMMENT ON COLUMN scheduled_transactions.organization_id IS 'Tenant isolation: scheduled transaction belongs to this organization';
COMMENT ON COLUMN audit_logs.organization_id IS 'Optional tenant reference for audit logs (NULL = system-wide)';
