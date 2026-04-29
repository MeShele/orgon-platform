# Changelog

All notable changes between the post-redesign v0 and the production-readiness
demo cut. Sprint-by-sprint, oldest first. Format: just-the-facts; lifecycle
intent ("planned", "deferred to Sprint N") is captured here so future
contributors know what was deliberately punted vs. forgotten.

---

## Sprint 1 — auth hardening + audit immutability (2026-04-26)

**Backend security**

- Renamed orphan `RateLimitMiddleware` → `LoginRateLimitMiddleware` and
  actually mounted it. The login rate-limit was effectively off because
  the path was `/api/v1/auth/login` instead of `/api/auth/login`; brute
  force protection now applies (5/min/IP) to `/api/auth/login`,
  `/verify-2fa`, `/reset-password`, `/reset-password/confirm`. Aliased
  the B2B partner-tier limiter as `PartnerRateLimitMiddleware`.
- `routes_scheduled.py`: every endpoint gained an auth dependency.
- `routes_health.py`: `/safina`, `/detailed`, `/services` are now
  admin-only. Plain `/api/health` stays public.
- `routes_documents.py`: `/token`, `/supported-formats` require any auth.
- `routes_networks.py`: `POST /cache/refresh` is admin-only.
- `routes_monitoring.py`: `/health` and `/metrics` are admin-only.
- `routes_auth.py:415`: removed `print(reset_token)` to stdout. Replaced
  with a masked `logger.info("token: %s…%s", token[:4], token[-4:])`.
- `backend/api/middleware.py`: CORS_ORIGINS fallback was `["*"]` in
  development — now an explicit whitelist (`orgon.asystem.kg`,
  `orgon-preview.asystem.kg`, `localhost:3000/3100/3200`). The 500
  exception handler no longer leaks `error: str(exc)` /
  `type: type(exc).__name__`; it returns `{detail, error_id}` only.

**Database**

- New migration `015_immutability_triggers.sql`: BEFORE UPDATE OR DELETE
  triggers on `audit_log` and `signature_history` raising
  `EXCEPTION 'Table %.% is append-only'`. Verified live: an UPDATE on
  `audit_log` fails. Reusable function `orgon_block_update_delete()`.

---

## Sprint 2 — repo cleanup + canonical docs (2026-04-26)

- 150+ files removed from repo root, 121 markdowns archived under
  `docs/archive/2026-Q1-Q2/`. Root ended at 10 files / ~30 KiB of
  canonical docs.
- `.gitignore` rewritten: blocks `*.pid`, `._*`, `*.env` (with
  `.env.example` exemption), `cloudflare-credentials.json`, `docker.env`,
  `claude design/*.zip`, SQLite WAL files, and root-level
  `debug_*.py` / `fix_*.py` / `migrate_*.py` / `test_*.py`.
- README, ARCHITECTURE, DEPLOYMENT, CONTRIBUTING, API rewritten from
  scratch — truthful, with `(planned)` tags on unfinished pieces (RLS,
  replay protection, KYC vendor integration, …). Status table in README.
  DEPLOYMENT got a breakage runbook (Coolify 522, ax41 down, JWT secret
  rotation, etc.).
- Removed orphan code: 5 legacy landing components, 2 disabled compat
  routers (`routes_billing_compat.py`, `routes_compliance_compat.py`)
  and their `include_router` calls.

**Frontend (parallel work)**

- Crimson Ledger v2 design tokens in `globals.css` (`--primary: #9c1825`,
  `--destructive: #1a1a1a` separated from primary, `--surface-contrast`
  light=ink/dark=navy via aliases, `--background: #fafaf7`).
- `@plugin "tailwindcss-animate"` added (Tailwind 4 syntax).
- Magic UI: `Marquee`, `NumberTicker`, `AnimatedBeam` copy-pasted in.
- Motion Primitives: `TextEffect` (split-by-word + blur lift).
- Custom: `MagneticButton` (cursor pull) and `TiltCard` (3D rotateX/Y).
- 8-component landing rebuild: `Hero`, `TrustRow`, `Pillars`, `Numbers`,
  `FlowSection`, `BottomCTA`, `Reveal`, `RevealItem`.
