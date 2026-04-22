-- Migration 003: Create user_organizations table
-- Phase: 1.1 Database Design
-- Date: 2026-02-10
-- Description: Many-to-many relationship between users and organizations with role-based access

-- Create user_organizations table
CREATE TABLE IF NOT EXISTS user_organizations (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Role-based access control
    role VARCHAR(20) NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin', 'operator', 'viewer')),

    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    
    PRIMARY KEY (user_id, organization_id)
);

-- Indexes
CREATE INDEX idx_user_organizations_user ON user_organizations(user_id);
CREATE INDEX idx_user_organizations_org ON user_organizations(organization_id);
CREATE INDEX idx_user_organizations_role ON user_organizations(role);

-- Comments
COMMENT ON TABLE user_organizations IS 'Many-to-many: users can belong to multiple organizations with different roles';
COMMENT ON COLUMN user_organizations.role IS 'Access level: admin (full access), operator (create transactions), viewer (read-only)';

-- Role descriptions:
-- admin:    Full access to organization (manage wallets, users, settings, billing)
-- operator: Create transactions, sign, manage contacts (daily operations for exchange staff)
-- viewer:   Read-only access (auditor, accountant, compliance officer)
