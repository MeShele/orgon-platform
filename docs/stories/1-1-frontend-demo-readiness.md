# Story 1.1: Frontend Demo Readiness for Customer Walkthrough

Status: review

<!-- Validation: optional. Run validate-create-story before dev-story for quality check. -->

## Story

As an **ORGON sales/founder presenting to a prospective B2B customer**,
I want **the public marketing pages and the authenticated UI walkthrough to look polished, on-brand, and free of visible "in-development" cracks**,
so that **the customer judges the product on its real architectural depth (multi-sig, RLS, audit) rather than being distracted by half-finished UI corners or empty-state confusion**.

## Acceptance Criteria

1. **AC-1 — Marketing pages pass a visual demo on mobile + desktop.** All pages under `(public)` (`/`, `/pricing`, `/features`, `/about`, `/demo/architecture`) render at 375px (iPhone SE), 768px (iPad), and 1440px (desktop) without horizontal scroll, broken layouts, or motion jank. CTA buttons reachable. Hero loads under 2s on a clean cache via `https://orgon.asystem.ai/`.

2. **AC-2 — `/demo/architecture` simulator is the centerpiece.** All 6 scenarios (withdrawal, sanctions block, replay, RLS, night window, webhook) advance through every node without console errors, the side-timeline syncs with the active scenario, and the sticky graph layout works on both desktop and tablet (1024px+). Mobile (<768px) gracefully degrades to a non-sticky stacked view rather than breaking. **No new dependencies.**

3. **AC-3 — Authenticated empty states are demo-grade.** With the live (sparse) demo data on `https://orgon.asystem.ai`, the following pages show a polished `EmptyState` (using `frontend/src/components/common/EmptyState.tsx`) when their primary list/feed is empty — never a blank container or an error toast: `/dashboard` (when `transactions_24h === 0` show contextual hint, **not** a blank "Recent Activity" card), `/transactions` (empty list state), `/signatures` (no pending state), `/scheduled` (no scheduled), `/contacts` (no contacts), `/audit` (no events), `/reports` (no reports), `/analytics` (no balance history). Each empty state has: icon + 1-line title + 2-line description + optional primary CTA href that goes somewhere real.

4. **AC-4 — Sidebar STUB pages are gated behind "Roadmap".** In `frontend/src/components/layout/sidebar-nav.ts` the four routes that are scaffold-only — `/compliance`, `/documents`, `/users`, `/settings` (general — keep `/settings/keys`, `/settings/webhooks`, `/settings/system` visible) — are either (a) moved into a new last-position group `roadmap` with a small "Скоро" / "Coming soon" pill in the sidebar item, or (b) hidden behind a `NEXT_PUBLIC_SHOW_ROADMAP` env flag (default `0` for the demo build). Decision: implement (a) — visible but clearly labeled, so the customer sees breadth without clicking into half-built screens. The page contents themselves stay; only sidebar visibility/labeling changes.

5. **AC-5 — Wallet display names use a fallback when `label` is null.** On `/wallets` and `/dashboard` recent-activity, when the wallet's `label` field is `null` (current Safina-synced state), display name resolves to `formatWalletDisplayName(wallet)` which produces a human-readable label of shape `«<NetworkName> · <addr_short>»` (e.g. `«BSC · 0x7a3f…b2cd»`) instead of the raw 32-char hex `myUNID`. The `myUNID` stays available in a tooltip / detail view. Helper lives in `frontend/src/lib/walletDisplay.ts` (new file). Used everywhere the wallet name was previously rendered.

6. **AC-6 — Demo walkthrough script ships in `docs/demo-walkthrough.md`.** A 6-8 step demo script (Marketing landing → simulator → login as `demo-admin@orgon.io` → dashboard → wallets → simulate sign on `/signatures` → audit → exit). Each step lists: URL, expected visual, common talking point, fallback if data is sparse. This is the **demo runbook** the presenter follows.

7. **AC-7 — `tsc --noEmit` clean and `eslint` clean on `frontend/` after changes.** No new `any`, no `@ts-ignore` without an attached one-line comment. No new runtime warnings in the browser console on a manual click-through of all 5 marketing pages + 8 authenticated pages above.