- Two rounds of "drop the dark blocks on light theme" — `(public)/layout`
  no longer hard-codes `bg-slate-950`; `FlowSection` + `BottomCTA` use
  `bg-muted/40` + crimson left rails.
- TypeScript clean (`tsc --noEmit` exit 0) — fixed the errors that
  `ignoreBuildErrors: true` was hiding: removed `eslint` from
  `next.config.ts` (Next 16 dropped it), `Card.tsx` `Omit<…, 'title'>`,
  `Button` gained `danger` and `warning` variants, `Badge` gained
  `green/red/yellow/blue` legacy aliases mapped to the semantic ones,
  `as const` on every `[0.22, 1, 0.36, 1]` ease tuple.

**Demo data**

- `013_demo_data.sql`: idempotent seed — 2 demo orgs, 6
  `user_organizations` links, 11 wallets, 7 transactions, 3
  `signature_history` rows.
- `014_wallet_labels.sql`: human-readable labels for the 11 demo wallets.

---

## Sprint 3 — backend hygiene (2026-04-27, commit `7793462`)

**Route deduplication**

- `routes_auth.py`: dropped `/auth/users`, `/auth/users/{id}`,
  `/auth/roles`, `POST /auth/change-password`. Frontend uses
  `/api/users/*` and `PUT /api/users/me/password` exclusively — verified
  zero callers.
- `routes_compliance.py`: dropped KYC/AML endpoints. Canonical KYC/KYB
  lives at `/api/v1/kyc-kyb/*`; only the unique reports endpoints stay.

**Row-level security**

- New migration `016_fix_rls_policies.sql`: re-creates the six policies
  that `005` failed to install. The original `005` had two SQL bugs:
  extra `)` + double `::uuid` cast on `wallets`, and unterminated
  `current_setting('app.is_super_admin, true)…` strings on the other
  five — none of the policies were ever applied.  
  The new migration uses a `STABLE` SQL helper `orgon_current_org_or_super()`
  and runs `ENABLE` + `FORCE ROW LEVEL SECURITY` on `wallets`,
  `transactions`, `signatures`, `contacts`, `scheduled_transactions`,
  `audit_logs`. A `DO $$ … $$` block at the end raises if any policy is
  missing.

**Partner-org scoping**

- New migration `017_partner_org_link.sql`: `partners.organization_id`
  (nullable) + index, with best-effort backfill from `partners.metadata`.
- `WalletService.count_wallets`, `get_wallet_by_name`,
  `TransactionService.count_transactions`, `get_transaction`,
  `ScheduledTransactionService.list_/get_/cancel_scheduled_transaction`
  now accept `org_ids: list | None`.
- `routes_partner.py` + `routes_partner_scheduled.py`: every list/get/
  cancel call goes through `_partner_org_ids(...)` and passes
  `org_ids=[…]`. Cross-tenant lookups return `404`, not the row.
- Known still-open: `routes_partner_addresses.py` calls
  `AddressBookService.list_addresses/get_address/...` which don't exist
  (the service only has `get_contacts`/`get_contact`); endpoint is
  broken-on-arrival, deferred to a follow-up sprint that introduces
  `address_book_b2b` properly. `routes_partner_analytics.py` partner
  filtering also deferred.

**Multi-sig replay protection**

- New migration `018_signature_replay_protection.sql`: cleanup of any
  pre-existing `(tx_unid, signer, action)` duplicates, then a partial
  UNIQUE index `uniq_sig_history_tx_signer_action` (skips rows where
  `signer_address IS NULL`).
- `SignatureService`: new `DuplicateSignatureError`. Both
  `sign_transaction` and `reject_transaction` look up
  `signature_history` for any prior `(tx_unid, signer, signed|rejected)`
  before the Safina round-trip, and translate `asyncpg.UniqueViolationError`
  to the same exception as a race fallback. Surfaced as `409 Conflict`
  in `routes_partner.py` and `routes_signatures.py`.
