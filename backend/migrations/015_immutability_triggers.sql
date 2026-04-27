-- Migration 015: Immutability triggers for audit_log and signature_history
-- Date: 2026-04-27
-- Purpose: Forensic-grade audit. Once a row is written it cannot be altered or
--          deleted, even by the application. Compliance requirement (FATF
--          Travel Rule, internal anti-fraud).
--
-- Idempotent: triggers use CREATE OR REPLACE; existing rows are not affected.
-- Reversible (if needed): DROP TRIGGER orgon_immutable_* ON <table>;

BEGIN;

-- ============================================================
-- Reusable function — raises on any UPDATE / DELETE
-- ============================================================
CREATE OR REPLACE FUNCTION orgon_block_update_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Table %.% is append-only — UPDATE is not allowed.',
            TG_TABLE_SCHEMA, TG_TABLE_NAME;
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Table %.% is append-only — DELETE is not allowed.',
            TG_TABLE_SCHEMA, TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- audit_log
-- ============================================================
DROP TRIGGER IF EXISTS orgon_immutable_audit_log ON audit_log;
CREATE TRIGGER orgon_immutable_audit_log
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW
    EXECUTE FUNCTION orgon_block_update_delete();

-- ============================================================
-- signature_history
-- ============================================================
DROP TRIGGER IF EXISTS orgon_immutable_signature_history ON signature_history;
CREATE TRIGGER orgon_immutable_signature_history
    BEFORE UPDATE OR DELETE ON signature_history
    FOR EACH ROW
    EXECUTE FUNCTION orgon_block_update_delete();

-- ============================================================
-- Verification
-- ============================================================
DO $$
DECLARE
    audit_trig int;
    sig_trig int;
BEGIN
    SELECT COUNT(*) INTO audit_trig FROM pg_trigger
     WHERE tgname = 'orgon_immutable_audit_log';
    SELECT COUNT(*) INTO sig_trig FROM pg_trigger
     WHERE tgname = 'orgon_immutable_signature_history';
    RAISE NOTICE 'Migration 015 done — audit_log trigger=%, signature_history trigger=%',
        audit_trig, sig_trig;
END $$;

COMMIT;
