-- Migration 019: re-price subscription plans to the 4-tier USD model
-- Date: 2026-04-27
-- Purpose: replace the legacy 3-tier KGS plans (Start / Business / Enterprise)
--          with the 4-tier USD model used on the public pricing page
--          (Starter / Basic / Pro / Enterprise). Slugs change too —
--          frontend already fetches by slug so the pricing UI lights up
--          immediately after this migration runs.
--
-- Idempotent. Reversible via the explicit DELETE-then-INSERT pattern.

BEGIN;

-- Wipe legacy rows so slugs and sort_order match the new mapping.
-- Production safety: only delete plans that are NOT referenced by any
-- active subscription. If somebody is on `start` we keep the row and let
-- ops re-target them manually.
DELETE FROM subscription_plans
 WHERE slug IN ('start', 'business', 'free', 'pro_legacy')
   AND id NOT IN (SELECT DISTINCT plan_id FROM organization_subscriptions WHERE plan_id IS NOT NULL);

-- Upsert the new tiers. ON CONFLICT updates everything so re-running this
-- migration after editing prices keeps the new values.
INSERT INTO subscription_plans
  (name, slug, description, monthly_price, yearly_price, currency, margin_min, features, sort_order, is_active)
VALUES
  ('Starter', 'starter',
   'Для пилотов и небольших обменников. Один блокчейн, ограниченная команда.',
   60, 600, 'USD', NULL,
   '{"all_interfaces": true, "max_wallets": 100, "max_team_members": 1, "max_blockchains": 1, "support_24h": true}'::jsonb,
   1, TRUE),

  ('Basic', 'basic',
   'Для растущих обменников. Несколько сетей, командная работа.',
   600, 6000, 'USD', NULL,
   '{"all_interfaces": true, "max_wallets": 10000, "max_team_members": 3, "max_blockchains": 3, "support_24h": true}'::jsonb,
   2, TRUE),

  ('Pro', 'pro',
   'Для активных бирж. Все сети, расширенная команда.',
   2500, 25000, 'USD', NULL,
   '{"all_interfaces": true, "max_wallets": 50000, "max_team_members": 5, "all_blockchains": true, "support_24h": true}'::jsonb,
   3, TRUE),

  ('Enterprise', 'enterprise',
   'Для банков и крупных площадок. Без лимитов, выделенная поддержка.',
   0, 0, 'USD', NULL,
   '{"all_interfaces": true, "unlimited_wallets": true, "unlimited_team_members": true, "all_blockchains": true, "support_1h": true, "custom_pricing": true}'::jsonb,
   4, TRUE)
ON CONFLICT (slug) DO UPDATE
SET name           = EXCLUDED.name,
    description    = EXCLUDED.description,
    monthly_price  = EXCLUDED.monthly_price,
    yearly_price   = EXCLUDED.yearly_price,
    currency       = EXCLUDED.currency,
    margin_min     = EXCLUDED.margin_min,
    features       = EXCLUDED.features,
    sort_order     = EXCLUDED.sort_order,
    is_active      = EXCLUDED.is_active,
    updated_at     = NOW();

COMMIT;