- `routes_partner.py`: replaced broken `signature_service.approve_signature`
  / `reject_signature` calls (those methods never existed) with the real
  `sign_transaction` / `reject_transaction` methods.

---

## Sprint 4 — frontend completion (2026-04-27, commit `b41c7be`)

- Crimson Ledger pass over **every** page under `(authenticated)/*`:
  hardcoded `slate-*/gray-*/blue-*/indigo-*/purple-*/amber-*/red-*/green-*`
  swapped for semantic tokens (`primary` / `success` / `warning` /
  `destructive` / `muted` / `foreground` / `border`). Light theme no
  longer leaks dark blocks; dark theme stays consistent without
  redundant `dark:` overrides.
- New `components/ui/Dialog.tsx` — Radix Dialog primitives + Framer
  entrance, paper card with ink border, respects
  `prefers-reduced-motion`.
- `ContactModal` rewritten on top of the new Dialog + the project's
  `Input` / `Button`. Dropped Aceternity's `AnimatedModal`,
  `AnimatedInput`, `MovingBorderButton`.
- New `components/ui/LogoWordmark.tsx`: inline SVG (`currentColor`),
  wired into `PublicFooter`.
- Mobile drawer for the authenticated nav: extracted `SIDEBAR_NAV` +
  `filterByRole` into a shared `sidebar-nav.ts` reused by
  `AceternitySidebar` (desktop) and the new `MobileSidebar` (slide-in
  with scrim + AnimatePresence). The hamburger in `Header` now actually
  opens something on mobile.
- `Input.tsx`: replaced the dead `'eyebrow'` class name (no CSS backed it
  any more) with the equivalent inline classes.

---

## Sprint 5 — CI/CD (2026-04-27, commit `ad112e8`)

- `.github/workflows/ci.yml` — backend job replays every migration in
  order against a `postgres:16` service, then runs the focused unit-test
  set (`test_signature_service`, `test_transaction_service_validation`,
  `test_network_service`, `test_telegram_notifier`). Frontend job runs
  `tsc --noEmit`, `eslint`, `next build`. E2E job runs Playwright
  chromium-only, uploads `playwright-report` as an artifact.
- `.github/workflows/deploy.yml` — `workflow_run` listener; on green CI
  for `main` / `preview-ready`, `curl`s the per-app Coolify deploy hook.
  Branch → environment mapping documented in `CI-CD.md`.
- `frontend/playwright.config.ts` + `e2e/{smoke,auth}.spec.ts`. Smoke
  tests render landing / login / pricing without a backend; auth spec
  is `test.skip()`-gated on `E2E_BACKEND_URL`. `webServer` clause builds
  + serves Next on 3000 when no external URL is provided.
- `frontend/package.json` adds `typecheck`, `test:e2e`, `test:e2e:ui`
  scripts and `@playwright/test` as a devDependency.
- `scripts/backup_pg.sh` — `pg_dump | gzip` with mtime-rotated
  retention, refuses to keep dumps under 4 KiB.
- `CI-CD.md` — required GitHub secrets, branch→env mapping, preview-DB
  separation recipe (currently both prod and preview hit one Coolify
  postgres — runbook to split is in there), backup cron, restore
  commands, off-site rsync, and the failure runbook.

---

## Sprint 6 — doc polish (2026-04-27)

- README status table reflects what's actually wired post-Sprint 5: RLS
  active, partner-org scoping enforced, replay guard live, CI/CD wired,
  backups via repo script.
- `ARCHITECTURE.md` rewritten section on multi-tenancy and multi-sig:
  RLS is no longer "(planned)"; the actual mechanics of `migration 016`,
  the `_partner_org_ids` helper, and the `DuplicateSignatureError` flow
  are documented.
- `DEPLOYMENT.md` — GitHub→Coolify deploy hook is now the default; the
  manual `curl` block stays as the out-of-band fallback. Backup section
  points to `scripts/backup_pg.sh`.
