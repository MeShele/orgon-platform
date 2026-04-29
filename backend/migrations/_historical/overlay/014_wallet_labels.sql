-- Migration 014: Demo wallet labels
-- Date: 2026-04-27
-- Purpose: Give the 11 hex-named demo wallets human-readable labels so the
--          redesigned UI can show "Treasury Cold" instead of E55EF29A...
--
-- Idempotent: only updates rows where wallets.label IS NULL or empty.
-- Targets only the demo organizations created in migration 013.

BEGIN;

-- Demo Exchange KG primary wallets (8 expected after 013)
UPDATE wallets SET label = labels.label
  FROM (VALUES
    (1,  'Treasury Cold'),
    (2,  'Operating Pool'),
    (3,  'Settlement TRX'),
    (4,  'Hot Wallet'),
    (5,  'Compliance Reserve'),
    (6,  'Client Float'),
    (7,  'Reserve Vault'),
    (8,  'Tax Account')
  ) AS labels(id, label)
 WHERE wallets.id = labels.id
   AND (wallets.label IS NULL OR wallets.label = '')
   AND wallets.organization_id = '123e4567-e89b-12d3-a456-426614174000'::uuid;

-- Demo Broker KG wallets (3 moved over by migration 013)
UPDATE wallets SET label = labels.label
  FROM (VALUES
    (9,  'Trading Pool'),
    (10, 'Margin Account'),
    (11, 'Broker Settlement')
  ) AS labels(id, label)
 WHERE wallets.id = labels.id
   AND (wallets.label IS NULL OR wallets.label = '')
   AND wallets.organization_id = '234e5678-e89b-12d3-a456-426614174111'::uuid;

DO $$
DECLARE
    labelled int;
    unlabelled int;
BEGIN
    SELECT COUNT(*) INTO labelled FROM wallets WHERE label IS NOT NULL AND label <> '';
    SELECT COUNT(*) INTO unlabelled FROM wallets WHERE label IS NULL OR label = '';
    RAISE NOTICE 'Migration 014 done — labelled=%, unlabelled=%', labelled, unlabelled;
END $$;

COMMIT;