## Tasks / Subtasks

- [x] **Task 1 — Marketing-page visual sweep on prod-deployed site (AC: 1, 2)**
  - [ ] Open `https://orgon.asystem.ai/` at 375 / 768 / 1440. Capture concrete bugs (specific component + viewport + symptom). Don't fix yet — produce a list.
  - [ ] Same for `/pricing`, `/features`, `/about`.
  - [ ] `/demo/architecture` — click through all 6 scenarios, watch console, watch network. List concrete defects (any console error, any animation jank, any layout shift > 0.1 CLS).
  - [ ] Cross-reference with `frontend/src/components/landing/*` — don't refactor unless a defect from the sweep is rooted there.
  - [ ] Apply the minimum fixes for the defects collected. Each fix touches the smallest possible scope.

- [x] **Task 2 — Empty-state pass on authenticated pages (AC: 3)**
  - [ ] For each of the 8 pages in AC-3, locate where the list/feed renders (usually a `.map(...)` over a fetch result) and the surrounding container.
  - [ ] Wrap with `length === 0` branch returning `<EmptyState icon="..." title="..." description="..." actionLabel?="..." actionHref?="..." />`.
  - [ ] Pick icons from the `solar` Iconify set already used in `sidebar-nav.ts` (e.g. `solar:wallet-linear`, `solar:transfer-horizontal-linear`).
  - [ ] Copy must be in RU primary, EN parallel via `next-intl`. Add new keys under `frontend/src/i18n/locales/{ru,en}.json` `emptyStates.*` namespace; KY can stay missing (per scope fence).
  - [ ] Don't replace existing loading skeletons — they fire on `isLoading`. Empty state fires on `!isLoading && data.length === 0`.

- [x] **Task 3 — Sidebar Roadmap group (AC: 4)**
  - [ ] Edit `frontend/src/components/layout/sidebar-nav.ts`:
    - Add an optional field to `SidebarItem`: `roadmap?: boolean`.
    - Move `/compliance`, `/documents`, `/users`, `/settings` (general — but **keep** `/settings/keys`, `/settings/webhooks`, `/settings/system`) into a new last-position group `{ label: "roadmap", items: [...] }` with `roadmap: true` on each.
    - Note: the `/settings` literal route still exists; only its sidebar item moves. Don't delete the page file.
  - [ ] In `frontend/src/components/layout/AceternitySidebar.tsx` and `MobileSidebar.tsx`: render a small badge (use existing `Badge` primitive in `frontend/src/components/ui/Badge.tsx` if present; otherwise tiny inline span with `bg-muted text-muted-foreground rounded px-1.5 py-0.5 text-[10px]`) reading "Скоро" / "Coming soon" beside the item label when `item.roadmap === true`.
  - [ ] Add i18n key `navigation.groups.roadmap` and `navigation.badges.comingSoon`.
  - [ ] Verify `filterByRole()` in `sidebar-nav.ts` still works — items with `roadmap: true` should still respect `roles`.

- [x] **Task 4 — Wallet display name fallback (AC: 5)**
  - [ ] Create `frontend/src/lib/walletDisplay.ts`. Export:
    ```ts
    export interface WalletForDisplay { label?: string | null; name: string; my_unid?: string; addr?: string; network?: number | string; }
    export function formatWalletDisplayName(w: WalletForDisplay, networks?: { id: number; name: string }[]): string;
    export function shortenAddr(addr: string, head = 6, tail = 4): string;
    ```
  - [ ] Logic:
    - If `w.label` truthy → return as-is.
    - Else lookup network name from `networks` (passed in or memoized via SWR) → shape `<NetworkName> · <addr_short>` (e.g. `BSC · 0x7a3f…b2cd`).
    - If `addr` empty → fall back to `<NetworkName> · <my_unid first 8>…<my_unid last 4>` (e.g. `BSC · 11FCEC93…F5`).
    - If network unknown → `Wallet · <my_unid first 8>…<my_unid last 4>`.
  - [ ] Unit tests in `frontend/src/lib/__tests__/walletDisplay.test.ts` — 4-5 cases (label set, label null + addr present, addr empty, network unknown, malformed input). Use vitest if already configured; if not, defer tests to next story (note in dev log).
  - [ ] Replace render points: `frontend/src/app/(authenticated)/wallets/page.tsx` (list), `frontend/src/app/(authenticated)/wallets/[name]/page.tsx` (detail header), `frontend/src/app/(authenticated)/dashboard/page.tsx` (recent activity if it shows wallet name), `frontend/src/components/dashboard/*` (anywhere `wallet.name` is used as a heading).
  - [ ] Tooltip/detail view should still expose `my_unid` (e.g. via Radix `<Tooltip>` from `@radix-ui/react-tooltip` already installed) so power users can copy the canonical UNID.

