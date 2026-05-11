-- 031_demo_admin_org_link.sql
--
-- Demo-admin (`demo-admin@orgon.io`) is seeded by `backend/main.py` on
-- boot but has no row in `user_organizations`. As a result:
--   * `/api/organizations` returns `[]` for them
--   * `POST /api/v1/compliance/rules` cannot scope a rule to any org
--     (and currently 500s instead of 403'ing cleanly)
--   * All org-scoped read paths return empty under RLS
--
-- This overlay links demo-admin to the seeded Safina Exchange KG org
-- so the full UI walkthrough works under demo credentials.
--
-- Demo-signer and demo-viewer get linked too — they're created by the
-- same boot-seed and would otherwise have the same dead-end UX.
--
-- Idempotent: ON CONFLICT (user_id, organization_id) — pkey.
-- Safe to re-run: doesn't touch other users or orgs.
-- Only fires if Safina Exchange KG actually exists (seeded). If the
-- org seed was skipped, this migration is a no-op.

DO $$
DECLARE
    safina_org_id uuid := '123e4567-e89b-12d3-a456-426614174000';
    admin_user_id integer;
    signer_user_id integer;
    viewer_user_id integer;
BEGIN
    -- entrypoint.sh's seed_test_organizations.sql is gated by a
    -- "demo-admin user exists?" check that mis-fires when users were
    -- seeded from main.py before the org seed got a chance to run.
    -- Result: in some installs `organizations` ends up empty even
    -- though demo users exist. Create the seed org here too so the
    -- migration is self-sufficient regardless of seed ordering.
    INSERT INTO organizations (id, name, slug, license_type, status, email, country)
    VALUES (
        safina_org_id,
        'Safina Exchange KG',
        'safina-kg',
        'enterprise',
        'active',
        'admin@safina.kg',
        'Kyrgyzstan'
    )
    ON CONFLICT (id) DO NOTHING;

    SELECT id INTO admin_user_id FROM users WHERE email = 'demo-admin@orgon.io';
    SELECT id INTO signer_user_id FROM users WHERE email = 'demo-signer@orgon.io';
    SELECT id INTO viewer_user_id FROM users WHERE email = 'demo-viewer@orgon.io';

    IF admin_user_id IS NOT NULL THEN
        INSERT INTO user_organizations (user_id, organization_id, role)
        VALUES (admin_user_id, safina_org_id, 'admin')
        ON CONFLICT (user_id, organization_id) DO UPDATE
            SET role = EXCLUDED.role;
    END IF;

    IF signer_user_id IS NOT NULL THEN
        INSERT INTO user_organizations (user_id, organization_id, role)
        VALUES (signer_user_id, safina_org_id, 'operator')
        ON CONFLICT (user_id, organization_id) DO UPDATE
            SET role = EXCLUDED.role;
    END IF;

    IF viewer_user_id IS NOT NULL THEN
        INSERT INTO user_organizations (user_id, organization_id, role)
        VALUES (viewer_user_id, safina_org_id, 'viewer')
        ON CONFLICT (user_id, organization_id) DO UPDATE
            SET role = EXCLUDED.role;
    END IF;
END$$;
