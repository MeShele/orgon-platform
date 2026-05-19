-- 052_backfill_schema_migrations.sql
--
-- One-off backfill of `schema_migrations` markers for overlay
-- migrations 027–046, which were applied to production but never
-- recorded their own row in `schema_migrations`. See TD-8 in
-- docs/TECH_DEBT.md.
--
-- Why this matters: the `entrypoint.sh` overlay loader re-applies
-- every `0*.sql` file in the migrations directory on every boot
-- if `ORGON_AUTO_MIGRATE=1`. That's fine while all overlays remain
-- idempotent, but it eats CPU on every cold start and — more
-- importantly — masks the difference between "applied" and "needs
-- to apply". Without markers, a future non-idempotent overlay
-- would either re-run dangerously or quietly skip when it
-- shouldn't.
--
-- This file inserts markers ONLY. It does not re-execute the
-- underlying DDL. Each ON CONFLICT clause makes the operation
-- safe to re-run.
--
-- Going forward, every new overlay (e.g. 047_…sql onward) inserts
-- its own marker as the final statement (the canonical pattern).
-- This file just catches the legacy backlog.
--
-- Idempotent.

INSERT INTO public.schema_migrations (version, description) VALUES
    ('027_aml_alerts_indexes',          'AML alerts table indexes (status, severity, org_id).'),
    ('028_transactions_signer_mismatch','Wave 13 signature-verifier hooks: transactions.signer_mismatch_at / sig_canonical_variant.'),
    ('029_transactions_on_hold',        'Wave 23 rule engine: transactions.status can be on_hold; release-from-hold UX (Wave 26).'),
    ('030_sar_submissions',             'Wave 24 SAR pipeline: sar_submissions table + backend dispatch enum.'),
    ('031_demo_admin_org_link',         'Link demo-admin/signer/viewer users to seeded Safina Exchange KG org.'),
    ('032_webhook_events_delivered_at', 'Legacy webhook_events table — delivered_at column for retry-vs-final state.'),
    ('033_drop_non_safina_tables',      'Drop legacy /api/v1/partner/* family: partners, partner_*, fiat_*, billing_*.'),
    ('034_drop_audit_log_b2b',          'Drop parallel audit_log_b2b table — AuditService now writes single audit_log.'),
    ('035_wallet_tenant_backfill',      'wallets.organization_id backfill from owner-mapping; required for RLS.'),
    ('036_org_safina_ec_key',           'organizations.safina_ec_private_key column for per-org headless Safina EC.'),
    ('037_drop_tx_hash_unique',         'Drop UNIQUE on transactions.tx_hash — allows replays / refunds with same hash.'),
    ('038_purge_pending_wallets',       'Wave 28 housekeeping: clear stuck pending wallets older than 7 days.'),
    ('039_wallet_hidden_tombstone',     'wallets.is_hidden column. Original 039 bulk-tombstone UPDATE retired in commit ad7678a.'),
    ('040_asystem_wallet_state_repair', 'Repair: wallet activation flags after Safina headless model rollout.'),
    ('041_b2b_merchant_foundation',     'B2B platform schema: merchant_api_keys, merchant_request_nonces, end_users, wallets.purpose, webhook_deliveries, merchant_usage_daily.'),
    ('042_merchant_api_key_encryption', 'merchant_api_keys.secret_encrypted (pgcrypto) for at-rest HMAC secret recovery.'),
    ('043_deposits_table',              'deposits table for the multi-chain watcher (UNIQUE on network, tx_hash, log_index).'),
    ('044_deposit_watcher_trc20',       'deposit_watch_cursors: last_seen_ts_native/tokens split; tron module hookup.'),
    ('045_deposit_cursor_rename',       'Rename deposit cursor column for consistency with deposit_sources module shape.'),
    ('046_invoices',                    'Monthly invoice ledger: invoices + invoice_line_items, currency/amount/items frozen.')
ON CONFLICT (version) DO NOTHING;

-- Finally, this file's own marker.
INSERT INTO public.schema_migrations (version, description)
VALUES ('052_backfill_schema_migrations',
        'One-off backfill of markers for legacy overlays 027–046 (TD-8).')
ON CONFLICT (version) DO NOTHING;
