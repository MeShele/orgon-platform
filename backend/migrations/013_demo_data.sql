-- Migration 013: Demo Data
-- Date: 2026-04-27
-- Purpose: Seed two demo organizations + link existing demo users to them, attach existing
--          wallets/transactions to a default organization, and create a few extra demo
--          transactions so a fresh login as demo-admin/demo-signer/demo-viewer shows live data.
--
-- Idempotent: every INSERT uses ON CONFLICT DO NOTHING or WHERE NOT EXISTS.

BEGIN;

-- ============================================================
-- 1. Demo Organizations
-- ============================================================

INSERT INTO organizations (id, name, slug, license_type, status, email, phone, city, country, settings)
VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    'Demo Exchange KG',
    'demo-exchange-kg',
    'enterprise',
    'active',
    'admin@demo-exchange.kg',
    '+996 555 100 200',
    'Bishkek',
    'Kyrgyzstan',
    '{
        "kyc_required": true,
        "daily_limit_usd": 100000,
        "supported_chains": ["Tron", "BNB", "ETH"],
        "api_enabled": true
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

INSERT INTO organizations (id, name, slug, license_type, status, email, phone, city, country, settings)
VALUES (
    '234e5678-e89b-12d3-a456-426614174111',
    'Demo Broker KG',
    'demo-broker-kg',
    'pro',
    'active',
    'info@demo-broker.kg',
    '+996 555 300 400',
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
-- 2. User <-> Organization links for demo accounts
-- ============================================================
-- user_organizations.role allows: admin / operator / viewer
-- We attach demo accounts with the role that mirrors their global users.role.

INSERT INTO user_organizations (user_id, organization_id, role)
SELECT u.id, '123e4567-e89b-12d3-a456-426614174000'::uuid, 'admin'
FROM users u WHERE u.email = 'demo-admin@orgon.io'
ON CONFLICT (user_id, organization_id) DO NOTHING;

INSERT INTO user_organizations (user_id, organization_id, role)
SELECT u.id, '234e5678-e89b-12d3-a456-426614174111'::uuid, 'admin'
FROM users u WHERE u.email = 'demo-admin@orgon.io'
ON CONFLICT (user_id, organization_id) DO NOTHING;

INSERT INTO user_organizations (user_id, organization_id, role)
SELECT u.id, '123e4567-e89b-12d3-a456-426614174000'::uuid, 'operator'
FROM users u WHERE u.email = 'demo-signer@orgon.io'
ON CONFLICT (user_id, organization_id) DO NOTHING;

INSERT INTO user_organizations (user_id, organization_id, role)
SELECT u.id, '123e4567-e89b-12d3-a456-426614174000'::uuid, 'viewer'
FROM users u WHERE u.email = 'demo-viewer@orgon.io'
ON CONFLICT (user_id, organization_id) DO NOTHING;

-- Also pin super-admin Ruslan to both for convenience
INSERT INTO user_organizations (user_id, organization_id, role)
SELECT u.id, '123e4567-e89b-12d3-a456-426614174000'::uuid, 'admin'
FROM users u WHERE u.email = 'ruslan@asystem.kg'
ON CONFLICT (user_id, organization_id) DO NOTHING;

INSERT INTO user_organizations (user_id, organization_id, role)
SELECT u.id, '234e5678-e89b-12d3-a456-426614174111'::uuid, 'admin'
FROM users u WHERE u.email = 'ruslan@asystem.kg'
ON CONFLICT (user_id, organization_id) DO NOTHING;

-- ============================================================
-- 3. Attach existing wallets/transactions to the primary demo org
-- ============================================================
-- Existing prod data was created before multi-tenancy and has organization_id = NULL.
-- Only update rows where organization_id IS NULL — never overwrite.

UPDATE wallets
   SET organization_id = '123e4567-e89b-12d3-a456-426614174000'::uuid
 WHERE organization_id IS NULL;

UPDATE transactions
   SET organization_id = '123e4567-e89b-12d3-a456-426614174000'::uuid
 WHERE organization_id IS NULL;

-- ============================================================
-- 4. Move 3 wallets over to Demo Broker so the second org has data too
-- ============================================================
-- Pick the highest-id wallets so the primary org keeps most of its inventory.

WITH movable AS (
    SELECT id FROM wallets
     WHERE organization_id = '123e4567-e89b-12d3-a456-426614174000'::uuid
     ORDER BY id DESC
     LIMIT 3
)
UPDATE wallets w
   SET organization_id = '234e5678-e89b-12d3-a456-426614174111'::uuid
  FROM movable m
 WHERE w.id = m.id
   AND NOT EXISTS (
       SELECT 1 FROM wallets x
        WHERE x.organization_id = '234e5678-e89b-12d3-a456-426614174111'::uuid
   );

-- ============================================================
-- 5. Demo transactions across both orgs
-- ============================================================
-- Insert a small set with varied statuses, so dashboards render correctly.
-- Skip if the demo tx_unid is already present to keep this idempotent.

INSERT INTO transactions (
    wallet_name, tx_unid, tx_hash, from_address, to_address,
    amount_decimal, network, status, fee, info, organization_id, token, value
)
SELECT * FROM (VALUES
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0001', '0xdemo0001', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZdf12345abcdefghijklmnopqr', 250.00, 5010, 'confirmed',  0.5, 'Demo confirmed transfer',     '123e4567-e89b-12d3-a456-426614174000'::uuid, 'USDT', '250.00'),
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0002', '0xdemo0002', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZab98765zyxwvutsrqponmlkj',  1500.00, 5010, 'confirmed', 0.5, 'Demo confirmed payout',       '123e4567-e89b-12d3-a456-426614174000'::uuid, 'USDT', '1500.00'),
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0003', NULL,        'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZ4444444444444444444444444',  500.00, 5010, 'pending',    0.5, 'Awaiting signatures (2/3)',   '123e4567-e89b-12d3-a456-426614174000'::uuid, 'USDT', '500.00'),
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0004', NULL,        'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZ5555555555555555555555555',   75.00, 5010, 'pending',    0.5, 'Awaiting signatures (1/3)',   '123e4567-e89b-12d3-a456-426614174000'::uuid, 'USDT', '75.00'),
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0005', '0xdemo0005', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZ6666666666666666666666666', 1200.00, 5010, 'rejected',   0.5, 'Rejected by compliance',      '123e4567-e89b-12d3-a456-426614174000'::uuid, 'USDT', '1200.00'),
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0006', '0xdemo0006', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZ7777777777777777777777777',  300.00, 5010, 'sent',       0.5, 'Broadcast, awaiting confirms','234e5678-e89b-12d3-a456-426614174111'::uuid, 'USDT', '300.00'),
    ('E55EF29AACC3C7B145258D930049023B', 'DEMO-TX-0007', '0xdemo0007', 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t', 'TXYZ8888888888888888888888888',  900.00, 5010, 'confirmed',  0.5, 'Demo broker payout',          '234e5678-e89b-12d3-a456-426614174111'::uuid, 'USDT', '900.00')
) AS v(wallet_name, tx_unid, tx_hash, from_address, to_address, amount_decimal, network, status, fee, info, organization_id, token, value)
WHERE NOT EXISTS (SELECT 1 FROM transactions t WHERE t.tx_unid = v.tx_unid);

