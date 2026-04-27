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

- Use `docker compose up postgres` for a local Postgres (matches prod schema
  via migrations).
- Backend `uvicorn ... --reload` picks up changes instantly.
- Frontend `npm run dev` uses Turbopack; full reload on type errors.
- Run `pip install -r backend/requirements.txt` and `npm install` in
  frontend after pulling.

---

## Tests

```bash
# Backend
cd backend
pytest -v

# Frontend (Playwright E2E, smoke)
cd frontend
npx playwright test
```

CI (GitHub Actions, when wired): every PR runs `pytest backend/tests` and
`npm run build` in frontend. PR cannot merge with red tests.

When you add a feature:

- Backend route → corresponding `tests/test_<area>.py` with at least
  `200 happy path`, `401 unauthenticated`, `403 wrong role`, `400 invalid
  input`.
- Migration → integration test that runs it on a fresh DB and asserts the
  new constraint / trigger / data.
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
