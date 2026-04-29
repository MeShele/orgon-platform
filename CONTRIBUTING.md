# Contributing

How to make changes to ORGON without breaking production.

---

## Branches

```
main            production. Direct commits forbidden. Merged via PR only.
preview-ready   staging. Where multi-day refactors live until they're ready
                for review. Force-push allowed (paired with a backup tag).
feature/<x>    short-lived branch for a single change. Merge to preview-ready
               or directly to main via PR depending on scope.
```

The Coolify webhook (when wired) will redeploy `prod` on every push to `main`
and `preview` on every push to `preview-ready`.

---

## PR process

1. Branch off `preview-ready` (or `main` for hotfixes).
2. Commit logically — one concern per commit. Co-author Claude Code if used:
   `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`.
3. Open a PR with:
   - what changed
   - why (link issue / Slack thread)
   - what you tested manually (URLs hit, demo accounts used)
   - migration notes if any (need `/api/health/run-migrations`?)
4. Wait for green tests + at least one human approval.
5. Merge with **squash** (we don't keep individual commits in main history).
6. Verify the deploy succeeded (Coolify UI or `docker ps` on the host).

---

## Local development

See `README.md` for the quick start. Key points:

- `docker compose up -d postgres` for a local Postgres.
- First time on a fresh DB: apply the canonical schema once:
  ```bash
  psql -v ON_ERROR_STOP=1 \
       "postgresql://orgon_user:orgon_dev_password@localhost:5432/orgon_db" \
       -f backend/migrations/000_canonical_schema.sql
  ```
- Backend `uvicorn ... --reload` picks up changes instantly. Port 8890.
- Frontend `npm run dev` uses Turbopack; port 3000.
- Run `pip install -r backend/requirements.txt` and `npm install` in
  frontend after pulling.

---

## Tests

```bash
# Backend (152 tests, 0 skipped, must stay green)
.venv/bin/python -m pytest backend/tests/ -v

# Backend compile-check (catches import errors fast)
.venv/bin/python -m compileall -q backend

# Frontend
cd frontend && npx tsc --noEmit
cd frontend && npm run build
cd frontend && npx playwright test       # smoke E2E
```

CI (GitHub Actions): every PR runs four jobs:
1. `backend` — compileall + canonical schema apply against postgres:16 + 152 unit tests
2. `frontend` — tsc + eslint + Next.js build
3. `fresh-install` — clean Postgres → canonical → uvicorn → assert `/api/health=200` within 30s
4. `e2e` — Playwright chromium

PR cannot merge with red tests.

When you add a feature:

- Backend route → corresponding `tests/test_<area>.py` with at least
  `200 happy path`, `401 unauthenticated`, `403 wrong role`, `400 invalid
  input`. Use `AsyncMock` for db and Safina client; never `MagicMock`
  for awaitable methods.
- Schema change → new `backend/migrations/0NN_xxx.sql`, idempotent, with
  a `schema_migrations` insert at the bottom. Verify locally on a clean
  Postgres before opening the PR.
- Frontend page → at least Playwright `goto + assert h1`.

---

## Commits and code style

- Conventional-ish commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`.
- One logical concern per commit. If you find yourself writing "and" in the
  message, split it.
- Backend: `black` formatting, type hints required, docstrings on public
  service methods.
- Frontend: TypeScript strict, no `any` in new code, `next.config.ts`
  `ignoreBuildErrors` is a temporary measure — remove it as you fix
  surrounding errors.
- Animations: see [`~/.claude/CLAUDE.md`](../../.claude/CLAUDE.md) — strict stack
  (Framer Motion + Tailwind + Magic UI + Motion Primitives only).

---

## When you must edit secrets / env

- **Never commit a secret to git**, even on a feature branch. The repo is
  private, but git history travels with every clone.
- Update Coolify env via API or UI. Both prod and preview have separate env
  blocks; sync values when behaviour should match.
- Document the change in the PR body. Don't paste the secret value.

---

## Adding a dependency

Backend:

```bash
# Bump backend/requirements.txt with a pinned version
# Run pip install in venv, verify nothing else breaks
```

Frontend:

- For UI animation libs: review [`~/.claude/CLAUDE.md`](../../.claude/CLAUDE.md)
  first — only `framer-motion`, `tailwindcss-animate`, `gsap`, Lottie are
  approved engines. Magic UI / Motion Primitives are copy-paste, not npm.
- For non-UI deps: open a PR with the rationale, no surprise installs.

---

## Documentation rule

Documentation describes what *exists*, not what *we wish existed*. If you
add a section to `ARCHITECTURE.md` or `README.md`, it must correspond to
shipped code. Aspirational features get the `(planned)` tag.

If a doc and the code disagree, fix the doc — unless the code is wrong, in
which case fix both in the same PR.
