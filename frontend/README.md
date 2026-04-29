# ORGON frontend

Next.js 16 (App Router) + React 19 + TypeScript 5 + Tailwind CSS 4 +
Framer Motion + Magic UI primitives + Iconify Solar icons + SWR.

For project-wide context (architecture, deploy, API), see the docs at
the repo root: [`../README.md`](../README.md), [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

---

## Local dev

```bash
npm install
NEXT_PUBLIC_API_URL=http://localhost:8890 npm run dev
```

Open <http://localhost:3000>. Backend must be running on `:8890`
(see backend README / repo-root README for that).

If `NEXT_PUBLIC_API_URL` is unset, the client routes through the Next.js
proxy to `/api/*` — handy for cookie-based auth without CORS plumbing,
but breaks WebSocket. Set the env explicitly when developing
WS-driven views.

---

## Stack rules

- TypeScript strict; no `any`, no `@ts-ignore` without an attached
  comment.
- API calls through `src/lib/api.ts`, not raw `fetch()`. Auth/cookie
  handling is centralised there.
- Animations: only Framer Motion / Tailwind / Magic UI / Motion
  Primitives (per `~/.claude/CLAUDE.md`). No `react-spring`, `anime.js`,
  GSAP-mixed-with-Motion, etc.
- i18n keys must stay synced across `src/i18n/locales/{ru,en,ky}.json`.
  RU and EN are full-parity; KY ships navigation + dashboard, full
  parity for landing/compliance is on the backlog.

---

## Build / test / lint

```bash
npx tsc --noEmit          # type-check
npm run lint              # ESLint
npm run build             # production build (Coolify uses this)
npm run test:e2e          # Playwright chromium
```

CI runs all four on every PR.

---

## Deployment

Coolify rebuilds on push to `main` (prod) and `preview-ready` (preview)
via `.github/workflows/deploy.yml`. Output mode is `standalone` so
Coolify can serve the bundled output without a Node runtime in the
container at runtime — see `next.config.ts`.