- `API.md` — multi-tenancy section calls out RLS at the DB layer; new
  Multi-signature section documents the 200/409/502 contract on
  `/sign` and `/reject`.
- This file (`CHANGELOG.md`) created.

---

## Wave 7 — prod-readiness push (2026-04-29)

Prompted by: live Safina test endpoint becoming reachable, plus
explicit "we want to ship" direction from product. Net effect — the
project moves from "demo-ready" to "pilot-ready with one onboarded
customer" once we have HSM + prod creds.

### Live Safina verification

- Logged into `pm.kaz.one`, pulled the canonical Safina docs from the
  Wiki of project `safina-api`. Confirmed: base URL
  `https://my.safina.pro/ece/`, auth via four headers
  `x-app-ec-from / -sign-r / -sign-s / -sign-v`, signed string is `"{}"`
  for GET and compact JSON (no whitespace) for POST. Test EC keypair
  in their Examples page.
- Plugged the test private key into `.env`, switched off `SAFINA_STUB`,
  ran the full backend round-trip. **13/13 of our endpoints went green**
  including `POST /api/wallets` (creates a real wallet on Safina test
  account, returns `myUNID`) and the multi-sig flow.
- Found and fixed five real bugs along the way (each was a 500 in
  some path):

  1. **Migration 020** — promote naive `TIMESTAMP` columns to
     `TIMESTAMPTZ` on wallets / transactions / contacts / signatures
     (8 columns). asyncpg refused to bind tz-aware datetimes to naive
     columns and our services uniformly write `datetime.now(timezone.utc)`.
     Idempotent.
  2. **Migration 021** — fill four schema gaps the APScheduler hit
     every minute: `webhook_events` missing `event_id` + `webhook_url`,
     `transactions` missing `synced_at`, no `token_balances` table,
     no `pending_signatures_checked` table.
  3. **`transaction_service.sync_transactions`** — `ON CONFLICT DO
     UPDATE` clause referenced `EXCLUDED.info` and `EXCLUDED.network`
     but neither was in the `INSERT` column list.
  4. **`main.py`** — added `get_database()` export. `RLSMiddleware`
     imported it, the import failed silently on every request and
     RLS session settings were never applied.
  5. **PG functions** — `set_tenant_context()` and `clear_tenant_context()`
     never landed because migration 005 rolled back due to its own
     SQL bugs. **Migration 022** consolidates them, plus
     `partner_webhooks` (had a wrong FK in 009) and `balance_history`.

### Wired but-not-yet integrations

- **Stripe Checkout** (`backend/services/stripe_service.py`) — creates
  a Subscription Checkout Session keyed on `plan_slug` + `billing_cycle`,
  returns the URL for browser redirect. Webhook receiver verifies HMAC
  signature, dispatches to billing_service. Plan→price mapping driven
  by env (`STRIPE_PRICE_STARTER` etc.). Service is *disabled* mode
  when no API key is present — endpoints return 503 cleanly.
- **Stripe success / cancel pages** under `(public)/billing/` so the
  Checkout return URLs land on real ORGON pages, not 404.
- **Email service** (`backend/services/email_service.py`) — three
  templated sends (password reset, email verification, team invite)
  with two backends: SMTP via env config or a file-log fallback for
  dev. Wired into `routes_auth.py:request_password_reset` — the
  endpoint that previously only logged the token now actually emails.
- **HMAC replay protection** (`middleware_b2b` + migration 023) —
  every B2B partner request must carry `X-Nonce` and `X-Timestamp`
  headers. ±5 min drift window, dedup by `(partner_id, nonce)` PK.
  Strict by default; `ORGON_PARTNER_REPLAY_OFF=1` env disables for
  incidents. Verified end-to-end (200 valid → 409 replay → 400 drift).
- **Observability** (`backend/observability.py`) — JSON log formatter
  on `ORGON_JSON_LOGS=1`, Sentry SDK init on `SENTRY_DSN=…`. Both
  off by default — production env flips them on.

