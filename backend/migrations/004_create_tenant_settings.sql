-- Migration 004: Create organization_settings table
-- Phase: 1.1 Database Design
-- Date: 2026-02-10
-- Description: Organization-specific settings (features, limits, branding for White Label)

-- Create organization_settings table
CREATE TABLE IF NOT EXISTS organization_settings (
    organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Feature flags
    billing_enabled BOOLEAN NOT NULL DEFAULT true,
    kyc_enabled BOOLEAN NOT NULL DEFAULT false,
    fiat_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Features (flexible JSON)
    features JSONB NOT NULL DEFAULT '{}',
    -- Example: {"auto_withdrawal": true, "2fa_required": true, "ip_whitelist": ["1.2.3.4"]}
    
    -- Limits
    limits JSONB NOT NULL DEFAULT '{}',
    -- Example: {"daily_withdrawal_usdt": 10000, "monthly_transactions": 1000, "max_wallets": 50}
    
    -- Branding (White Label customization)
    branding JSONB NOT NULL DEFAULT '{}',
    -- Example: {
    --   "logo_url": "https://cdn.example.com/logo.png",
    --   "primary_color": "#1E40AF",
    --   "company_name": "Safina Exchange KG",
    --   "custom_domain": "exchange.safina.kg"
    -- }
    
    -- Integrations
    integrations JSONB NOT NULL DEFAULT '{}',
    -- Example: {
    --   "safina_api_key": "sk_...",
    --   "webhook_url": "https://api.exchange.kg/webhooks/orgon",
    --   "telegram_bot_token": "123456:ABC..."
    -- }
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_organization_settings_org ON organization_settings(organization_id);
CREATE INDEX idx_organization_settings_billing ON organization_settings(billing_enabled);
CREATE INDEX idx_organization_settings_kyc ON organization_settings(kyc_enabled);

-- Trigger for updated_at
CREATE TRIGGER update_organization_settings_updated_at
    BEFORE UPDATE ON organization_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE organization_settings IS 'Organization-specific configuration (features, limits, branding, integrations)';
COMMENT ON COLUMN organization_settings.features IS 'Feature flags and settings (flexible JSON)';
COMMENT ON COLUMN organization_settings.limits IS 'Transaction and usage limits (flexible JSON)';
COMMENT ON COLUMN organization_settings.branding IS 'White Label branding (logo, colors, domain)';
COMMENT ON COLUMN organization_settings.integrations IS 'External integrations (Safina API, webhooks, etc.)';

-- Default settings for new organizations
-- Will be created by trigger or application code when organization is created
