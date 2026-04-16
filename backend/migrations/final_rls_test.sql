-- Final RLS Test (Clean)
-- Run as orgon_app user

-- Cleanup first
DELETE FROM wallets WHERE address LIKE '0xTEST%';

-- Create 3 test wallets for 2 organizations
\echo '=== Creating test data ==='

-- Context: Safina KG
SELECT set_tenant_context('123e4567-e89b-12d3-a456-426614174000', false);
INSERT INTO wallets (name, address, network, organization_id) VALUES
    ('Safina Wallet 1', '0xTEST_SAFINA_1', 'tron', '123e4567-e89b-12d3-a456-426614174000'),
    ('Safina Wallet 2', '0xTEST_SAFINA_2', 'tron', '123e4567-e89b-12d3-a456-426614174000');

-- Context: BitExchange KG
SELECT clear_tenant_context();
SELECT set_tenant_context('234e5678-e89b-12d3-a456-426614174111', false);
INSERT INTO wallets (name, address, network, organization_id) VALUES
    ('BitEx Wallet 1', '0xTEST_BITEX_1', 'tron', '234e5678-e89b-12d3-a456-426614174111');

\echo '✅ Created 3 test wallets (2 Safina, 1 BitEx)'
\echo ''

-- Test 1: Safina should see only 2 wallets
\echo '=== Test 1: Safina context (expect 2 rows) ==='
SELECT clear_tenant_context();
SELECT set_tenant_context('123e4567-e89b-12d3-a456-426614174000', false);
SELECT name, LEFT(address, 20) AS address FROM wallets WHERE address LIKE '0xTEST%';

-- Test 2: BitExchange should see only 1 wallet
\echo ''
\echo '=== Test 2: BitExchange context (expect 1 row) ==='
SELECT clear_tenant_context();
SELECT set_tenant_context('234e5678-e89b-12d3-a456-426614174111', false);
SELECT name, LEFT(address, 20) AS address FROM wallets WHERE address LIKE '0xTEST%';

-- Test 3: Super Admin should see all 3
\echo ''
\echo '=== Test 3: Super Admin context (expect 3 rows) ==='
SELECT clear_tenant_context();
SELECT set_tenant_context('00000000-0000-0000-0000-000000000000', true);
SELECT name, LEFT(address, 20) AS address FROM wallets WHERE address LIKE '0xTEST%';

-- Test 4: No context should see 0 rows
\echo ''
\echo '=== Test 4: No context (expect 0 rows) ==='
SELECT clear_tenant_context();
SELECT name, LEFT(address, 20) AS address FROM wallets WHERE address LIKE '0xTEST%';

-- Cleanup
\echo ''
\echo '=== Cleanup ==='
SELECT set_tenant_context('00000000-0000-0000-0000-000000000000', true);
DELETE FROM wallets WHERE address LIKE '0xTEST%';
SELECT clear_tenant_context();

\echo '✅ RLS Test Complete!'
\echo ''
\echo 'Expected results:'
\echo '  Test 1: 2 rows (Safina wallets only)'
\echo '  Test 2: 1 row (BitEx wallet only)'
\echo '  Test 3: 3 rows (all wallets)'
\echo '  Test 4: 0 rows (no context)'
