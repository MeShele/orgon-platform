# AGENTS.md — ORGON Project Context
> Stripe Blueprint pattern: scoped rule file for AI agents working on ORGON.
> Agents: read this file FIRST before any task in this project.

---

## Project Overview
**ORGON** — Multi-sig wallet platform for Кыргызстан
- **Phase 2** in progress: Safina API integration (crypto exchanges)
- **Domain:** orgon.asystem.ai
- **DB:** Neon PostgreSQL (cloud), multi-tenant schema

---

## Stack

### Backend (`backend/`)
```
FastAPI 0.115 + Python
asyncpg + PostgreSQL (Neon cloud)
JWT + refresh tokens (PyJWT 2.9)
Uvicorn on port 8000
```

**Key files:**
```
backend/api/routes_*.py     — all route handlers (auth, billing, contacts, analytics...)
backend/database/db.py      — DB connection pool
backend/database/migrations/— Alembic migrations
backend/config.py           — settings (env vars)
backend/main.py             — FastAPI app entry
```

**Critical rules:**
- ⛔ NEVER modify migration files directly — use `alembic revision --autogenerate -m "desc"`
- ⛔ NEVER hardcode credentials — use env vars from `.env`
- ✅ All routes must be async (`async def`)
- ✅ DB queries via asyncpg connection pool (see `database/db.py`)
- ✅ Auth via JWT: `dependencies.py → get_current_user()`
- Lint: `cd backend && ruff check . --fix`
- Tests: `cd backend && pytest tests/ -v`

### Frontend (`frontend/`)
```
Next.js 16 + TypeScript
TailwindCSS + Aceternity UI components
Port 3000 (dev), standalone output (prod)
```

**Key files:**
```
frontend/src/app/           — App Router pages
frontend/src/components/    — reusable components (Aceternity UI)
frontend/src/lib/           — API clients, utils
frontend/next.config.ts     — Next.js config (standalone output)
```

**Critical rules:**
- ✅ TypeScript strict — no `any`, no `@ts-ignore`
- ✅ Aceternity UI components preferred over custom CSS
- ✅ API calls through `src/lib/api.ts` (not direct fetch)
- ✅ Mobile-first responsive (Tailwind breakpoints)
- Lint: `cd frontend && npm run lint`
- Build check: `cd frontend && npm run build`
- Dev: `cd frontend && npm run dev`

---

## Команды запуска (local)

```bash
# Backend
cd ~/projects/ORGONASYSTEM
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Frontend
cd ~/projects/ORGONASYSTEM/frontend
npm run dev   # port 3000
```

---

## Environment Variables (не хранить в коде)

```
DATABASE_URL        — Neon PostgreSQL connection string
JWT_SECRET_KEY      — JWT signing key
SAFINA_EC_PRIVATE_KEY — Safina exchange private key
ORGON_ADMIN_TOKEN   — Admin API token
```

Все переменные в `.env` файле (корень проекта). Загружать: `source .env`

---

## Agent Assignments

| Agent | Scope | Don't touch |
|-------|-------|-------------|
| **Bekzat** ⚙️ | `backend/` — API routes, DB, migrations, auth | `frontend/` |
| **Ainura** 🎨 | `frontend/` — pages, components, styles | `backend/` |

---

## Current Phase 2 Goals
1. Safina API integration → `backend/api/routes_billing.py` + new `routes_safina.py`
2. Multi-sig wallet UI → `frontend/src/app/wallet/`
3. Analytics dashboard → `backend/api/routes_analytics.py` + frontend charts
4. B2B platform features → see `B2B_PLATFORM_SUMMARY.md`

---

## Blueprint Steps (Stripe pattern)

Every task follows:
```
[agent writes code]
    → lint (ruff / eslint) — DETERMINISTIC
    → type check (mypy / tsc) — DETERMINISTIC
    → tests (pytest / jest) — DETERMINISTIC
    → PR with summary — proof of work
```

**Max 2 retries** on failing tests → escalate to Урмат if still failing.

---

## Do NOT
- ⛔ Modify `backend/database/migrations/` manually
- ⛔ Change `next.config.ts` output mode
- ⛔ Push directly to `main` — always PR
- ⛔ Use synchronous DB calls in FastAPI routes
- ⛔ Import from `venv/` or `node_modules/` directly

_Last updated: 2026-03-13 by Forge_
