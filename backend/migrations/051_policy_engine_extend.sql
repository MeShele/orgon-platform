-- 051_policy_engine_extend.sql
--
-- Extend the in-house rule engine (Wave 23) to dfns-grade Policy
-- semantics — WITHOUT creating a parallel `policies` table.
--
-- Why no new table:
--   The current `transaction_monitoring_rules` already carries
--   (organization_id, rule_type, rule_config jsonb, action, severity,
--   is_active). Forking into a new schema would require either:
--     (a) a `policies` view → INSERT/UPDATE would break the existing
--         CRUD in compliance_service.py until we wrote INSTEAD-OF
--         triggers, OR
--     (b) a hard cut-over where we migrate rows and ship the new
--         service code in lock-step.
--   Neither is worth the risk for what is really a small column add.
--
-- What changes:
--   * `scope jsonb` — restricts a rule to a subset of the org's
--     traffic. NULL or `'{}'` means "applies to every tx in the org"
--     (current behaviour). Recognised keys:
--         wallet_ids: array of wallet UUIDs the rule applies to
--         networks:   array of network ids the rule applies to
--     Unknown keys are tolerated (forward-compat).
--
-- App-layer changes (not enforced by the DB):
--   * SUPPORTED_RULE_TYPES gains `velocity_amount_usd`,
--     `recipient_whitelist`, `recipient_geo_block`, `time_window`.
--   * SUPPORTED_RULE_ACTIONS gains `request_approval`.
--   No CHECK constraint — the column type is text, app validates.
--
-- Idempotent.

ALTER TABLE public.transaction_monitoring_rules
    ADD COLUMN IF NOT EXISTS scope jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Partial GIN — only meaningful rows. Most rules will leave scope at
-- '{}' (= empty object); the GIN index size therefore stays small.
CREATE INDEX IF NOT EXISTS idx_transaction_monitoring_rules_scope
    ON public.transaction_monitoring_rules USING gin (scope)
    WHERE scope <> '{}'::jsonb;

COMMENT ON COLUMN public.transaction_monitoring_rules.scope IS
    'Optional restriction on which transactions a rule evaluates. Recognised keys: wallet_ids (uuid[]), networks (int[]). Empty object = no restriction (current default).';

INSERT INTO public.schema_migrations (version, description)
VALUES ('051_policy_engine_extend',
        'transaction_monitoring_rules.scope jsonb (per-wallet / per-network rule targeting).')
ON CONFLICT (version) DO NOTHING;
