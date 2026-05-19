# ORGON

**B2B custodial wallet platform for crypto exchangers, brokers, banks
and fintech companies.**

Operational layer between wallet and blockchain. Two surfaces:

* **`/api/*`** — JWT-bearer dashboard for ORGON operators (signers,
  admins, compliance). M-of-N signing policies, KYC/KYB/AML, append-
  only audit log, multi-tenant org dashboard.
* **`/v1/*`** — HMAC-signed B2B API for external integrators. Merchants
  onboard end-users, get per-network deposit addresses, receive
  webhook notifications on inbound transfers, send outbound
  transactions. SDKs in TypeScript and Python; sample apps included.

```
prod        https://orgon.asystem.ai
support     support@orgon.asystem.kg
api docs    /api/docs   (Swagger)
            /api/redoc
            /api/openapi.json
            /developers (guided onramp for integrators)
```

---

## Status

| Layer | What's wired | What's not yet |
|---|---|---|
| B2B Merchant Platform | `/v1/*` HMAC-signed surface — end-users, lazy wallets (per-network on demand), transactions (send+sign), deposits (multi-chain watcher: Tron + TRC20, BTC via Esplora, ETH + ERC20 via Etherscan / Sepolia), webhooks (publish + delivery worker, **retry v1 default `30s→6h`, retry v2 opt-in `1m→24h`, X-ORGON-Webhook-Event-Id for exactly-once, 90-day retention sweep**), usage counters → daily plan quota (429), monthly invoice generator (cron 02:00 UTC, catch-up safe). **Optional `X-ORGON-Idempotency-Key` header on every mutating call — 24h response replay keyed by `(merchant_id, idem_key)`, dfns-style drift-tolerant.** Pgcrypto-encrypted API secrets (`MERCHANT_KEY_MASTER`), 300/min/IP edge guard, replay-nonces, sandbox isolation. Standardized error envelope `{error, message, request_id, details?}` with `X-Request-Id` on every response, **request-id threaded through `webhook_deliveries.originating_request_id` and `signature_history.request_id`**. Prometheus counters per `(merchant_id, endpoint, status)`. `/v1/health/extended` exposes queue lag + watcher status | ORGON-chain (5800/5810) watcher pending Safina's explorer API; npm publish for `@orgon/sdk` under the @orgon scope; PyPI publish for `orgon-sdk`; payment processor integration for invoice payments |
| SDKs | `@orgon/sdk` (TS, Node ≥ 18) + `orgon-sdk` (Python ≥ 3.10) — same resource layout in both. Static `WebhooksAPI.verify` / `verify_webhook` for inbound event verification. Sample apps under `sdks/typescript/examples/` (`payment-receiver` Express server, `payout-sender` CLI). CI publish workflow (`.github/workflows/sdk-publish.yml`) triggers on `sdk-v*` git tag → npm publish with provenance. Backend signature-drift tests pin the HMAC message layout so a SDK<->server mismatch fails CI not integrators | published packages on npm/PyPI; full async variant of Python SDK |
| Auth | JWT + refresh + 2FA-ready, role hierarchy with legacy mapping; cookie+localStorage drift detection on mount; rate-limit on auth (5/min/IP) | webhook-based JWT rotation |
| Multi-tenancy | service-layer tenant context (`set_tenant_context()` PG function) **and** Postgres RLS on `wallets / transactions / signatures / contacts / scheduled_transactions / audit_log`; super_admin bypass via `orgon_current_org_or_super()` | each environment gets its own Postgres on the new deploy (no shared instance) |
| Multi-signature | thresholds and signing flow live in Safina; ORGON records each step in `signature_history` (append-only via DB trigger); replay/double-sign blocked at the application layer + UNIQUE index on `(tx_unid, signer_address, action)`; **read + wallet create + transaction submission live-verified against `https://my.safina.pro/ece/`** (Safina accepts new wallets and queues transactions in pending state); HSM-ready signer abstraction (`SignerBackend` protocol with `Env` / `KMS` / `Vault` implementations); **local signature-verification primitive** (`recover_signer_address` + `verify_signer`) with 6 candidate canonical variants ready, gated on `ORGON_SAFINA_VERIFY_MODE=shadow|enforce` once Safina-side canonical-payload format is confirmed via a sample signed-tx | **`POST /tx_sign` returns 200 OK but Safina silently does not register the signature** in its multi-sig state machine (open question to Safina — see `docs/SESSION_2026-05-11_FIRE_TEST_FINDINGS.md`); end-to-end multi-sig sign + broadcast not yet verified live; KMS-backend not yet exercised against real AWS (only against in-process fake-KMS in unit tests); Vault backend stays a stub |
| Compliance | KYC/KYB submission (Sumsub-WebSDK based, Wave 19+20) + admin review queue (canonical at `/api/v1/kyc-kyb/*`); AML alert table; in-house transaction rule engine — `threshold | velocity | blacklist_address` (Wave 23) + **`velocity_amount_usd | recipient_whitelist | time_window` plus `recipient_geo_block` stub (Wave 29)**, actions `alert | hold | block | request_approval` (Wave 29), **per-rule `scope` for wallet / network targeting (Wave 29)**, `policy.triggered` webhook on non-alert hits; admin UI for rules at `/compliance/rules` (Wave 25); release-from-hold button in AML drawer (Wave 26); SAR submission pipeline with `manual_export | email | api_v1 | dryrun` backends (Wave 24) | Sumsub pre-launch until 3 env vars supplied (clean 503 in the meantime); Chainalysis integration; document upload to S3/R2; full approval-engine for `request_approval` action (Phase 2, E-08) |
| Audit log | append-only via DB trigger (UPDATE/DELETE blocked); **`GET /api/audit/events` with keyset pagination + `GET /api/audit/events.csv` streaming export (Wave 29)** | retention policy + cold storage; multi-tenant isolation by RBAC only — `audit_log.organization_id` backfill blocked by append-only trigger (see `docs/TECH_DEBT.md`) |
| Frontend | Crimson Ledger v2 design — every page under `(authenticated)/*` and every public landing page now uses semantic tokens; mobile drawer; inline `LogoWordmark`; shadcn-style Dialog primitives in Contacts; pricing matches dfns 4-tier USD model; `/settings` API-keys tab tells the truth about admin-only key provisioning | — |
| Platform admin | `/admin/merchants` dashboard — onboard, edit settings (kind / plan / sandbox / webhook URL), suspend/resume, issue / revoke API keys with one-time-reveal modal, view per-merchant usage (today's counters + 30-day chart) + invoices (mark paid back-office). Sidebar entry RBAC-gated to super_admin / platform_admin / admin. The legacy `/api/v1/partner/*` and `/api/v1/admin/partners` families were removed in migration 033 in favor of the cleaner `/v1/*` surface | partner-scoped address book (planned) |
| i18n | RU primary, EN parity, KY for navigation/dashboard | full KY parity for `landing.*`, `compliance.*` |
| Security | rate-limit on auth (5/min/IP) + general (100/min/IP) + B2B (300/min/IP); CORS whitelist; no stack-trace leak in 500s; monitoring/debug routes admin-gated; RLS active; per-merchant scoping derived only from signed key (never request body); **HMAC replay protection** on `/v1/*` (`X-ORGON-Key/Timestamp/Nonce/Signature`, ±60s drift, dedup via `merchant_request_nonces` PK, 15-min cleanup cron); pgcrypto envelope encryption for merchant API secrets (`MERCHANT_KEY_MASTER`); sandbox isolation (sandbox keys physically rejected on mainnet networks); deprecated `/api/transactions/{unid}/{sign,reject}` endpoints **removed** (they bypassed replay-guard) | KMS/Vault wire-up for signer key (abstraction is in) |
| Operator billing (Stripe) | Stripe Checkout adapter (`stripe_service.py`) for ORGON-side subscriptions sold via the marketing site; `organization_subscriptions` carries Stripe ids; service in *disabled* mode (clean 503) until `STRIPE_API_KEY` is set. Separate from the B2B Merchant Platform billing above (which has its own monthly-invoice generator) | real Stripe price IDs provisioned per env |
| Email | unified `backend/services/email_service.py` — SMTP backend (env-configured) + dev FileBackend fallback (`/tmp/orgon_emails.log`); typed entry points (password reset / email verification / invite) + 5-template HTML path used by `NotificationService`; legacy `backend/email_service.py` consolidated and removed | `SMTP_HOST` etc. on prod; SES/Mailgun choice |
| Observability | `observability.py` — JSON log formatter on `ORGON_JSON_LOGS=1`, `sentry_sdk` init on `SENTRY_DSN=…`. Both off by default, prod env flips them on | distributed tracing (OTel) |
| CI/CD | GitHub Actions: backend `compileall` + canonical schema apply against postgres:16 + 152 unit tests passing (0 skipped, 0 failed); frontend `tsc --noEmit` + eslint + Next.js build; **fresh-install job** (clean Postgres → canonical → uvicorn → `/api/health`); Playwright chromium smoke. `deploy.yml` curls Coolify deploy hooks on green CI for `main` / `preview-ready` | preview-DB separation, off-site backup mirror |
| Backups | `scripts/backup_pg.sh` — `pg_dump | gzip` with mtime retention + optional S3-compatible upload (AWS S3 / Cloudflare R2 / Wasabi / MinIO). Activated by `ORGON_BACKUP_S3_BUCKET` env; size-verified post-upload. systemd timer template in `DEPLOYMENT.md` | running on the new server (cron + systemd unit installed) |
| Schema | **single canonical file** (`backend/migrations/000_canonical_schema.sql`) — 60 tables, 15 functions, 36 triggers, 7 RLS policies, 311 indexes. Replaces the historical 47-file chain (preserved under `_historical/`). Tracking table `schema_migrations` with marker row gates re-runs. Greenfield deploys flip `ORGON_AUTO_MIGRATE=1` and the entrypoint applies it on first boot. **Overlay migrations 025–051 applied automatically in numeric order.** | future migrations are individual idempotent `0NN_*.sql` files |
| Deploy | Coolify on a new server — provisioning details in `DEPLOYMENT.md`. GitHub→Coolify deploy hooks via `.github/workflows/deploy.yml` (separate prod / preview hook URLs) | — |

> Honest baseline. Anything not listed is not yet implemented — please don't
> sell what isn't here.

---

## Tech stack

**Backend** — Python 3.12 · FastAPI · asyncpg · PostgreSQL 16 (with
pgcrypto) · Pydantic v2 · APScheduler · python-jose JWT · bcrypt ·
`eth_keys` for SECP256k1 · `httpx` for chain explorers and Safina · Safina Pay client.

**Frontend** — Next.js 16 (App Router) · React 19 · TypeScript 5 ·
Tailwind CSS 4 (`@theme inline` syntax, no `tailwind.config.js`) ·
Framer Motion · Magic UI primitives · Iconify Solar set · SWR · react-hot-toast.

**SDKs** — `@orgon/sdk` (TypeScript, Node ≥ 18, no runtime deps) ·
`orgon-sdk` (Python ≥ 3.10, `httpx`) — both hand-written, mirror API
1:1, ship with HMAC signing + webhook-signature verification helpers.

**Chain coverage** — Tron mainnet/Nile (TRX + TRC20 via TronGrid),
Bitcoin mainnet (Blockstream Esplora), Ethereum mainnet (ETH + ERC20
via Etherscan), Ethereum Sepolia (Sepolia Etherscan). ORGON-chain
(5800/5810) provisioned via Safina but deposit watcher pending their
explorer API.

**Infra** — Docker · Coolify v4 self-hosted · Postgres in container ·
Cloudflare (DNS).

---

## Quick start (local dev)

Requires Docker, Node 18+, Python 3.12+.

```bash
git clone https://github.com/MeShele/orgon-platform
cd orgon-platform

# 1. Spin up Postgres locally
docker compose up -d postgres

# 2. Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8890

# 3. Apply canonical schema (first time only — fresh DB)
DATABASE_URL=postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db \
  psql -v ON_ERROR_STOP=1 \
       "$DATABASE_URL" \
       -f backend/migrations/000_canonical_schema.sql

# 4. Frontend (separate terminal)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8890 npm run dev
```

Default demo accounts (created by `seed_test_organizations.sql`, applied
once after the canonical schema lands):

```
demo-admin@orgon.io   / demo2026   Admin in Demo Exchange + Demo Broker
demo-signer@orgon.io  / demo2026   Operator in Demo Exchange
demo-viewer@orgon.io  / demo2026   Viewer in Demo Exchange
```

For Coolify deploys (greenfield), set `ORGON_AUTO_MIGRATE=1` and the
container's entrypoint applies the canonical on first boot. See
[`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Repository layout

```
backend/                                FastAPI app
  api/routes_*.py                       JWT-bearer routers grouped by domain
  api/routes_public_v1.py               B2B /v1/* surface (HMAC-signed)
  api/routes_merchant_admin.py          /api/admin/merchants/* + api-keys + usage + invoices
  api/middleware_merchant_hmac.py       HMAC verify + replay-guard + quota
  api/middleware_request_id.py          X-Request-Id + error envelope + Prometheus
  services/                             business logic
  services/merchant_api_keys.py         issue / lookup / revoke; pgcrypto wrap
  services/merchant_wallet_service.py   lazy provisioning, sandbox enforcement
  services/merchant_tx_service.py       outbound tx + sign + usage counter
  services/merchant_billing.py          plan limits, usage counters, quota
  services/invoice_service.py           monthly cron + line items
  services/webhook_publisher.py         INSERT side of webhook queue
  services/webhook_delivery.py          drain worker, HMAC-sign + retry
  services/deposit_watcher.py           multi-chain dispatcher
  services/deposit_sources/             per-chain modules (tron / bitcoin / ethereum)
  services/end_user_service.py          merchant's customers CRUD
  safina/                               Safina Pay client + signer backends
  migrations/                           single canonical schema + 025+ overlays
  rbac.py                               role hierarchy + require_roles dependency
  observability.py                      JSON logs + Sentry init
frontend/                               Next.js 16 App Router
  src/app/(public)/*                    marketing, /developers (B2B onramp), billing
  src/app/(authenticated)/*             dashboard
  src/app/(authenticated)/admin/        platform admin: /admin/merchants/*
  src/app/(authenticated)/settings/     incl. ApiKeysSection (used in both /settings and /admin/merchants/[id])
  src/i18n/locales/                     ru.json · en.json · ky.json
sdks/typescript/                        @orgon/sdk — Node ≥ 18
  src/                                  hand-written client + resources + HMAC
  src/__tests__/                        unit tests (Node built-in test runner)
  examples/payment-receiver/            sample Express server
  examples/payout-sender/               sample CLI
sdks/python/                            orgon-sdk — Python ≥ 3.10
  orgon_sdk/                            same surface as TS, httpx-based
.github/workflows/sdk-publish.yml       on `sdk-v*` tag → npm publish with provenance
scripts/backup_pg.sh                    nightly pg_dump + retention + optional S3
docs/                                   architecture notes (live + archive/)
docker-compose.yml                      local dev stack
config/orgon.yaml                       backend runtime config
```

---

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — actual stack, auth flow, multi-sig flow, B2B platform layout
- [`API.md`](API.md) — both `/api/*` and `/v1/*` surfaces; HMAC spec; error catalog; SDK pointers
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Coolify procedures, env vars table, fresh DB apply, backups, rollback
- [`CI-CD.md`](CI-CD.md) — GitHub Actions pipelines (backend + frontend + SDK publish)
- [`CHANGELOG.md`](CHANGELOG.md) — what shipped, wave-by-wave
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — branch strategy, PR process, tests
- [`AGENTS.md`](AGENTS.md) — guidance for AI assistants working on the repo
- [`sdks/typescript/README.md`](sdks/typescript/README.md) — TS SDK install + usage + release flow
- [`sdks/python/README.md`](sdks/python/README.md) — Python SDK install + usage
- [`backend/migrations/README.md`](backend/migrations/README.md) — canonical schema flow, how to add a 025+ overlay
- [`docs/`](docs/) — deeper architecture notes (live and archived)
- Public: [`/developers`](https://orgon.asystem.ai/developers) — guided B2B onramp with copy-paste snippets

---

## License

Proprietary. © ОсОО «АСИСТЕМ». ORGON™ is a trademark of ОсОО «АСИСТЕМ».
