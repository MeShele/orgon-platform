-- Migration 024 — wire Stripe webhook events back to organization_subscriptions.
--
-- The webhook receiver in routes_billing needs to look up existing rows by
-- the Stripe-side identifiers (customer + subscription) so that
-- subscription.updated / .deleted / invoice.payment_failed can mirror state
-- back into our DB. Until now no such columns existed, so the webhook was a
-- no-op logger.
--
-- Also: relax the status CHECK constraint so we can persist `past_due`,
-- which is a Stripe lifecycle state we want to surface to operators.
--
-- Idempotent (IF NOT EXISTS / DO blocks) — safe to re-run.

BEGIN;

ALTER TABLE organization_subscriptions
    ADD COLUMN IF NOT EXISTS stripe_customer_id     TEXT,
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS stripe_session_id      TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_org_subs_stripe_sub
    ON organization_subscriptions(stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_org_subs_stripe_customer
    ON organization_subscriptions(stripe_customer_id)
    WHERE stripe_customer_id IS NOT NULL;

-- Relax the status CHECK to also allow `past_due` (invoice.payment_failed)
-- and `trialing` (Stripe trials) — without dropping the guard entirely.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'org_subscriptions_valid_status'
           AND conrelid = 'organization_subscriptions'::regclass
    ) THEN
        ALTER TABLE organization_subscriptions
            DROP CONSTRAINT org_subscriptions_valid_status;
    END IF;
    ALTER TABLE organization_subscriptions
        ADD CONSTRAINT org_subscriptions_valid_status
        CHECK (status IN ('active', 'trialing', 'past_due',
                          'suspended', 'cancelled', 'expired', 'pending'));
END $$;

COMMIT;
