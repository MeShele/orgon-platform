-- Test RLS (Row-Level Security) Isolation
-- Purpose: Verify that organizations see only their own data

\echo '\n=== RLS ISOLATION TEST ==='
\echo '\n1. Creating test wallets for both organizations...'

-- Create wallet for Safina Exchange KG
INSERT INTO wallets (name, address, network, organization_id)
VALUES (
    'Safina Test Wallet',
    '0xSAFINA123...',
    'tron',
    '123e4567-e89b-12d3-a456-426614174000'
);

-- Create wallet for BitExchange KG
INSERT INTO wallets (name, address, network, organization_id)
VALUES (
    'BitExchange Test Wallet',
    '0xBITEX456...',
    'tron',
    '234e5678-e89b-12d3-a456-426614174111'
);

\echo '✅ Created 2 test wallets'
\echo ''

-- Test 1: Set context for Safina KG
\echo '2. Setting context for Safina Exchange KG...'
SELECT set_tenant_context('123e4567-e89b-12d3-a456-426614174000', false);

\echo '   Querying wallets (should see only Safina wallet):'
SELECT id, name, address, organization_id FROM wallets;

\echo ''
\echo 'Expected: 1 row (Safina Test Wallet)'
\echo ''

-- Test 2: Set context for BitExchange KG
\echo '3. Setting context for BitExchange KG...'
SELECT clear_tenant_context();
SELECT set_tenant_context('234e5678-e89b-12d3-a456-426614174111', false);

\echo '   Querying wallets (should see only BitExchange wallet):'
SELECT id, name, address, organization_id FROM wallets;

\echo ''
\echo 'Expected: 1 row (BitExchange Test Wallet)'
\echo ''

-- Test 3: Super Admin context (see all)
\echo '4. Setting Super Admin context...'
SELECT clear_tenant_context();
SELECT set_tenant_context('00000000-0000-0000-0000-000000000000', true);

\echo '   Querying wallets (should see ALL wallets):'
SELECT id, name, address, organization_id FROM wallets;

\echo ''
\echo 'Expected: 2 rows (both wallets)'
\echo ''

-- Test 4: No context (should block)
\echo '5. Testing without context (should block or return empty)...'
SELECT clear_tenant_context();

\echo '   Querying wallets (should return 0 rows or error):'
SELECT id, name, address, organization_id FROM wallets;

\echo ''
\echo 'Expected: 0 rows (RLS blocks access without context)'
\echo ''

-- Cleanup
\echo '=== CLEANUP ==='
SELECT set_tenant_context('00000000-0000-0000-0000-000000000000', true);
DELETE FROM wallets WHERE address IN ('0xSAFINA123...', '0xBITEX456...');
SELECT clear_tenant_context();

\echo '✅ RLS test complete!'
\echo ''
\echo 'If all tests passed:'
\echo '  ✅ Organization A sees only its data'
\echo '  ✅ Organization B sees only its data'
\echo '  ✅ Super Admin sees all data'
\echo '  ✅ No context = no access'
\echo ''
