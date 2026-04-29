# ORGON

**Институциональная мульти-подписная кастоди для криптообменников, брокеров,
банков и финтех-компаний.**

Operational layer between wallet and blockchain: M-of-N signing policies,
KYC/KYB/AML, append-only audit log, B2B API and white-label dashboard.

```
production       https://orgon.asystem.kg
preview          https://orgon-preview.asystem.kg
api docs         https://orgon-preview-api.asystem.kg/api/redoc
support          support@orgon.asystem.kg
```

---

## Status

| Layer | What's wired | What's not yet |
|---|---|---|
| Auth | JWT + refresh + 2FA-ready, role hierarchy with legacy mapping | webhook-based JWT rotation |
| Multi-tenancy | service-layer tenant context (`set_tenant_context`) **and** Postgres RLS — migration `016` re-creates the policies that the buggy `005` failed to install, ENABLE+FORCE on `wallets` / `transactions` / `signatures` / `contacts` / `scheduled_transactions` / `audit_logs` | shared Coolify postgres serves both prod and preview — preview-DB split is on the runbook |
| Multi-signature | thresholds and signing flow live in Safina; ORGON records each step in `signature_history` (append-only via trigger from migration `015`); replay/double-sign blocked at the application layer + UNIQUE index from migration `018`; **live-verified against `https://my.safina.pro/ece/`** — 13/13 endpoints green incl. real `POST /newWallet` | full canonical-payload signature verification (currently trust Safina); HSM/KMS for the EC private key |
| Compliance | KYC/KYB submission + admin review queue (canonical at `/api/v1/kyc-kyb/*`); AML alert table; deduped — old `/api/v1/compliance/kyc` and `/api/auth/users` routes removed | AML rule engine (Sumsub/Chainalysis or in-house); document upload to S3/R2 |
| Audit log | append-only via migration `015` (UPDATE/DELETE blocked) | retention policy + cold storage |
| Frontend | Crimson Ledger v2 design — every page under `(authenticated)/*` and every public landing page now uses semantic tokens; mobile drawer; inline `LogoWordmark`; shadcn-style Dialog primitives replacing Aceternity in Contacts; pricing matches dfns 4-tier USD model | — |
| Partner API | every endpoint in `routes_partner*.py` scopes by org via the new `partners.organization_id` link (migration `017`); cross-tenant lookup returns 404, not the row | partner-scoped analytics + address book (`address_book_b2b` model still TBD) |
| i18n | RU primary, EN parity, KY for navigation/dashboard | full KY parity for `landing.*`, `compliance.*` |
| Security | rate-limit on auth (5/min/IP), CORS whitelist, no stack-trace leak in 500s, monitoring/debug routes admin-gated; RLS active; partner-id scoping; **HMAC replay protection** on B2B (`X-Nonce` + `X-Timestamp`, ±5 min drift, dedup via `partner_request_nonces` PK — migration `023`); deprecated `/api/transactions/{unid}/{sign,reject}` endpoints **removed** (they bypassed replay-guard) | HSM-backed signer key |
| Payments | Stripe Checkout adapter (`stripe_service.py`); `POST /api/v1/billing/checkout` returns a Session URL; `POST /api/v1/billing/webhook` verifies HMAC + dispatches; success/cancel landing pages on `(public)/billing/{success,cancel}`; service in *disabled* mode (clean 503) until `STRIPE_API_KEY` is set | real Stripe price IDs provisioned per env |
| Email | `email_service.py` with SMTP backend (env-configured) + dev file-log fallback; password reset, verification, invite flows wired | `SMTP_HOST` etc. on prod; SES/Mailgun choice |
| Observability | `observability.py` — JSON log formatter on `ORGON_JSON_LOGS=1`, `sentry_sdk` init on `SENTRY_DSN=…`. Both off by default, prod env flips them on | distributed tracing (OTel) |
| CI/CD | GitHub Actions: backend compile + migration replay against postgres:16 + pytest unit; frontend tsc + eslint + build; Playwright chromium smoke. `deploy.yml` curls Coolify deploy hooks on green CI for `main` / `preview-ready`. Nightly `pg_dump` script + retention | preview-DB separation, off-site backup mirror |
| Deploy | Coolify on `asystem-proxmox` (10.30.30.132), nginx on `hetzner-ax41` + Cloudflare DNS; GitHub→Coolify deploy hooks via `.github/workflows/deploy.yml` | — |