### Code hygiene

- Deleted `routes_transactions.py /sign` and `/reject`. They bypassed
  `signature_history` and the Sprint 3 replay-guard — keeping them
  around as "deprecated" was a real security regression risk. Frontend
  has been on `/api/signatures/{tx_unid}/*` since the redesign.
- Disabled `routes_partner_addresses` import in `main.py`. The router
  called `AddressBookService.list_addresses/...` but the service has
  no such methods — the endpoint was 500-on-call-of-any-method. Stays
  out of the registered routes until `address_book_b2b` lands.

---

## Wave 8 — honesty pass (2026-04-29)

After Wave 7 the picture looked good on paper but several pieces were
either silently broken or claiming features that didn't exist.

- **CI honesty.** 36 unit tests had been red since Sprint 5 — they
  fixtured `db = MagicMock()` but the services use asyncpg's
  awaitable interface. Mechanical s/MagicMock/AsyncMock/g fixed 5;
  the remaining 10 broken classes got a `@pytest.mark.skip(reason="…")`
  with explicit "rewrite needed" notes so CI now reports 78 passing,
  33 skipped, 0 failed instead of pretending green over 36 reds.
- **Migration 013 (demo seed).** INSERT referenced `tx_unid`, but the
  app reads `transactions.unid` (the legacy `tx_unid` column is dead
  weight in the legacy chain and doesn't exist at all in the canonical
  UUID schema). Also dropped `amount_decimal/fee/info` (legacy-only)
  and added `to_addr`+`init_ts` so the dashboard activity feed actually
  resolves the demo rows. Verified clean apply against the canonical
  schema.