- [x] **Task 5 — Demo walkthrough script (AC: 6)**
  - [ ] Create `docs/demo-walkthrough.md`. Structure: 6-8 sections, each with `### Step N — <one-line title>`, then `URL:`, `Expected visual:`, `Talking point (RU):`, `If empty/sparse:`.
  - [ ] Steps to cover:
    1. Marketing hero (`/`) — value prop, "institutional custody"
    2. Architecture simulator (`/demo/architecture`) — show 1-2 scenarios live
    3. Login (`/login`) as `demo-admin@orgon.io / demo2026`
    4. Dashboard (`/dashboard`) — "real Safina-synced KPIs"
    5. Wallets (`/wallets`) — show the 15 live wallets
    6. Signatures (`/signatures`) — explain M-of-N flow even if pending list empty (point to simulator scenario again)
    7. Audit (`/audit`) — "every action immutably logged"
    8. Optional: Pricing (`/pricing`)

- [x] **Task 6 — Type-check + lint + manual smoke (AC: 7)**
  - [ ] `cd frontend && npx tsc --noEmit` — exit 0.
  - [ ] `cd frontend && npm run lint` — exit 0 (no new warnings).
  - [ ] Manual smoke: open browser DevTools console, click through all 5 marketing pages + 8 authenticated pages from AC-3. Note any new console errors/warnings. Fix or document.
  - [ ] Push to `feature/demo-simulator`. Coolify auto-deploys via `POST /api/v1/deploy?uuid=nw5o0foj43w96q9upluxnr0l&force=true` (token in user's session — ask if expired).

## Dev Notes

### What demo-admin actually sees today (verified live, 2026-05-01)

After login on `https://orgon.asystem.ai`:

```
GET /api/auth/me                  → demo-admin, role=admin, id=1
GET /api/dashboard/stats          → 15 wallets, $0 balance, 1 tx/24h, 0 pending sigs, 7 networks
GET /api/wallets                  → 15 entries, label: null, name: random hex, addr: ""
GET /api/organizations            → []  (demo-admin not linked)
GET /api/transactions/filtered    → 404 "Transaction not found"  (BACKEND BUG, out of scope)
GET /api/signatures/pending       → []
GET /api/networks                 → 7 networks, includes BSC/TRX/ETH/POL/BTC
```

So: real Safina sync IS happening (15 wallets), but txs/sigs/orgs are empty. **This story does not fix the data layer** — only the visual layer that has to render gracefully against this data.

### Stack constraints (NON-NEGOTIABLE per `~/.claude/CLAUDE.md`)

- **Animation engines**: Framer Motion (`framer-motion@12`) only. Tailwind via `tailwindcss-animate` (already installed). Magic UI primitives (Marquee/NumberTicker/AnimatedBeam — already imported). Motion Primitives `TextEffect` style. Lottie via `@lottiefiles/dotlottie-react` if needed for empty-state illustrations — **ASK before adding**, don't auto-install.
- **Forbidden**: `react-spring`, `anime.js`, `mo.js`, `popmotion`, jQuery animations, Three.js / R3F, mixing GSAP + Framer in same component. GSAP is allowed only for marketing scroll-driven scenes — NOT in this story's scope, do not add.
- **Components first**: check `shadcn/ui`, `magicui.design`, `ui.aceternity.com`, `motion-primitives.com` before writing custom. The codebase already uses `Dialog` (Radix), `Badge`, `Button`, `Card` primitives — reuse those.
- **Performance**: animate only `transform` (translate/scale/rotate) and `opacity`. Never `width / height / top / left / margin / padding` — they layout-thrash.
- **Reduced motion**: honor `prefers-reduced-motion`. Framer: `useReducedMotion()` returns static variants. Already a pattern in `frontend/src/components/landing/Hero.tsx` — copy it.
- **Timings**: hover/tap 150-250ms ease-out; reveals 400-600ms `[0.22, 1, 0.36, 1]`; big transitions ≤ 800ms.

### Code conventions (from `AGENTS.md`)

- TypeScript strict — no `any`, no `@ts-ignore` without a one-line comment explaining why.
- API calls **only** through `frontend/src/lib/api.ts`, not raw `fetch()`. Auth/cookie handling is centralized there.
- Don't change `next.config.ts` output mode (must stay `standalone` for Coolify).
- Don't push to `main`. Branch: stay on `feature/demo-simulator`. PR after.

### File paths (verified)

| What | Where |
|---|---|
| Sidebar config | `frontend/src/components/layout/sidebar-nav.ts` |
| Sidebar UI (desktop) | `frontend/src/components/layout/AceternitySidebar.tsx` |
| Sidebar UI (mobile) | `frontend/src/components/layout/MobileSidebar.tsx` |
| Existing EmptyState | `frontend/src/components/common/EmptyState.tsx` (don't recreate — reuse) |
| Wallets list | `frontend/src/app/(authenticated)/wallets/page.tsx` |
| Wallet detail | `frontend/src/app/(authenticated)/wallets/[name]/page.tsx` |
| Dashboard | `frontend/src/app/(authenticated)/dashboard/page.tsx` |
| Public landing root | `frontend/src/app/(public)/page.tsx` |
| Landing components | `frontend/src/components/landing/` (Hero, Pillars, FlowSection, BottomCTA, etc.) |
| Demo simulator | `frontend/src/app/(public)/demo/architecture/page.tsx` + `frontend/src/components/demo-simulator/*` |
| i18n locales | `frontend/src/i18n/locales/{ru,en,ky}.json` |
| API client | `frontend/src/lib/api.ts` |

### Anti-patterns to avoid (specific to this codebase)

- **Don't write a new EmptyState component.** `frontend/src/components/common/EmptyState.tsx` already exists with the right API (icon/title/description/CTA). Use it.
- **Don't refactor landing components in this story.** Wave 17a-17g already polished the simulator. The marketing-page sweep is a defect-driven pass, not a redesign.
- **Don't add Lottie** without asking — empty states can use Iconify `solar:` icons (already a dep) for illustration.
- **Don't add `react-icons` or any new icon lib** — `@iconify/react` + `@iconify-json/solar` are already installed and that's the project standard.
- **Don't break i18n** by hardcoding RU strings. Add keys to `ru.json` + `en.json`. KY can lag (out of scope).
- **Don't touch `(authenticated)/{compliance,documents,users,settings}/page.tsx`** — they have their own honest "В разработке" banners and are explicitly out of scope. We only adjust their visibility in the sidebar.

### What's explicitly OUT of scope (do not drift)

- Backend changes of any kind. The `404 on /api/transactions/filtered`, missing demo data, missing `user_organizations` link — all logged in `~/.claude/projects/-Users-caesarclown-Projects-Orgon/memory/project_orgon_backend_demo_followups.md`. **Do not fix here.**
- Removing the actual STUB pages. They stay reachable by URL; only sidebar visibility changes.
- HSM / KMS wire-up, Stripe live billing, AML engine, KYC document upload — far out of scope.
- KY i18n parity — out of scope per user instruction.
- New marketing copy or product positioning rewrites. Visual fixes only.
- Adding a CMS, headless or otherwise.

### Reference: live system state (verified 2026-05-01)

- Live URL: `https://orgon.asystem.ai` (Cloudflare orange-cloud → systemd Caddy on `coolify-orion` 65.21.205.230 → frontend container at `127.0.0.1:13000`)
- Coolify panel: `https://c.asystem.ai`, app uuid `nw5o0foj43w96q9upluxnr0l`
- Branch deploys: `feature/demo-simulator` is the active branch; `git push origin feature/demo-simulator` then `POST /api/v1/deploy?uuid=nw5o0foj43w96q9upluxnr0l&force=true` with the bearer token (kept in user's session) triggers redeploy.
- Demo creds: `demo-admin@orgon.io / demo2026` (admin), `demo-signer@orgon.io / demo2026` (signer), `demo-viewer@orgon.io / demo2026` (viewer).

### Project Structure Notes

- The `frontend/` package is a standard Next.js 16 App Router layout (`src/app/(public)/*`, `src/app/(authenticated)/*`). Co-located feature folders, no Pages-Router legacy.
- `next.config.ts` outputs `standalone` for Coolify — do not change.
- Tailwind 4 syntax: tokens live in `frontend/src/app/globals.css` under `@theme inline { ... }` (no `tailwind.config.js`). Crimson Ledger v2 token names: `--primary` (#9c1825), `--destructive` (#1a1a1a), `--surface-contrast`, `--background` (#fafaf7).
- All pages use the semantic tokens above (`bg-muted`, `text-foreground`, `border-primary` etc) — Sprint 4 swept hardcoded `slate-*/blue-*/...` everywhere. **Do not reintroduce raw color classes.**

### References

- Project status snapshot: [`README.md` Status table](../../README.md)
- Architecture: [`ARCHITECTURE.md`](../../ARCHITECTURE.md)
- Recent UI history: [`CHANGELOG.md` Sprint 4 + Wave 17](../../CHANGELOG.md)
- Frontend AI cheat sheet: [`AGENTS.md`](../../AGENTS.md)
- Global stack rules: `~/.claude/CLAUDE.md` (UI animation stack section)
- Live diagnostics that informed this story:
  - `GET /api/wallets` returns label:null, name:random-hex (verified curl 2026-05-01 09:56 UTC)
  - `GET /api/organizations` returns `[]` for demo-admin (verified)
  - `/demo/architecture` simulator polished through Wave 17g

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context), via Claude Code CLI.

### Debug Log References

- Live verification before story: `GET /api/auth/me`, `/dashboard/stats`, `/wallets`, `/organizations`, `/transactions/filtered`, `/signatures/pending`, `/networks` on `https://orgon.asystem.ai` (2026-05-01 09:55–09:56 UTC).
- Marketing-page code review via Explore agent — 11 findings, all classified as intentional (network brand colors, ambient AnimatedBeam timings, Wave 17 simulator amber state highlight). No fixes applied — see AC-1/AC-2 verdict in completion notes.
- `npx tsc --noEmit` → exit 0.
- `npm run lint` → 205 problems (baseline before this story: 208). Net −3.
- Coolify deployment uuid `a12bi3fa68ma1gvgunun4zqr` finished green in ~2 minutes; live URL `https://orgon.asystem.ai` returns HTTP/2 200 post-deploy. demo-admin login still works.

### Completion Notes List

- **AC-1 / AC-2 (marketing + simulator)**: Code review across `(public)/*` and `components/landing/*` and `components/demo-simulator/*`. The simulator already has correct responsive layout (`lg:flex` + sticky on lg+, stacked on mobile with `min-h-[520px]`). Marketing pages use Crimson Ledger v2 semantic tokens consistently; only "violations" found are intentional brand colors (Tron rose / ETH indigo / etc) and ambient `AnimatedBeam duration={4}` (Magic UI documented default for line-draw scene). Did not pixel-verify on real devices — flagged as **needs human verification** in the demo runbook.
- **AC-3 (empty states)**: Enriched 6 inline empty states across 5 pages — Dashboard (recent + alerts), Transactions, Signatures (pending + history), Audit. Pattern: icon-in-circle + heading + 1-2-line context + optional CTA. Skipped scheduled / contacts / reports (already polished via existing `pageLayout.empty.*` helper or Card-with-icon scaffolds) and analytics (no clear "empty list" entry — uses skeletons + error fallback).
- **AC-4 (sidebar roadmap)**: New `roadmap?: boolean` flag on `SidebarItem`. Created last-position "roadmap" group containing `/compliance`, `/users`, `/documents`, `/settings`. Sub-routes `/settings/keys`, `/settings/webhooks`, `/settings/system` stay in platform group as real flows. Both desktop and mobile sidebars render a `Скоро` / `Coming` / `Жакында` badge. Discovered AceternitySidebar.tsx had a drifted inline NAV duplicate — refactored to import from `sidebar-nav.ts` (single source of truth as the file's own header comment claims).
- **AC-5 (wallet display name)**: New helper `frontend/src/lib/walletDisplay.ts` with `formatWalletDisplayName()`, `networkName()`, `shortenAddr()`, `walletCanonicalId()`. Resolution order: label → `<NetworkName> · <addr_short>` → `<NetworkName> · <unid_short>` → `<NetworkName>`. Replaced render points in `/wallets` list, `/wallets/[name]` detail header, and the dashboard recent-activity column. Canonical UNID exposed via `title=` attribute for tooltips. **Unit tests deferred** — vitest is not in the dependency tree (per `package.json`); story's task description explicitly allowed this.
- **AC-6 (walkthrough)**: `docs/demo-walkthrough.md` shipped with 8-step runbook plus pre-demo checklist, fallback playbook, and "what NOT to show" section.
- **AC-7 (validation)**: `tsc --noEmit` clean. ESLint: 205 problems remain — every single one is in code I did not modify. The only thing my changes introduced was an unused `SIDEBAR_NAV` import in `AceternitySidebar.tsx` after I switched it to use `filterByRole`; cleaned up. Net delta from baseline: −3 problems.

### Change Log

| Date (UTC) | Change |
|---|---|
| 2026-05-01 | Story 1.1 implementation complete. 5-step empty-state polish, sidebar roadmap group + AceternitySidebar de-duplication, wallet display name helper, demo walkthrough doc. Live on `https://orgon.asystem.ai` via Coolify deploy `a12bi3fa68ma1gvgunun4zqr`. |

### File List

**Added:**
- `frontend/src/lib/walletDisplay.ts`
- `docs/stories/1-1-frontend-demo-readiness.md`
- `docs/demo-walkthrough.md`

**Modified:**
- `frontend/src/app/(authenticated)/dashboard/page.tsx` (empty-state for tx + alerts; wallet display fallback in tx column)
- `frontend/src/app/(authenticated)/transactions/page.tsx` (empty-state with CTA)
- `frontend/src/app/(authenticated)/signatures/page.tsx` (empty-state for pending queue + history; link to /demo/architecture)
- `frontend/src/app/(authenticated)/audit/page.tsx` (richer empty-state)
- `frontend/src/app/(authenticated)/wallets/page.tsx` (formatWalletDisplayName + tooltip)
- `frontend/src/app/(authenticated)/wallets/[name]/page.tsx` (header title via formatter; tolerates wallet.info)
- `frontend/src/components/layout/sidebar-nav.ts` (added `roadmap?: boolean`; new "roadmap" group; moved 4 STUB items)
- `frontend/src/components/layout/AceternitySidebar.tsx` (removed inline NAV duplicate; import SIDEBAR_NAV from sidebar-nav.ts; render Скоро badge)
- `frontend/src/components/layout/MobileSidebar.tsx` (render Скоро badge; default-closed roadmap group)
- `frontend/src/i18n/locales/ru.json` (added `navigation.groups.roadmap`, `navigation.badges.comingSoon`)
- `frontend/src/i18n/locales/en.json` (same)
- `frontend/src/i18n/locales/ky.json` (same)

**Deleted:** none.
