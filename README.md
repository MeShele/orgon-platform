# ORGON

**Институциональная мульти-подписная кастоди для криптообменников, брокеров,
банков и финтех-компаний.**

Operational layer between wallet and blockchain: M-of-N signing policies,
KYC/KYB/AML, append-only audit log, B2B API and white-label dashboard.

```
production       (TBD — новый Coolify-сервер, см. DEPLOYMENT.md)
support          support@orgon.asystem.kg
api docs         GET /api/docs (Swagger), GET /api/redoc, GET /api/openapi.json
```

> Старая инсталляция на Hetzner-узле уходит в архив. Активный путь —
> greenfield-деплой на новом Coolify-сервере; конкретные домены и UUIDs
> уточнятся в `DEPLOYMENT.md` после провижининга.

---

## Status

| Layer | What's wired | What's not yet |
|---|---|---|
| Auth | JWT + refresh + 2FA-ready, role hierarchy with legacy mapping; cookie+localStorage drift detection on mount; rate-limit on auth (5/min/IP) | webhook-based JWT rotation |
| Multi-tenancy | service-layer tenant context (`set_tenant_context()` PG function) **and** Postgres RLS on `wallets / transactions / signatures / contacts / scheduled_transactions / audit_log`; super_admin bypass via `orgon_current_org_or_super()` | each environment gets its own Postgres on the new deploy (no shared instance) |
| Multi-signature | thresholds and signing flow live in Safina; ORGON records each step in `signature_history` (append-only via DB trigger); replay/double-sign blocked at the application layer + UNIQUE index on `(tx_unid, signer_address, action)`; **live-verified against `https://my.safina.pro/ece/`** — 13/13 endpoints green incl. real `POST /newWallet`; HSM-ready signer abstraction (`SignerBackend` protocol with `Env` / `KMS` / `Vault` implementations); **local signature-verification primitive** (`recover_signer_address` + `verify_signer`) ready, gated on `ORGON_VERIFY_SAFINA_SIGS=1` once Safina canonical-payload format is confirmed | KMS / Vault backend stubs need ~200 lines of boto3/hvac wire-up each (checklists in `signer_backends.py` docstrings); Safina canonical-payload format to confirm |
| Compliance | KYC/KYB submission + admin review queue (canonical at `/api/v1/kyc-kyb/*`); AML alert table | AML rule engine (Sumsub / Chainalysis or in-house); document upload to S3/R2 |
| Audit log | append-only via DB trigger (UPDATE/DELETE blocked) | retention policy + cold storage |
| Frontend | Crimson Ledger v2 design — every page under `(authenticated)/*` and every public landing page now uses semantic tokens; mobile drawer; inline `LogoWordmark`; shadcn-style Dialog primitives in Contacts; pricing matches dfns 4-tier USD model; `/settings` API-keys tab tells the truth about admin-only key provisioning | — |
| Partner API | every endpoint in `routes_partner*.py` scopes by org via `partners.organization_id`; cross-tenant lookup returns 404, not the row; admin REST under `/api/v1/admin/partners` (super_admin / company_admin) | partner-scoped analytics + address book (`address_book_b2b` model still TBD) |
| i18n | RU primary, EN parity, KY for navigation/dashboard | full KY parity for `landing.*`, `compliance.*` |
| Security | rate-limit on auth, CORS whitelist, no stack-trace leak in 500s, monitoring/debug routes admin-gated; RLS active; partner-id scoping; **HMAC replay protection** on B2B (`X-Nonce` + `X-Timestamp`, ±5 min drift, dedup via `partner_request_nonces` PK, 15-min cleanup cron); deprecated `/api/transactions/{unid}/{sign,reject}` endpoints **removed** (they bypassed replay-guard) | KMS/Vault wire-up for signer key (abstraction is in) |
| Payments | Stripe Checkout adapter (`stripe_service.py`); `POST /api/v1/billing/checkout` returns a Session URL; `POST /api/v1/billing/webhook` verifies HMAC + dispatches `checkout.session.completed` / `customer.subscription.updated|deleted` / `invoice.payment_failed` to `BillingService.upsert_subscription_from_checkout` etc.; `organization_subscriptions` carries `stripe_customer_id` / `stripe_subscription_id` / `stripe_session_id`; success/cancel landing pages on `(public)/billing/{success,cancel}`; service in *disabled* mode (clean 503) until `STRIPE_API_KEY` is set | real Stripe price IDs provisioned per env |
| Email | unified `backend/services/email_service.py` — SMTP backend (env-configured) + dev FileBackend fallback (`/tmp/orgon_emails.log`); typed entry points (password reset / email verification / invite) + 5-template HTML path used by `NotificationService`; legacy `backend/email_service.py` consolidated and removed | `SMTP_HOST` etc. on prod; SES/Mailgun choice |
| Observability | `observability.py` — JSON log formatter on `ORGON_JSON_LOGS=1`, `sentry_sdk` init on `SENTRY_DSN=…`. Both off by default, prod env flips them on | distributed tracing (OTel) |
| CI/CD | GitHub Actions: backend `compileall` + canonical schema apply against postgres:16 + 152 unit tests passing (0 skipped, 0 failed); frontend `tsc --noEmit` + eslint + Next.js build; **fresh-install job** (clean Postgres → canonical → uvicorn → `/api/health`); Playwright chromium smoke. `deploy.yml` curls Coolify deploy hooks on green CI for `main` / `preview-ready` | preview-DB separation, off-site backup mirror |
| Backups | `scripts/backup_pg.sh` — `pg_dump | gzip` with mtime retention + optional S3-compatible upload (AWS S3 / Cloudflare R2 / Wasabi / MinIO). Activated by `ORGON_BACKUP_S3_BUCKET` env; size-verified post-upload. systemd timer template in `DEPLOYMENT.md` | running on the new server (cron + systemd unit installed) |
| Schema | **single canonical file** (`backend/migrations/000_canonical_schema.sql`) — 60 tables, 15 functions, 36 triggers, 7 RLS policies, 311 indexes. Replaces the historical 47-file chain (preserved under `_historical/`). Tracking table `schema_migrations` with marker row gates re-runs. Greenfield deploys flip `ORGON_AUTO_MIGRATE=1` and the entrypoint applies it on first boot | future migrations are individual idempotent `025_*.sql` files |
| Deploy | Coolify on a new server — provisioning details in `DEPLOYMENT.md`. GitHub→Coolify deploy hooks via `.github/workflows/deploy.yml` (separate prod / preview hook URLs) | — |