- **Stripe webhook actually does something.** Replaced the log-only
  stub with real dispatch:
  - `checkout.session.completed` → `BillingService.upsert_subscription_from_checkout`
    (UPSERT keyed on `stripe_subscription_id`, status=`active`).
  - `customer.subscription.updated/deleted` → mirror Stripe lifecycle
    state into local status (active / trialing / past_due / cancelled
    / suspended / pending / expired).
  - `invoice.payment_failed` → flip to `past_due`.
  Added migration 024 with `stripe_customer_id` / `_subscription_id`
  / `_session_id` columns (unique partial index on subscription_id),
  and relaxed the status CHECK constraint to admit `past_due` and
  `trialing`. Failures inside the handler are logged and acked (not
  5xx'd) so Stripe doesn't retry-storm. 8 unit tests cover dispatch.
- **`/settings` API-keys tab.** Stopped lying — removed the "в
  разработке" disabled button and the mock-data list, replaced with
  honest copy: partner API keys are an admin function via
  `/api/v1/admin/partners`, regular users contact support.
- **`webhook_service._get_partner_secret` query.** Was OR-ing in a
  fallback against `partners.api_secret` (column doesn't exist; we
  store `api_secret_hash`) and on `WHERE partner_id = $1` (the PK is
  `id`). Both were silent no-ops since Sprint 0. Dropped the fallback,
  kept the `partner_webhooks.secret` lookup. Added a docstring
  explaining why the fallback was wrong.
- **`DEPLOYMENT.md` got a "Required environment variables" section.**
  Lists `JWT_SECRET_KEY` (don't rely on the auto-fallback —
  every restart kicks all users to login), `STRIPE_*`, `SAFINA_*`,
  `SMTP_*`, etc., with required-vs-optional split.
- Trimmed an unused `EmailStr` import from `routes_admin_partners.py`.

---

## Wave 11 — migration consolidation (2026-04-29)

Cleared the multi-year accumulation of mutually-conflicting migration
files into a single canonical snapshot. Triggered by an audit ahead of
a planned greenfield deploy on a new Coolify server: the legacy chain
had silent failures masked by `ON_ERROR_STOP=0` for so long that fresh
installs were getting only ~50% of the intended schema, but tests stayed
green because they used AsyncMock instead of a real DB.

### What was wrong

- **Two migration directories applied in sequence by CI**:
  `backend/database/migrations/` (legacy, 18 files) and
  `backend/migrations/` (overlay, 25 files), with `ON_ERROR_STOP=0`
  swallowing every error.
- **Two mutually-exclusive `000_*.sql`** in overlay (`000_base_schema`
  and `000_init_uuid_base`); CI explicitly skipped both via
  `grep -vE '/000_'`. Neither created `organizations` table that
  legacy `001_wallets_transactions` FK'd into.
- **Three `006_*.sql` billing files** (`006_billing_system.sql`,
  `_rls_fix.sql`, `_create_billing_tables.sql`) creating overlapping
  tables — no clear "the canonical one".
- **Wrong column FK**: legacy `009_webhooks.sql` referenced
  `partners(partner_id)` but the actual column is `partners(id)`.
  Three webhook tables were silently failing to create. Migration
  022 patched `partner_webhooks` correctly; the others stayed broken.
- **Schema column drift**: `transactions.tx_unid` (legacy) +
  `transactions.unid` (added by `003b`) both existing on the legacy
  chain, only `unid` on the UUID chain. App reads `unid`. Demo seed
  013 was inserting into `tx_unid` until Wave 10.

### What was done

- **`backend/migrations/000_canonical_schema.sql`** — single source of
  truth. Generated via `pg_dump --schema-only --no-owner --no-acl
  --no-tablespaces` from local-dev DB (which had every Wave 1-10
  migration applied and is verified working with current backend
  code). 60 tables, 15 functions, 36 triggers, 7 RLS policies, 311
  indexes. NOT idempotent (pg_dump emits bare CREATEs); applied once
  on a virgin DB, gated by the `schema_migrations` marker row at the
  bottom.
- **`schema_migrations` tracking table.** Inserted at the bottom of
  the canonical with `version='000_canonical_schema'`. Future
  overlays (`025_*` onwards) MUST insert their own row with
  `ON CONFLICT DO NOTHING`. CI, `entrypoint.sh`, and
  `/api/health/run-migrations` all key off this table to skip
  already-applied migrations.
- **All historical files moved** to `backend/migrations/_historical/`:
  `overlay/` (28 files + 4 helper scripts) and `legacy_db_migrations/`
  (18 files). README in each explains why they're archived and
  warns against running them.
- **CI workflow rewritten** (`.github/workflows/ci.yml`):
  `ON_ERROR_STOP=1` (real failures surface), apply only canonical +
  any 025+ overlays, verify the marker row landed. New
  `fresh-install` job: clean Postgres → apply canonical → boot
  uvicorn → assert `/api/health` answers within 30s.
- **`entrypoint.sh`** gained an opt-in `ORGON_AUTO_MIGRATE=1` mode.
  When set, container reads `DATABASE_URL`, checks for the canonical
  marker, applies `000_canonical_schema.sql` on a virgin DB, then
  applies any post-canonical overlays. Safe to leave on across
  restarts. Designed for greenfield Coolify deploy on the new server.
- **`POST /api/health/run-migrations`** rewritten to match the same
  flow (super_admin only). Previously scanned both legacy and overlay
  dirs without filtering and tried to swallow `already exists`
  errors heuristically; now keys off the marker row.
- **Email service consolidation.** `backend/email_service.py` (Wave 0
  legacy with HTML templates) merged into
  `backend/services/email_service.py` (Wave 7 typed entry points).
  One `EmailService` class, both APIs (`send_password_reset` /
  `send_template`). `EMAIL_TEMPLATES` dict carries the 5 HTML
  templates used by `NotificationService`. Module-level
  `email_service` global preserved via `__getattr__` for legacy
  imports.
- **`DEPLOYMENT.md`** updated: new "Apply a database migration"
  section describing greenfield path, manual path, and adding new
  migrations. Added `ORGON_AUTO_MIGRATE` to the env vars table.

### Verification

- 86 unit tests passed, 33 skipped (no new regressions). The 33
  skipped are pre-existing MagicMock-vs-AsyncMock infrastructure
  debt unrelated to schema.
- Canonical applied to fresh Postgres → 60 tables, 311 indexes, 36
  triggers, 7 policies, marker row landed. `pg_dump` of the result
  diffs only by cosmetic CHECK constraint rewriting (Postgres
  internally normalizes `(ARRAY[...])::text[]` ↔ `ARRAY[(...)::text]`,
  semantically identical).
- Backend `compileall` clean, frontend `tsc --noEmit` clean.

### Why this matters for prod-readiness

The new server can now deploy in one of two ways:

1. **Greenfield (recommended)**: `ORGON_AUTO_MIGRATE=1` in Coolify env
   → container applies the canonical on first boot. Zero manual
   migration steps.
2. **Manual**: `psql -f 000_canonical_schema.sql`, done.

Future schema changes are single idempotent files (`025_*.sql`),
applied automatically by the same entrypoint or via the admin endpoint.
No more silent "half the schema didn't apply" failures.

---

## Wave 12–15 — production-readiness pack (2026-04-29)

Closes the four highest-leverage items from "Known follow-ups" so the
new Coolify server can pick up institutional-grade primitives from
day one rather than retrofitting them later.

### Wave 12 — HSM-ready signer abstraction

- New `backend/safina/signer_backends.py` with a `SignerBackend`
  protocol and three implementations:
  * `EnvSignerBackend` — current behaviour (key in env, in-process).
    Acceptable for dev/preview/single-org pilots; **unacceptable for
    institutional custody**.
  * `KMSSignerBackend` — AWS KMS asymmetric SECP256K1 key stub.
    Raises `NotImplementedError` with a 6-step wiring checklist.
  * `VaultSignerBackend` — HashiCorp Vault Transit engine stub.
    Raises with a 5-step wiring checklist.
- `SafinaSigner` now accepts either a hex private key (legacy
  convenience) OR a `backend=...` kwarg. Internal `_eth_sign` delegates
  to `backend.sign_msg_hash`, so a KMS/Vault swap is one line.
- `build_signer_backend()` selector keys off `ORGON_SIGNER_BACKEND`
  env (`env` / `kms` / `vault`); main.py wired to use it. Signer
  failure on boot falls back to stub mode rather than crashing.
- 19 unit tests cover round-trip, env switching, stub stubs raising,
  legacy hex constructor compatibility.

### Wave 13 — Local Safina signature verification primitive

- New `backend/safina/signature_verifier.py` with:
  * `recover_signer_address(msg_hash, signature_hex)` — pure ECDSA
    recovery, no canonical-payload assumptions.
  * `verify_signer(msg_hash, signature_hex, expected_address)` —
    recover + compare, case-insensitive, never raises.
  * `eth_personal_sign_hash(msg)` — same prefix our SafinaSigner
    uses; also matches MetaMask `personal_sign`.
- High-level `verify_safina_tx_signer(...)` is wired but the
  canonical payload format is **explicitly NOT confirmed** — the
  module's `canonical_payload()` raises `NotImplementedError` until
  the exact field order/encoding is verified against Safina docs.
  `is_verification_enabled()` probes this gate so accidentally
  setting `ORGON_VERIFY_SAFINA_SIGS=1` without wiring the payload
  doesn't silently turn on broken verification.
- 14 unit tests cover round-trip with known-good signatures
  (generated via SafinaSigner+TEST_KEY), tamper detection, malformed
  inputs, the gate, and the disabled-mode return path.

### Wave 14 — Off-site PG backup

- `scripts/backup_pg.sh` extended with optional S3-compatible upload
  (works with AWS S3, Cloudflare R2, Wasabi, MinIO).
  Off-site activated by `ORGON_BACKUP_S3_BUCKET`; size-verified via
  `aws s3api head-object`. Local-only behaviour preserved when env
  is unset.
- DEPLOYMENT.md "Backups" section rewritten with R2 setup snippet,
  systemd timer template, and explicit retention guidance ("manage
  off-site retention via lifecycle rules in the bucket — don't let
  one host compromise wipe history").

### Wave 15 — Rewrite 33 skipped tests

- 10 test classes that had been carrying
  `@pytest.mark.skip(reason="legacy MagicMock-style mocks")` since
  Sprint 5: now green and unmocked. Mechanical changes:
  * `db.fetchone` → `db.fetchrow` (asyncpg style)
  * `db.fetchall` → `db.fetch`
  * `MagicMock` for `db.fetch` → `AsyncMock`
  * SQLite `?` placeholders → Postgres `$N`
  * Two non-async tests promoted to `@pytest.mark.asyncio` because
    the underlying methods became `async`.
- **Real bug fixed in passing.** `signature_service.check_new_pending_signatures`
  was emitting events with `pending.ecaddress`, `pending.value`,
  `pending.min_sign`, `pending.signed` — none of those exist on the
  `PendingSignature` model. The whole code path was silently caught
  by `except Exception` and returning `[]`. Updated the event
  payload to use only fields the model actually carries
  (`token / to_addr / tx_value / init_ts / unid`) plus the signer
  address from the client. Now the background "new pending sig"
  Telegram path actually fires.
- CI suite: **152 passed, 0 skipped, 0 failed** (was 86 passed, 33
  skipped). Real coverage of NetworkService cache logic, signature
  flow, transaction filtering — none of that was being exercised
  before.

---

## Known follow-ups (not in any sprint above)

These remain genuine gaps. Order is "product impact, descending".

- **HSM / KMS wire-up for signer key.** Wave 12 abstraction is in;
  `EnvSignerBackend` runs in process today. To switch to AWS KMS or
  Vault: implement the two stub classes per their wiring checklists in
  `backend/safina/signer_backends.py` (~200 lines each, mostly
  boto3/hvac plumbing + v-recovery). No app-side changes required.
- **Confirm Safina canonical sign-payload format.** Wave 13 verifier
  primitive is in but `canonical_payload()` raises until the exact
  byte format is confirmed against Safina docs. One-line unblocking
  + flip `ORGON_VERIFY_SAFINA_SIGS=1` to activate.
- **Real Stripe price IDs.** Service is wired but
  `STRIPE_PRICE_STARTER` / `_BASIC` / `_PRO` env vars are empty until
  someone provisions products in Stripe and sets them.
- **Real SMTP creds.** Email service runs in file-log mode in dev; on
  prod set `SMTP_HOST` etc. or wire SES.
- **AML rule engine.** `aml_alerts` table is a CRUD shell, no
  detector. Compliance checklist won't close without it. Plan: either
  Sumsub / Chainalysis integration or in-house rules (sanction lists,
  threshold breaches, repeat-address signal).
- **Document upload to S3 / R2.** `/compliance/{kyc,kyb}` show a
  banner sending users to email; backend is `placeholder://`.
- **Preview DB separation.** Preview still shares the prod Coolify
  postgres container — recipe in `CI-CD.md`. (Mooted by the planned
  greenfield Coolify deploy on a new server — fresh DB per env.)
- **Address-book B2B model.** `routes_partner_addresses.py` is
  disabled in `main.py`; lands when `address_book_b2b` table + service
  methods are written.
- **Partner analytics filtering.** `AnalyticsService` needs a
  `partner_id` axis for the partner endpoints.
- **i18n KY parity.** Landing and compliance keys still missing.

### Resolved by waves above

- ~~**Backup off-site mirror.**~~ Wave 14 — `scripts/backup_pg.sh`
  now does S3-compatible upload. Activate by setting
  `ORGON_BACKUP_S3_BUCKET` + AWS creds.
- ~~**Local canonical-payload signature verification primitives.**~~
  Wave 13 — recovery + verify functions ready; only the canonical
  payload byte format is left to confirm.
- ~~**Signer key abstraction.**~~ Wave 12 — `SignerBackend` interface
  with KMS/Vault stubs.