-- ============================================================
-- 6. Demo signature_history rows for the pending demo transactions
-- ============================================================

INSERT INTO signature_history (tx_unid, signer_address, action, reason, signed_at)
SELECT * FROM (VALUES
    ('DEMO-TX-0003', 'demo-admin@orgon.io',  'sign',   'Initial approval',          NOW() - INTERVAL '2 hours'),
    ('DEMO-TX-0003', 'demo-signer@orgon.io', 'sign',   'Co-signed by operator',     NOW() - INTERVAL '90 minutes'),
    ('DEMO-TX-0004', 'demo-admin@orgon.io',  'sign',   'Initial approval',          NOW() - INTERVAL '40 minutes')
) AS v(tx_unid, signer_address, action, reason, signed_at)
WHERE NOT EXISTS (
    SELECT 1 FROM signature_history sh
     WHERE sh.tx_unid = v.tx_unid AND sh.signer_address = v.signer_address
);

-- ============================================================
-- Verification
-- ============================================================
DO $$
DECLARE
    org_count int;
    link_count int;
    orphan_wallets int;
    orphan_tx int;
    demo_tx_count int;
BEGIN
    SELECT COUNT(*) INTO org_count FROM organizations;
    SELECT COUNT(*) INTO link_count FROM user_organizations;
    SELECT COUNT(*) INTO orphan_wallets FROM wallets WHERE organization_id IS NULL;
    SELECT COUNT(*) INTO orphan_tx FROM transactions WHERE organization_id IS NULL;
    SELECT COUNT(*) INTO demo_tx_count FROM transactions WHERE tx_unid LIKE 'DEMO-TX-%';

    RAISE NOTICE 'Migration 013 done — orgs=%, user_org_links=%, orphan_wallets=%, orphan_tx=%, demo_tx=%',
        org_count, link_count, orphan_wallets, orphan_tx, demo_tx_count;
END $$;

COMMIT;