> Honest baseline. Anything not listed is not yet implemented — please don't
> sell what isn't here.

---

## Tech stack

**Backend** — Python 3.12 · FastAPI · asyncpg · PostgreSQL 16 · Pydantic v2 ·
APScheduler · python-jose JWT · bcrypt · `eth_keys` for SECP256k1 · Safina Pay client.

**Frontend** — Next.js 16 (App Router) · React 19 · TypeScript 5 ·
Tailwind CSS 4 (`@theme inline` syntax, no `tailwind.config.js`) ·
Framer Motion · Magic UI primitives · Iconify Solar set · SWR.

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
backend/                      FastAPI app
  api/routes_*.py             routers grouped by domain
  api/middleware*.py          CORS, RLS context, auth, B2B partner-key, HMAC replay
  api/routes_admin_partners.py admin REST: provision / rotate / revoke partner keys
  services/                   business logic — wallet, transaction, signature, billing, email
  services/email_service.py   unified email (SMTP / FileBackend) + 5 HTML templates
  safina/                     Safina Pay client + signer + signer_backends (HSM-ready) + signature_verifier
  migrations/                 single canonical schema + future 025+ overlays
  migrations/_historical/     pre-Wave-11 47-file migration journey, preserved for git history
  rbac.py                     role hierarchy + require_roles dependency
  observability.py            JSON logs + Sentry init
  entrypoint.sh               container entrypoint; ORGON_AUTO_MIGRATE=1 applies canonical on greenfield
frontend/                     Next.js 16 App Router
  src/app/(public)/*          marketing pages, billing success/cancel
  src/app/(authenticated)/*   logged-in app
  src/components/landing/     Hero, Pillars, FlowSection, …
  src/components/magicui/     Marquee, NumberTicker, AnimatedBeam
  src/components/ui/          Button, Card, primitives (Eyebrow, Mono, BigNum, …)
  src/i18n/locales/           ru.json · en.json · ky.json (must stay in sync)
scripts/backup_pg.sh          nightly pg_dump + retention + optional S3-compatible upload
docs/                         architecture notes (live + archive/)
docker-compose.yml            local dev stack (Postgres + backend + frontend)
config/orgon.yaml             backend runtime config (read by backend/config.py)
```

---

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — actual stack, auth flow, multi-sig flow with honest disclaimers
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Coolify procedures, env vars table, fresh DB apply, backups, rollback
- [`CI-CD.md`](CI-CD.md) — GitHub Actions pipeline, secrets, deploy hooks, backup runbook
- [`CHANGELOG.md`](CHANGELOG.md) — what shipped, sprint/wave-by-wave (Waves 1-15)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — branch strategy, PR process, tests
- [`API.md`](API.md) — points at live Swagger / ReDoc
- [`AGENTS.md`](AGENTS.md) — guidance for AI assistants working on the repo
- [`backend/migrations/README.md`](backend/migrations/README.md) — canonical schema flow, how to add a 025+ overlay
- [`docs/`](docs/) — deeper architecture notes (live and archived)

---

## License

Proprietary. © ОсОО «АСИСТЕМ». ORGON™ is a trademark of ОсОО «АСИСТЕМ».
