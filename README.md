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
| Multi-tenancy | service-layer tenant context (`set_tenant_context`) | RLS policies have known SQL bugs in migration `005`; isolation is enforced at the Python layer until a follow-up migration |
| Multi-signature | thresholds and signing flow live in Safina; ORGON records each step in `signature_history` (append-only via trigger from migration `015`) | local canonical-payload verification + nonce/timestamp replay protection — planned |
| Compliance | KYC/KYB submission + admin review queue; AML alert table | regulator export (CSV/JSON) |
| Audit log | append-only via migration `015` (UPDATE/DELETE blocked) | retention policy + cold storage |
| Frontend | Crimson Ledger v2 design (light + composed dark), public marketing + 4 main authenticated screens | 25+ rest-of-app pages still on legacy density |
| i18n | RU primary, EN parity, KY for navigation/dashboard | full KY parity for `landing.*`, `compliance.*` |
| Security | rate-limit on auth (5/min/IP), CORS whitelist, no stack-trace leak in 500s, monitoring/debug routes admin-gated | RLS in Postgres, partner-id scoping in B2B API (work in progress) |
| Deploy | Coolify on `asystem-proxmox` (10.30.30.132), nginx on `hetzner-ax41` + Cloudflare DNS | GitHub→Coolify webhook (manual `curl` deploy for now) |

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
  migrations/                 multi-tenancy + RLS + seed migrations (001..015)
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
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — branch strategy, PR process, tests
- [`API.md`](API.md) — points at live Swagger / ReDoc
- [`AGENTS.md`](AGENTS.md) — guidance for AI assistants working on the repo
- [`docs/`](docs/) — deeper architecture notes
- [`docs/archive/2026-Q1-Q2/`](docs/archive/2026-Q1-Q2/) — historical session notes (read for context, not current truth)

---

## License

Proprietary. © ОсОО «АСИСТЕМ». ORGON™ is a trademark of ОсОО «АСИСТЕМ».
