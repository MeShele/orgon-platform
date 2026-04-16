-- Migration 001: Create organizations table
-- Phase: 1.1 Database Design
-- Date: 2026-02-10
-- Description: Core multi-tenancy table for ORGON-Safina integration (170+ exchanges)

-- Create organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    
    -- License & Status
    license_type VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (license_type IN ('free', 'basic', 'pro', 'enterprise')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'cancelled')),
    
    -- Subscription
    subscription_expires_at TIMESTAMP,
    
    -- Contact
    email VARCHAR(255),
    phone VARCHAR(50),
    
    -- Address
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    
    -- Settings (flexible JSON for future features)
    settings JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_organizations_slug ON organizations(slug);
CREATE INDEX idx_organizations_status ON organizations(status);
CREATE INDEX idx_organizations_license ON organizations(license_type);
CREATE INDEX idx_organizations_created_at ON organizations(created_at);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for organizations
CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE organizations IS 'Multi-tenant organizations for ORGON-Safina integration (170+ crypto exchanges)';
COMMENT ON COLUMN organizations.slug IS 'URL-friendly unique identifier for organization (e.g., exchange-1, safina-kyrgyzstan)';
COMMENT ON COLUMN organizations.license_type IS 'Subscription tier: free (trial), basic, pro, enterprise';
COMMENT ON COLUMN organizations.status IS 'Organization status: active, suspended (payment issue), cancelled';
COMMENT ON COLUMN organizations.settings IS 'Flexible JSON for future features (API keys, webhooks, etc.)';
