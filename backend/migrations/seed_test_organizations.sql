-- Seed Data: Test Organizations for Development
-- Phase: 1.1 Database Design
-- Date: 2026-02-10
-- Purpose: Create 2 test organizations + users + settings for RLS testing

-- ============================================================
-- Test Organizations
-- ============================================================

-- Organization 1: Safina Exchange KG (Enterprise)
INSERT INTO organizations (id, name, slug, license_type, status, email, phone, city, country, settings)
VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    'Safina Exchange KG',
    'safina-kg',
    'enterprise',
    'active',
    'admin@safina.kg',
    '+996 555 123456',
    'Bishkek',
    'Kyrgyzstan',
    '{
        "kyc_required": true,
        "daily_limit_usd": 100000,
        "supported_chains": ["Tron", "BNB", "ETH"],
        "api_enabled": true
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- Organization 2: BitExchange KG (Pro)
INSERT INTO organizations (id, name, slug, license_type, status, email, phone, city, country, settings)
VALUES (
    '234e5678-e89b-12d3-a456-426614174111',
    'BitExchange KG',
    'bitexchange-kg',
    'pro',
    'active',
    'info@bitexchange.kg',
    '+996 555 654321',
    'Osh',
    'Kyrgyzstan',
    '{
        "kyc_required": false,
        "daily_limit_usd": 50000,
        "supported_chains": ["Tron", "BNB"],
        "api_enabled": true
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Organization Settings
-- ============================================================

-- Settings for Safina Exchange KG
INSERT INTO organization_settings (
    organization_id,
    billing_enabled,
    kyc_enabled,
    fiat_enabled,
    features,
    limits,
    branding,
    integrations
)
VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    true,
    true,
    true,
    '{
        "auto_withdrawal": true,
        "2fa_required": true,
        "ip_whitelist": ["1.2.3.4", "5.6.7.8"],
        "webhook_enabled": true
    }'::jsonb,
    '{
        "daily_withdrawal_usdt": 100000,
        "monthly_transactions": 10000,
        "max_wallets": 100,
        "max_users": 50
    }'::jsonb,
    '{
        "logo_url": "https://safina.kg/logo.png",
        "primary_color": "#1E40AF",
        "secondary_color": "#3B82F6",
        "company_name": "Safina Exchange",
        "custom_domain": "exchange.safina.kg"
    }'::jsonb,
    '{
        "safina_api_key": "sk_test_safina_...",
        "webhook_url": "https://api.safina.kg/webhooks/orgon",
        "telegram_bot_token": "123456:ABC-DEF..."
    }'::jsonb
) ON CONFLICT (organization_id) DO NOTHING;

-- Settings for BitExchange KG
INSERT INTO organization_settings (
    organization_id,
    billing_enabled,
    kyc_enabled,
    fiat_enabled,
    features,
    limits,
    branding,
    integrations
)
VALUES (
    '234e5678-e89b-12d3-a456-426614174111',
    true,
    false,
    false,
    '{
        "auto_withdrawal": false,
        "2fa_required": false,
        "webhook_enabled": false
    }'::jsonb,
    '{
        "daily_withdrawal_usdt": 50000,
        "monthly_transactions": 5000,
        "max_wallets": 50,
        "max_users": 20
    }'::jsonb,
    '{
        "logo_url": "https://bitexchange.kg/logo.png",
        "primary_color": "#10B981",
        "secondary_color": "#34D399",
        "company_name": "BitExchange"
    }'::jsonb,
    '{}'::jsonb
) ON CONFLICT (organization_id) DO NOTHING;

-- ============================================================
-- Test Users (assuming users table exists)
-- ============================================================

-- User 1: Admin for Safina Exchange KG
-- INSERT INTO users (id, email, name) VALUES
--     ('user-safina-admin-001', 'admin@safina.kg', 'Safina Admin')
-- ON CONFLICT (id) DO NOTHING;

-- User 2: Operator for Safina Exchange KG
-- INSERT INTO users (id, email, name) VALUES
--     ('user-safina-operator-001', 'operator@safina.kg', 'Safina Operator')
-- ON CONFLICT (id) DO NOTHING;

-- User 3: Admin for BitExchange KG
-- INSERT INTO users (id, email, name) VALUES
--     ('user-bitex-admin-001', 'admin@bitexchange.kg', 'BitEx Admin')
-- ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- User-Organization Relationships
-- ============================================================

-- Link User 1 to Safina (Admin)
-- INSERT INTO user_organizations (user_id, organization_id, role)
-- VALUES ('user-safina-admin-001', '123e4567-e89b-12d3-a456-426614174000', 'admin')
-- ON CONFLICT DO NOTHING;

-- Link User 2 to Safina (Operator)
-- INSERT INTO user_organizations (user_id, organization_id, role)
-- VALUES ('user-safina-operator-001', '123e4567-e89b-12d3-a456-426614174000', 'operator')
-- ON CONFLICT DO NOTHING;

-- Link User 3 to BitExchange (Admin)
-- INSERT INTO user_organizations (user_id, organization_id, role)
-- VALUES ('user-bitex-admin-001', '234e5678-e89b-12d3-a456-426614174111', 'admin')
-- ON CONFLICT DO NOTHING;

-- ============================================================
-- Test Wallets (for RLS testing)
-- ============================================================

-- Wallet 1: Safina Exchange KG
-- INSERT INTO wallets (id, name, address, network, organization_id, created_by)
-- VALUES (
--     'wallet-safina-001',
--     'Safina Main Wallet',
--     '0xABCDEF1234567890ABCDEF1234567890ABCDEF12',
--     'Tron',
--     '123e4567-e89b-12d3-a456-426614174000',
--     'user-safina-admin-001'
-- ) ON CONFLICT (id) DO NOTHING;

-- Wallet 2: BitExchange KG
-- INSERT INTO wallets (id, name, address, network, organization_id, created_by)
-- VALUES (
--     'wallet-bitex-001',
--     'BitExchange Main Wallet',
--     '0xFEDCBA0987654321FEDCBA0987654321FEDCBA09',
--     'BNB',
--     '234e5678-e89b-12d3-a456-426614174111',
--     'user-bitex-admin-001'
-- ) ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- Verification Queries
-- ============================================================

-- Check organizations
SELECT id, name, slug, license_type, status FROM organizations;

-- Check settings
SELECT 
    organization_id, 
    billing_enabled, 
    kyc_enabled, 
    fiat_enabled,
    features->>'auto_withdrawal' as auto_withdrawal,
    limits->>'daily_withdrawal_usdt' as daily_limit
FROM organization_settings;

-- Check user-organization relationships (after creating users)
-- SELECT 
--     uo.user_id, 
--     u.name, 
--     o.name as organization, 
--     uo.role
-- FROM user_organizations uo
-- JOIN users u ON u.id = uo.user_id
-- JOIN organizations o ON o.id = uo.organization_id;

-- ============================================================
-- Comments
-- ============================================================

COMMENT ON TABLE organizations IS 'Seed: 2 test organizations (Safina Exchange KG, BitExchange KG)';
COMMENT ON TABLE organization_settings IS 'Seed: Settings for 2 test organizations (features, limits, branding)';
