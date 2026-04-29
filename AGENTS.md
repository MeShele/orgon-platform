# AGENTS.md — guidance for AI assistants working on ORGON

> Read this first. The README, ARCHITECTURE.md, and DEPLOYMENT.md are the
> long-form truth; this file is a fast-orientation cheat sheet for AI agents.

---

## What ORGON is

Multi-signature crypto custody platform for institutional clients
(crypto exchanges, brokers, banks, fintechs). Operational layer above
Safina Pay (custody / signing), enforces M-of-N policy, KYC/KYB/AML,
append-only audit log, and the operator UI.

Domain: `*.asystem.kg` (production / preview both managed via Coolify).
The current canonical deploy target is a fresh Coolify-managed server —
specific UUIDs / domains in [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Stack snapshot

### Backend (`backend/`)
- FastAPI 0.115+ on Python 3.12
- asyncpg + PostgreSQL 16 (self-hosted in Coolify, not managed cloud)
- JWT + refresh (python-jose), bcrypt-12 password hashes
- APScheduler for background jobs (cache refresh, nonce prune, sync)
- Uvicorn on port **8890** (not 8000 — that's a stale doc reference)

### Frontend (`frontend/`)
- Next.js 16 (App Router) + React 19 + TypeScript 5
- Tailwind CSS 4 (no `tailwind.config.js` — uses `@theme inline`)
- Framer Motion + Magic UI primitives + Iconify Solar icons
- Port **3000** in dev, standalone output in prod

### Schema
- **Single canonical SQL file**: `backend/migrations/000_canonical_schema.sql`
  (60 tables, generated via `pg_dump`). Applied once on a fresh DB; gated
  by `schema_migrations` row marker.
- **No Alembic.** Plain SQL files only. Future migrations are individual
  idempotent `025_*.sql` files.
- All previous 47 historical migrations are under
  `backend/migrations/_historical/` for reference — **never run them on
  fresh installs**.

### Tests
- `backend/tests/test_*.py` — pytest, 152 passed, 0 skipped, 0 failed
- CI runs them on `postgres:16-alpine` service container with the
  canonical schema applied via `ON_ERROR_STOP=1`

---

## Critical rules

### Backend
- ✅ Every route handler is `async def`.
- ✅ DB calls go through asyncpg's `fetch / fetchrow / fetchval / execute`
  (NOT `fetchall / fetchone` — those are the legacy SQLite wrapper).
- ✅ Tests use `AsyncMock` for `db` (not `MagicMock`) — see existing tests
  for the pattern.
- ⛔ Never edit `backend/migrations/000_canonical_schema.sql` in place —
  that breaks the "single source of truth" invariant. Add a new
  `025_*.sql` instead.
- ⛔ Never run anything under `backend/migrations/_historical/`.
- ⛔ Never hardcode credentials. All env via Coolify (or `.env` for local
  dev — gitignored).

### Frontend
- ✅ TypeScript strict — no `any`, no `@ts-ignore` without an attached
  comment explaining why.
- ✅ API calls through `src/lib/api.ts`, not raw `fetch()`. Auth/cookie
  handling is centralised there.
- ✅ Animations: Framer Motion / Tailwind / Magic UI / Motion Primitives
  only (per the global UI rules in `~/.claude/CLAUDE.md`).
- ⛔ Don't add a new animation library without asking.
- ⛔ Don't change `next.config.ts` output mode (currently `standalone`
  for Coolify).

### Schema changes
- ✅ New migrations go in `backend/migrations/0NN_xxx.sql`, idempotent,
  with a tracking row at the bottom:
  ```sql
  INSERT INTO public.schema_migrations (version, description)
  VALUES ('025_my_change', 'one-line summary')
  ON CONFLICT (version) DO NOTHING;
  ```
- ⛔ Don't modify the canonical file in place. Don't bring back any of
  the historical files.

---

## Local dev commands

```bash
# Postgres (Docker)
docker compose up -d postgres

# Apply canonical (first time only on a fresh DB)
psql -v ON_ERROR_STOP=1 \
     "postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db" \
     -f backend/migrations/000_canonical_schema.sql

# Backend
.venv/bin/python -m uvicorn backend.main:app --reload --port 8890

# Frontend (separate terminal)
cd frontend && npm run dev   # port 3000

# Tests
.venv/bin/python -m pytest backend/tests/ -v

# Type-check frontend
cd frontend && npx tsc --noEmit

# Backend compile-check
.venv/bin/python -m compileall -q backend
```

---

## Required env vars (production)

Full table in [`DEPLOYMENT.md`](DEPLOYMENT.md). The non-obvious ones:

| Var | Why |
|---|---|
| `JWT_SECRET_KEY` | Without it, the auto-fallback rotates on every restart, kicking every user back to login |
| `ORGON_AUTO_MIGRATE=1` | On greenfield Coolify deploy, makes entrypoint apply the canonical on first boot |
| `ORGON_SIGNER_BACKEND` | `env` (default) / `kms` / `vault`. Required `SAFINA_EC_PRIVATE_KEY` for `env`; KMS/Vault stubs need wire-up |
| `ORGON_BACKUP_S3_BUCKET` + S3 creds | Activate off-site backups via `scripts/backup_pg.sh` |
| `STRIPE_API_KEY` + `STRIPE_WEBHOOK_SECRET` | Optional — billing routes return 503 if unset |
| `SENTRY_DSN`, `ORGON_JSON_LOGS=1` | Optional — observability layer |

---

## Blueprint for any task

```
[agent reads task + relevant code]
   → write code
   → backend/compileall + frontend/tsc — DETERMINISTIC
   → relevant tests pass — DETERMINISTIC
   → smoke (uvicorn boots / UI loads) when applicable
   → commit on a feature branch (never push to main directly)
   → PR with detailed description
```

If a test fails twice and the root cause isn't obvious — escalate
rather than monkey-patch.

---

## What NOT to do

- ⛔ Push directly to `main` or `preview-ready` — always feature branch + PR
- ⛔ Edit `backend/migrations/000_canonical_schema.sql` in place
- ⛔ Run any file under `backend/migrations/_historical/`
- ⛔ Use `MagicMock` for asyncpg `db` in tests — use `AsyncMock`
- ⛔ Hardcode `orgon-preview.asystem.kg` / specific port numbers /
  Coolify UUIDs in code (those move when the deploy moves)
- ⛔ Use synchronous DB calls inside FastAPI route handlers
- ⛔ Add a backwards-compat shim "for the old schema" — there is no old
  schema in the new world; everything is the canonical
- ⛔ Re-introduce dead code paths from the historical migrations or the
  pre-Wave-11 dual-dir layout

_Last updated: 2026-04-29, end of Wave 15 (production-readiness pack)._