> Honest baseline. Anything not listed is not yet implemented — please don't
> sell what isn't here.

---

## Tech stack

**Backend** — Python 3.12 · FastAPI · asyncpg · PostgreSQL 16 · Pydantic v2 ·
APScheduler · python-jose JWT · bcrypt · Safina Pay client.

**Frontend** — Next.js 16 (App Router) · React 19 · TypeScript 5 ·
Tailwind CSS 4 (`@theme inline` syntax, no `tailwind.config.js`) ·
Framer Motion · Magic UI primitives · Iconify Solar set · SWR.

**Infra** — Docker · Coolify v4 self-hosted · Postgres in container ·
nginx reverse-proxy · Cloudflare (DNS proxied, no tunnel for orgon).

---

## Quick start (local dev)

Requires Docker, Node 18+, Python 3.12+.

```bash
git clone https://github.com/MeShele/orgon-platform
cd orgon-platform

# 1. Spin up Postgres locally
docker compose up -d postgres

# 2. Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8890

# 3. Frontend (separate terminal)
cd ../frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8890 npm run dev

# 4. Apply DB schema (once)
curl -X POST http://localhost:8890/api/health/run-migrations \
     -H "Authorization: Bearer <admin token>"
```

Default demo accounts (after migration `013` runs):

```
demo-admin@orgon.io   / demo2026   Admin in Demo Exchange + Demo Broker
demo-signer@orgon.io  / demo2026   Operator in Demo Exchange
demo-viewer@orgon.io  / demo2026   Viewer in Demo Exchange
```

---

## Repository layout

```
backend/                      FastAPI app
  api/routes_*.py             routers grouped by domain
  services/                   business logic, Safina client, signature flow
  database/                   asyncpg pool, schema migrations under database/migrations/
  migrations/                 multi-tenancy + RLS + seed migrations (001..018)
  rbac.py                     role hierarchy + require_roles dependency
  middleware/                 LoginRateLimit, security headers
  api/middleware*.py          CORS, RLS context, auth, B2B partner-key
frontend/                     Next.js 16 App Router
  src/app/(public)/*          marketing pages
  src/app/(authenticated)/*   logged-in app
  src/components/landing/     Hero, Pillars, FlowSection, …
  src/components/magicui/     Marquee, NumberTicker, AnimatedBeam
  src/components/ui/          Button, Card, primitives (Eyebrow, Mono, BigNum, …)
  src/i18n/locales/           ru.json · en.json · ky.json (must stay in sync)
docs/                         architecture + design notes
docs/archive/2026-Q1-Q2/      old phase-completion notes (preserved for history)
claude design/                design hand-offs (snapshots from claude.ai/design)
docker-compose.yml            local dev stack (Postgres + backend + frontend)
config/orgon.yaml             backend runtime config (read by backend/config.py)
```

---

## Documentation

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — actual stack, auth flow, multi-sig flow with honest disclaimers
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — Coolify API procedures, redeploy, rollback, log access
- [`CI-CD.md`](CI-CD.md) — GitHub Actions pipeline, secrets, deploy hooks, backup runbook
- [`CHANGELOG.md`](CHANGELOG.md) — what shipped, sprint-by-sprint
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — branch strategy, PR process, tests
- [`API.md`](API.md) — points at live Swagger / ReDoc
- [`AGENTS.md`](AGENTS.md) — guidance for AI assistants working on the repo
- [`docs/`](docs/) — deeper architecture notes
- [`docs/archive/2026-Q1-Q2/`](docs/archive/2026-Q1-Q2/) — historical session notes (read for context, not current truth)

---

## License

Proprietary. © ОсОО «АСИСТЕМ». ORGON™ is a trademark of ОсОО «АСИСТЕМ».
