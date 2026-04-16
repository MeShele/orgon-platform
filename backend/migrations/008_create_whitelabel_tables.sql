-- Migration 008: White Label & Branding Tables
-- Phase: 3.1 White Label UI
-- Date: 2026-02-12
-- Description: Organization branding, custom domains, email templates

-- ============================================================
-- WHITE LABEL TABLES
-- ============================================================

-- 1. Organization Branding
CREATE TABLE organization_branding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID UNIQUE NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Logo & Visuals
    logo_url TEXT,  -- Primary logo (CloudFlare R2 / S3)
    logo_dark_url TEXT,  -- Dark mode logo
    favicon_url TEXT,
    
    -- Color Scheme
    color_primary VARCHAR(7) DEFAULT '#3B82F6',  -- Tailwind blue-500
    color_secondary VARCHAR(7) DEFAULT '#10B981',  -- Tailwind green-500
    color_accent VARCHAR(7) DEFAULT '#F59E0B',  -- Tailwind amber-500
    color_background VARCHAR(7) DEFAULT '#FFFFFF',
    color_text VARCHAR(7) DEFAULT '#1F2937',
    
    -- Typography
    font_family VARCHAR(100) DEFAULT 'Inter',
    font_url TEXT,  -- Google Fonts URL or custom
    
    -- Custom Domain
    custom_domain VARCHAR(255),
    domain_verified BOOLEAN DEFAULT FALSE,
    domain_verified_at TIMESTAMPTZ,
    
    -- Branding Text
    platform_name VARCHAR(100),  -- e.g. "MyExchange" instead of "ORGON"
    tagline VARCHAR(255),
    footer_text TEXT,
    
    -- Contact Info
    support_email VARCHAR(255),
    support_phone VARCHAR(50),
    
    -- Social Links
    social_links JSONB DEFAULT '{}',
    -- Example: {"twitter": "https://x.com/myexchange", "telegram": "https://t.me/myexchange"}
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT branding_valid_color_primary CHECK (color_primary ~ '^#[0-9A-F]{6}$'),
    CONSTRAINT branding_valid_color_secondary CHECK (color_secondary ~ '^#[0-9A-F]{6}$')
);

CREATE INDEX idx_branding_org ON organization_branding(organization_id);
CREATE INDEX idx_branding_domain ON organization_branding(custom_domain);

CREATE TRIGGER update_branding_updated_at 
    BEFORE UPDATE ON organization_branding
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2. Email Templates
CREATE TABLE email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Template details
    template_type VARCHAR(50) NOT NULL,
    -- welcome/invoice/kyc_approved/kyc_rejected/payment_received/subscription_renewed/aml_alert
    
    template_name VARCHAR(255) NOT NULL,
    
    -- Email content
    subject VARCHAR(255) NOT NULL,
    body_text TEXT,  -- Plain text version
    body_html TEXT,  -- HTML version
    
    -- Variables (for interpolation)
    variables JSONB DEFAULT '[]',
    -- Example: ["customer_name", "invoice_number", "amount"]
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Constraints
    UNIQUE(organization_id, template_type)
);

CREATE INDEX idx_email_templates_org ON email_templates(organization_id);
CREATE INDEX idx_email_templates_type ON email_templates(template_type);

CREATE TRIGGER update_email_templates_updated_at 
    BEFORE UPDATE ON email_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 3. Custom Domains
CREATE TABLE custom_domains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Domain details
    domain VARCHAR(255) UNIQUE NOT NULL,
    subdomain VARCHAR(100),  -- e.g. "exchange" for exchange.mydomain.com
    
    -- Verification
    verification_method VARCHAR(50) DEFAULT 'dns_txt',  -- dns_txt/dns_cname/file_upload
    verification_token VARCHAR(100) UNIQUE,
    verification_record TEXT,  -- DNS record to add (e.g. "TXT _orgon-verify 123abc")
    
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    
    -- SSL/TLS
    ssl_enabled BOOLEAN DEFAULT FALSE,
    ssl_provider VARCHAR(50),  -- letsencrypt/cloudflare/custom
    ssl_issued_at TIMESTAMPTZ,
    ssl_expires_at TIMESTAMPTZ,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_primary BOOLEAN DEFAULT FALSE,  -- Primary domain for org
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT domains_valid_verification 
        CHECK (verification_method IN ('dns_txt', 'dns_cname', 'file_upload'))
);

CREATE INDEX idx_custom_domains_org ON custom_domains(organization_id);
CREATE INDEX idx_custom_domains_domain ON custom_domains(domain);
CREATE INDEX idx_custom_domains_verified ON custom_domains(verified);

CREATE TRIGGER update_custom_domains_updated_at 
    BEFORE UPDATE ON custom_domains
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Upload Assets (for logos, favicons)
CREATE TABLE upload_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- File details
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(100),  -- image/png, image/svg+xml
    file_size_bytes INT,
    
    -- Storage
    storage_provider VARCHAR(50) DEFAULT 'r2',  -- r2/s3/local
    storage_url TEXT NOT NULL,
    storage_key VARCHAR(255),  -- S3 key or R2 path
    
    -- Metadata
    uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Asset type
    asset_type VARCHAR(50),  -- logo/favicon/banner/background
    
    -- Status
    is_public BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_upload_assets_org ON upload_assets(organization_id);
CREATE INDEX idx_upload_assets_type ON upload_assets(asset_type);

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE organization_branding IS 'White label branding configuration (logo, colors, domain)';
COMMENT ON TABLE email_templates IS 'Customizable transactional email templates';
COMMENT ON TABLE custom_domains IS 'Custom domain verification and SSL management';
COMMENT ON TABLE upload_assets IS 'Uploaded files (logos, favicons, etc.)';

-- ============================================================
-- SEED DATA
-- ============================================================

-- Default email templates (system-wide, organization_id can be NULL for defaults)
-- Organizations can override these by creating their own

-- Note: We'll create org-specific templates via API, not seed data
