-- Migration 018: replay protection for multi-sig actions
-- Date: 2026-04-27
-- Purpose: At present nothing stops a signer from being recorded twice on
--          the same transaction. Two ways this happens in practice:
--          (a) idempotency-key retry where the client doesn't realize the
--              first call succeeded — same signer ends up with two `signed`
--              rows on one tx and the count is wrong;
--          (b) replay of a captured request — same effect, plus integrity
--              risk on the audit trail.
--
--          We add a UNIQUE INDEX on (tx_unid, signer_address, action) so
--          PostgreSQL rejects the duplicate INSERT. The application layer
--          translates the IntegrityError into a 409 Conflict.
--
--          We also clean any pre-existing duplicate rows (rare, demo data)
--          so the index can be created.
--
-- Idempotent. Safe to re-run.

BEGIN;

-- 1. Drop duplicate (tx_unid, signer_address, action) rows, keeping the
--    earliest one (lowest id).
WITH dups AS (
    SELECT id,
           ROW_NUMBER() OVER (
               PARTITION BY tx_unid, signer_address, action
               ORDER BY id
           ) AS rn
      FROM signature_history
     WHERE signer_address IS NOT NULL
)
DELETE FROM signature_history
 WHERE id IN (SELECT id FROM dups WHERE rn > 1);

-- 2. Now create the unique index — partial: NULL signer_address rows
--    (system events, very early demo data) are not constrained.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_sig_history_tx_signer_action
    ON signature_history(tx_unid, signer_address, action)
    WHERE signer_address IS NOT NULL;

COMMENT ON INDEX uniq_sig_history_tx_signer_action IS
    'Replay/double-sign guard: one row per (tx_unid, signer, action). NULL signer rows are exempt.';

COMMIT;
