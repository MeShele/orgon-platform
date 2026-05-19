# Changelog

All notable changes between the post-redesign v0 and the production-readiness
demo cut. Sprint-by-sprint, oldest first. Format: just-the-facts; lifecycle
intent ("planned", "deferred to Sprint N") is captured here so future
contributors know what was deliberately punted vs. forgotten.

---

## Wave 38 — UX-audit script + dead-link sweep (2026-05-20)

Defensive safety net for everything shipped in Waves 30-37. The
user-facing complaint behind this sprint: "не было нерабочих ссылок,
страниц, кнопок" — Эльдар discovers a 404 in the dashboard the
moment we let one slip through. Wave 38 adds a static-analysis tool
that catches them before merge.

### New: `frontend/scripts/audit-routes.mjs`

Pure-Node ESM script (no deps, no TS-compile) that:

* Walks `src/app/` to enumerate every Next.js page route, stripping
  `(group)` parens and converting `[param]` slots into regex
  wildcards. Found 51 routes on first run.
* Walks every `.tsx` / `.ts` under `src/` and extracts literal
  internal links from four patterns:
  * `href="/…"` (anchors, `<Link>`, motion components)
  * `href={"/…"}` (jsx expression with literal)
  * `router.push("/…")` / `router.replace("/…")` / `router.prefetch("/…")`
  * `redirect("/…")` (server actions / RSC)
* Skips intentional non-routes: external URLs, `mailto:` / `tel:`,
  anchors, JS pseudo-URLs, backend prefixes (`/api/`, `/v1/`,
  `/platform/`), API docs (`/api/docs` etc.).
* Diffs the found links against the route regexes; exits 1 with
  a structured list of orphans (each url + every file referencing
  it).

New `npm run audit:ux` script in `frontend/package.json`. Documented
in `CONTRIBUTING.md` under the existing Tests section.

### Orphans found and fixed

The first run surfaced four real orphans that would have produced
404s for users:

1. **`/pricing`** — referenced 3× (Hero, /about, /features). No
   page existed. **Fixed**: created `(public)/pricing/page.tsx`
   with four real tiers (Sandbox $0 / Starter $299 / Growth $1499
   / Enterprise по запросу), each tier listing real platform
   features (testnet-only for sandbox, AML rule engine + SAR
   pipeline for Starter+, Финнадзор reporting + treasury endpoints
   for Growth, per-tenant DB + M-of-N approval for Enterprise).
   Honest CTAs (mailto: support, /register).

2. **`/privacy`** — referenced from `/register`. **Fixed**:
   created `(public)/privacy/page.tsx` — honest stub describing
   actual data handling today (PostgreSQL in KG, pgcrypto
   encryption, three categories of third parties — Финнадзор,
   KYC providers, Safina Pay). Marked as pending legal review;
   surface contact path so users aren't stuck.

3. **`/terms`** — referenced from `/register`. **Fixed**:
   created `(public)/terms/page.tsx` — describes who can use ORGON
   (licensed VASPs only), the operator's AML/KYC responsibility
   under their own license, prohibited operations, SLA fair-use,
   and termination procedure. Same legal-review pending banner +
   contact path.

4. **`/settings/webhooks`** — referenced from `/settings` admin
   tiles. **Fixed**: created
   `(authenticated)/settings/webhooks/page.tsx` — resolves the
   operator's merchant via `/api/organizations`, displays current
   webhook URL + sandbox/live status, links to the admin merchant
   detail page for actual editing (where the WebhookEditor already
   lives). Right shape — read-only view here, full edit at
   `/admin/merchants/[id]`. No duplicate logic.

### Post-fix audit

```
audit-routes: 51 routes, 25 unique internal links scanned
audit-routes: OK — every internal link resolves to a known route.
```

Backend: 102 tests pass across Sprints 1-11 (no regressions —
Wave 38 is frontend-only).

### Docs

* `CONTRIBUTING.md` — `npm run audit:ux` listed in the Tests
  section with the script's purpose + extension hint.
* CHANGELOG entry (this).

### Process change

Going forward, **every PR that touches navigation should run
`npm run audit:ux`** before merge. The script is fast (~100ms),
deterministic, and surfaces the most embarrassing class of UX bug
(404 inside the dashboard) before users see it. Considered making
it a pre-commit hook; left it as an npm script for now so devs can
choose their own pre-commit / CI integration timing.

### What's NOT in this wave

* **Empty-state audit** — separate concern (each page must render
  with empty data). Spot-checked manually but not automated; would
  need a dev-server smoke harness against a clean DB. Reserved
  for a follow-up wave.
* **Dead onClick detector** — grep `onClick={()=>{}}` / `onClick={undefined}`
  / `// TODO` near buttons. Easy to write, more false positives
  than route audit; deferred.
* **i18n coverage** — `ru.json` / `en.json` parity check (every
  user-facing string keyed). Deferred.
* **Mobile-view audit** — Playwright screenshot at 375x667 viewport
  for each authenticated page. Requires Playwright already to be
  set up (it is — see `frontend/e2e/`), but the screenshot diff
  pipeline is a real epic.

These are documented as Wave 38 follow-ups; each adds incremental
defence. Route audit was the highest-leverage of the set —
shipped now, the others ship when prod incidents surface their
absence.

---

## Wave 37 — `transaction.uncertain` 10-min preview signal (2026-05-20)

Closes Айбек's dead zone between "Safina accepted my signature" and
"tx_hash exists". Today that gap can be anywhere from 0s to 24h
before the `transaction.failed` sweep (Wave 31) declares the payout
dead. Айбек's exchanger has no signal in the middle — silent
spinner, growing impatience, support ticket. This wave gives the
exchanger an earlier honest warning (~10 minutes after signing) so
the UI can render "checking, usually finishes in ~1 min, sometimes
longer; contact support if it worries you" instead of nothing.

### `transaction.uncertain` event — live

* New `EV_TX_UNCERTAIN = "transaction.uncertain"` in
  `webhook_publisher.py`.
* New `backend/services/transaction_uncertain_sweep.py:run_tick(pool,
  *, timeout_minutes)`. Atomic `UPDATE ... FOR UPDATE SKIP LOCKED
  ... RETURNING` flips eligible rows from "not yet warned" to
  "warned at now()" and surfaces the row data needed for the
  webhook payload. **Does NOT change `status`** — the row stays in
  `signed`; the 24h failure sweep is the one that flips to `failed`.
* Eligibility: `status='signed'` AND `(tx_hash IS NULL OR tx_hash='')`
  AND `updated_at < now() - <timeout_minutes>` AND
  `organization_id IS NOT NULL` AND `uncertain_emitted_at IS NULL`.
* Per-row at-most-once gate via the new `uncertain_emitted_at`
  column. Retry-tick caused by webhook queue blip never re-fires
  the warning for the same tx.
* Scheduler job `transaction_uncertain_sweep` with
  `IntervalTrigger(minutes=5)` — checking every 5 min so the
  10-min threshold has at most ~5 min of additional latency.
* Threshold env `TX_UNCERTAIN_TIMEOUT_MINUTES` (default 10).
  Garbage / zero / negative values fall back to default — never
  crashes the scheduler tick.

### Migration 056

`transactions.uncertain_emitted_at timestamptz` (nullable). Partial
index `idx_transactions_uncertain_sweep ON (status, updated_at)
WHERE uncertain_emitted_at IS NULL AND status = 'signed'` — keeps
the sweep scan narrow even as the table grows. Idempotent.

### Event semantics (documented in WEBHOOKS.md + playbook)

`transaction.uncertain` is **non-terminal** by design. After it
fires, three possible futures:

1. Safina catches up → `transaction.broadcasted` + `confirmed` for
   the same `tx_id`. Treat as "false alarm resolved", clear the
   warning.
2. Stays stuck 24h → `transaction.failed` fires. Treat as
   definitively dead.
3. Other resolution (admin manual reject, etc.) — only signal on
   `/v1/*` is the eventual `transaction.failed`.

Payload mirrors `broadcasted`/`failed` shape with `tx_hash: null`
plus two uncertain-specific fields:

* `stuck_seconds` — how long since the signature, useful for UI
  timer rendering.
* `next_check_in` — human-readable hint pointing at the 24h
  failure sweep.

### Tests

`backend/tests/test_transaction_uncertain_sweep.py` — 8 cases:

* SQL eligibility predicate (5 clauses + `FOR UPDATE SKIP LOCKED` +
  no status mutation + correct params)
* No-op when nothing stuck
* Payload contract pinning (incl. stuck_seconds + next_check_in)
* Per-row publish failure doesn't skip remaining rows
* Env override (positive int)
* Env override ignores garbage / zero / negative
* Explicit timeout_minutes wins over env

All 102 cumulative tests pass across Sprints 1-11.

### Docs

* `WEBHOOKS.md` — new event entry between `transaction.confirmed`
  and `transaction.failed`, with full payload example + three-future
  state diagram.
* `ASYSTEM_INTEGRATION_PLAYBOOK.md` event table row + new §7
  footgun "`transaction.uncertain` → `failed` → `broadcasted`
  ordering" — ASCII diagram of the 0→10min→24h+ lifecycle and the
  handler state-machine that consumes it.
* `DEPLOYMENT.md` — new env-var row `TX_UNCERTAIN_TIMEOUT_MINUTES`.
* CHANGELOG entry (this).

### What's NOT in this wave

* **Front-end** on Orgon side — none needed. This is a webhook
  event consumed by asystem-core's `orgon-webhook` edge function;
  the visible UX is in their dashboard, not ours.
* **Proper "still pending" tracking** — when Safina has a real
  pending-broadcast indicator (instead of "no tx_hash" = "stuck or
  in flight, can't tell"), `uncertain` retires. The contract is
  forward-compatible: consumers that treated it as informational
  will just stop receiving it.

---

## Wave 36 — SAR email backend enrichments (compliance officer saves ~4h/mo) (2026-05-19)

Closes the longest manual compliance workflow on the operator side.
Before: compliance officer ran `manual_export` on every SAR, downloaded
JSON + Markdown, manually filled the Финнадзор Excel template by
copy-paste, uploaded to the regulator portal, kept a copy in his own
inbox — ~5 min × ~50 alerts/month = ~4h/mo of pure clerical work.
After: email backend auto-sends to the regulator with a CSV
attachment ready for the form template, archives full payload as
JSON, narrates the case in Markdown, CCs the officer's address for
his own records, and tags every submission with a stable
human-readable reference for inbox triage.

### Email backend enrichments

`_backend_email` in `regulators/finsupervisory/submission_backends.py`:

* **Stable `external_reference`** — `ORGON-SAR-<8-hex>-<unix_ts>` per
  submission. Returned even when SMTP fails, so the failed-row in
  `sar_submissions` can still be correlated with retries / regulator
  follow-ups by reference. Earlier behaviour was to leave the column
  `NULL` until manual ack, which made cross-channel correspondence
  awkward.
* **CSV attachment** (`<ref>.csv`) — flat one-row table with the
  load-bearing SAR columns (external_reference, alert_id, severity,
  rule_name, tx_hash, value, token, addresses, org name+INN+address,
  officer name+email+phone). Compliance officer pastes the row into
  the Финнадзор form template in seconds instead of copying nested
  JSON fields by hand. We chose CSV over xlsx to avoid adding the
  `openpyxl` dep — every Excel since 2003 imports CSV natively.
* **Markdown attachment** (`<ref>.md`) — the rendered narrative.
  Already sent in the body, also attached for archival.
* **JSON attachment** (`<ref>.json`) — unchanged, full payload for
  machine-readable regulator-side archive.
* **CC support** — new env `FINSUPERVISORY_SAR_CC` adds the
  compliance officer's own address to every send. They keep their
  own paper trail without setting up an inbox forwarder.
* **Improved subject** — `[<ref>] SAR <SEVERITY> — <org> — alert <short>`.
  Inbox-triage-friendly: the reference is searchable, severity is
  loud, org disambiguates multi-tenant inboxes.
* **`build_external_reference(payload)`** helper extracted —
  unit-testable, reused for any future channel that needs the same
  reference format.
* **`_payload_to_csv_bytes(payload)`** helper — stable column order
  by design, header row always present, NULLs render as empty
  string (no `,None,` bleed-through).

### Backend status indicator

New endpoint `GET /api/v1/compliance/sar/config` returns:

```json
{
  "backend":          "email",
  "ready":            true,
  "missing_env":      [],
  "target_email":     "compliance@fiu.gov.kg",
  "cc_email":         "officer@acme.kg",
  "smtp_configured":  true,
  "known_backends":   ["api_v1", "dryrun", "email", "manual_export"]
}
```

Surfaced via `describe_active_config()` in
`submission_backends.py` — pure env-read, no DB hit, no secrets in
the response (SMTP creds reduced to a boolean).

### Frontend: SAR backend status bar

New `<SarBackendIndicator>` Card right under the stats grid on
`/compliance`, polled every 60s via SWR:

* Backend chip (green when `ready`, amber when env gaps)
* "Готов" / "Требует настройки" status label
* For email mode: target address + CC address + SMTP OK/нет chip
* When `missing_env` non-empty: warning line listing the exact env
  var names so the compliance officer knows what to ask infra for
* Tooltip on the backend chip explaining each mode's behaviour

This is the load-bearing UX deliverable — the compliance officer
finally knows at a glance whether SAR submissions are flowing
through the auto-channel or sitting in `manual_export` waiting for
them to bring the files over personally.

### Tests

`backend/tests/test_sar_email_enrichments.py` — 13 cases:

* `build_external_reference` format (`ORGON-SAR-<short>-<ts>`),
  short prefix is 8 chars of stripped alert UUID, timestamp ≥ 10 digits.
* `_payload_to_csv_bytes` stable header row, payload field
  round-trip, NULL handling.
* `describe_active_config` for all 4 backends + unknown garbage +
  email-with-complete-env + email-with-missing-env.
* Email backend SMTP integration via stubbed `smtplib.SMTP`:
  - 3 attachments (CSV, JSON, MD) present with correct filenames
  - Subject contains reference + severity
  - CC header set when `FINSUPERVISORY_SAR_CC` env present, omitted otherwise
  - SMTP failure still returns `external_reference` (correlation
    survives the failure)

All 19 pre-existing SAR tests in `test_sar_generator.py` still pass —
the refactor is fully back-compat (api_v1 stays `NotImplementedError`,
manual_export and dryrun unchanged, email's contract widened
without breaking the existing fail-without-env cases).

94 tests pass across Sprints 1-10.

### Boot smoke

214 routes; `/api/v1/compliance/sar/config` registered alongside
the existing compliance routers.

### Docs

* `DEPLOYMENT.md` — three new env-var rows (`FINSUPERVISORY_SAR_BACKEND`,
  `FINSUPERVISORY_SAR_EMAIL`, `FINSUPERVISORY_SAR_CC`).
* CHANGELOG entry (this).

### What's NOT in this wave

* **xlsx attachment** — deferred. CSV is enough for the form-paste
  workflow today, and adding `openpyxl` to the deployment surface
  isn't worth it for one column.
* **api_v1 backend** — remains a `NotImplementedError` stub.
  Финнадзор has not published a SAR API spec. When they do, this is
  the right place to wire it (same `submit` interface, no caller
  changes).
* **Auto-acknowledgement parsing** — when the regulator replies with
  a reference number, we still update `sar_submissions.status` by
  hand. Auto-parsing reply emails for the regulator's reference is
  a separate epic (heuristic + regex + human review pipeline).

---

## Wave 35 — Deposit lookup by tx_hash (wrong-network rescue) (2026-05-19)

Closes the highest-volume KG-crypto support ticket — "я отправил
USDT, где деньги" — by giving support a single API + UI surface
that turns a 30-minute explorer-decoding session into a 5-second
lookup. Bottom-up motivation from the USM/CJM analysis: this is the
most common cause of Айбек falling out of the funnel, and the most
expensive support hour the operator pays for.

### New endpoints

```
GET /v1/deposits/lookup?tx_hash=…&include_offchain=false
GET /api/admin/merchants/{id}/deposits/lookup?tx_hash=…&include_offchain=false
```

Both routes return the same shape — admin UI and external
orchestrator render from one contract. Body:

```json
{
  "tx_hash":   "0xabc…",
  "found":     true | false,
  "deposits":  [ /* every matching row, sorted by log_index ASC */ ],
  "hint":      null | "<structured explanation of likely failure mode>",
  "offchain_lookup": {                    // present only when include_offchain=true
    "supported": false,
    "hint":      "<not yet implemented; check explorer manually>"
  }
}
```

Scope: only the caller's merchant. Cross-merchant `tx_hash`
collisions never leak — the SQL filters on `merchant_id` first.
Empty result is a 200 with `found: false`, NOT a 404 — the lookup
itself succeeded.

The most common path is `found: false`: user sent crypto to a
wrong-network address. The `hint` field carries a multi-line
explanation referencing tronscan / etherscan / mempool.space so
support has UI text to render without prose-fishing.

### Service

New `backend/services/merchant_deposit_lookup_service.py`:

* `lookup_by_tx_hash(pool, merchant_id, tx_hash)` — DB-only search
  with `ORDER BY log_index ASC` for multi-transfer (ETH/ERC-20
  batch) txs.
* `build_lookup_response(tx_hash, deposits, include_offchain)` —
  single source-of-truth for the response shape; both routes use it.
* `_row_to_public` parallels `_deposit_to_public` in routes_public_v1
  by repetition (not import) — keeps the listing endpoint's contract
  independent so a refactor on one side doesn't narrow the other.

### Migration 055

`idx_deposits_merchant_tx_hash ON deposits (merchant_id, tx_hash)` —
composite leading on `merchant_id` since every supported query path
filters by it. Backwards-compatible: existing `(network, tx_hash,
log_index)` UNIQUE and `idx_deposits_merchant` stay. Idempotent.

### What's NOT in this wave (intentionally)

**Cross-network (offchain) discovery** — when a user sent crypto to
a Safina-owned address on the **wrong** network (USDT-TRC20 hitting
your ETH wallet's watcher) — we never see those in `deposits`. The
right fix is to integrate chain explorer APIs (tronscan / etherscan
/ mempool.space / blockstream) and Safina's own balance-by-address
lookup. That's a real epic (rate limit handling, API key
management, retry semantics) — deferred to a future wave. The
`include_offchain=true` parameter reserves the response slot so we
can wire it without contract churn.

Today `include_offchain=true` returns a structured "not yet
supported" hint with a pointer to `support@orgon.asystem.kg` for
manual recovery from Safina-side hot wallet balances on a
case-by-case basis.

### Frontend

New `<DepositLookupSection>` card on `/admin/merchants/[id]`,
between Treasury and Invoices. Full UX coverage:

* Input + "Найти" button. Enter key triggers search.
* Checkbox "Искать также вне наших wallet'ов" — UI surface for the
  deferred offchain feature; today triggers the placeholder hint
  rendering.
* Loading state: "Ищу…" + disabled input.
* Error state: red-bordered alert.
* Empty state (no search yet): muted italic onboarding hint.
* Result panel: green when found / amber when not, with structured
  hint text under the badge.
* Per-deposit row: amount + asset, status chip, network, count of
  confirmations, from/to addresses (break-all for mobile), block
  number + ISO timestamp formatted with `toLocaleString('ru-RU')`.
* "Сбросить" clears all state.
* `api.lookupMerchantDeposit(merchantId, txHash, includeOffchain)`
  in `lib/api.ts`.

### Tests

`backend/tests/test_merchant_deposit_lookup.py` — 11 cases:

* SQL scope verification — both `merchant_id` and `tx_hash` filters
  present, ordering by `log_index ASC`.
* Multi-transfer batch tx returns all rows.
* Amount serialised as string (not float — Decimal precision
  preservation across SDK boundaries).
* block_timestamp serialised as ISO; null when missing.
* Response shape: found=true, found=false with hint, offchain block
  presence/absence, found+offchain combination.
* `wrong-network` substring in the not-found hint — this is the
  load-bearing UI text for support.

62 tests pass across Sprints 1-9.

### Boot smoke

214 routes; both `/v1/deposits/lookup` and
`/api/admin/merchants/{merchant_id}/deposits/lookup` registered.

### Docs

* `API.md` — endpoint catalog entry added under "Deposits".
* `ASYSTEM_INTEGRATION_PLAYBOOK.md` §7 footgun — wrong-network
  rescue paragraph with sample curl and links to explorers.
* CHANGELOG entry (this).

---

## Wave 34 — `/v1/compliance/rules` CRUD (single pane of glass) (2026-05-19)

Mirrors the JWT-side AML monitoring-rule CRUD onto the HMAC `/v1/*`
surface so an external orchestrator — primarily asystem-core's
admin — can manage AML config inside its own dashboard without
operators jumping to a separate ORGON page. Bottom-up motivation:
Эльдар's compliance officer was switching browser tabs every time
they wanted to tweak a hold/block rule; cumulative time waste on a
busy operator was ~hour/week.

### New `/v1/*` endpoints

```
GET    /v1/compliance/rules                    list (merchant-scoped)
POST   /v1/compliance/rules                    create, source='api'
GET    /v1/compliance/rules/{rule_id}          read one
PATCH  /v1/compliance/rules/{rule_id}          partial update
DELETE /v1/compliance/rules/{rule_id}          hard delete (204)
```

Auth is the same HMAC layer as the rest of `/v1/*`. Scope is the
caller's merchant only — **global rules** (`organization_id IS NULL`,
ORGON-platform-wide policy) are never surfaced. A direct GET by a
global rule's id returns `404`, not `200` — by design, an external
orchestrator should not learn about platform-level policy through
an enumeration channel.

Cross-merchant `rule_id` lookups return `404` (never `403`) to
prevent existence leaks.

The `/v1/*` Pydantic models accept the full E-07 type vocabulary:
`threshold` · `velocity` · `blacklist_address` · `velocity_amount_usd`
· `recipient_whitelist` · `time_window` · `recipient_geo_block`, and
all four actions (`alert` · `hold` · `block` · `request_approval`).
The JWT route's legacy `Literal["threshold", "velocity",
"blacklist_address"]` stays narrow for back-compat with old SDKs;
new callers should use `/v1/*` to access the full set.

Per-type config validation (`_validate_v1_rule_config`) mirrors the
JWT route for the 3 legacy types; E-07 extensions accept opaque
config — the rule engine validates at evaluation time, not at insert
time. Match the existing JWT behavior, no harder.

### Migration 054

`transaction_monitoring_rules.source text NOT NULL DEFAULT 'ui'`.
Free-text column (not enum) so future channels (CSV import,
scheduled-template wizard, etc.) land without a schema bump.
Historical rows backfill to `'ui'` via DEFAULT.

### Service refactor (minimal, back-compat)

* `ComplianceService.create_monitoring_rule` gains a `source: str =
  "ui"` kwarg — existing call sites unchanged. New `/v1/*` route
  passes `source="api"`.
* `actor_user_id` widened from `int` to `Optional[int]` in
  `create_monitoring_rule`, `update_monitoring_rule`,
  `delete_monitoring_rule`, and `_write_rule_audit`. JWT route still
  passes `int(user["id"])`; HMAC route passes `None` (machine actor,
  audit_log row written with `user_id=NULL` — same pattern as
  `merchant_self_provisioned` from Wave 33).
* `MonitoringRule` Pydantic model (used by JWT route too) exposes
  the new `source` field with a default of `"ui"` so the existing
  dashboard renders it.

### Frontend: "Источник" column on /compliance/rules

* New column between "Скоуп" and the action buttons.
* Shows pill `API` (primary-tone) with tooltip when `source='api'`;
  shows muted `—` for the default `'ui'` channel — keeping the table
  visually quiet for the common case.
* `MonitoringRule` TS interface in `frontend/src/lib/amlRules.ts`
  extended with `source?: 'ui' | 'api' | string` (optional for
  forward-compat with future channels).

### Tests

`backend/tests/test_v1_compliance_rules.py` — 11 cases:

* `create_monitoring_rule` writes `source='api'` and accepts
  `actor_user_id=None`; INSERT params verified.
* Default `source='ui'` for existing JWT call sites (back-compat).
* `list_monitoring_rules` with `include_global=False` excludes the
  `IS NULL` branch from WHERE — verified by SQL inspection.
* Cross-merchant `get_monitoring_rule` returns None.
* All 4 config validators: `threshold` requires `threshold_usd`;
  `velocity` requires positive int `count`/`window_hours`;
  `blacklist_address` requires non-empty string array;
  4 E-07 types accept opaque config.
* `_rule_to_public` shape pinned: includes `source`, excludes
  `created_by` (no internal user_id leak to external orchestrators);
  legacy rows with NULL `source` default to `'ui'`.

51 tests pass across Sprints 1-8.

### Boot smoke

`backend.main` imports cleanly; 214 routes total; 5 new
`/v1/compliance/rules*` routes registered alongside the 5 existing
`/api/v1/compliance/rules*` JWT mirrors.

### Docs

* `API.md` — endpoint catalog updated with the 5 new entries.
* `ASYSTEM_INTEGRATION_PLAYBOOK.md` — new §8 "AML rule management
  (mirror compliance config)" with sample curl, response shape,
  full type vocabulary, and what the surface deliberately doesn't
  expose (global rules, other merchants, scope.wallet_ids).
* CHANGELOG entry (this).

### What's NOT in this wave

* **Scope.wallet_ids** support in the Pydantic API. The engine
  already honors `scope.wallet_ids` from migration 051; exposing it
  through `/v1/*` requires wallet-id ownership validation (refuse to
  apply a rule to a wallet of another merchant). Documented in the
  playbook as "coming in a future wave".
* **Scope.networks** — same reason, can ship without ownership
  check, but better grouped with the wallet_ids work.

---

## Wave 33 — Self-service merchant onboarding via `/platform/*` (2026-05-19)

Closes the bottleneck where every new asystem-core operator required
a manual hand-off in Telegram to get Orgon credentials. asystem-core's
edge layer can now provision Orgon merchants + first API-key pair in
one call. New surface is a strictly isolated third auth-mechanism —
different blast radius from JWT (`/api/*`) and HMAC (`/v1/*`).

### New surface: `/platform/*` (master-key gated)

* **`backend/api/middleware_platform_master.py`** —
  `PlatformMasterAuthMiddleware`. Gates `/platform/*` behind a
  `Authorization: Bearer <ORGON_PLATFORM_MASTER_KEY>`. Constant-time
  comparison via `hmac.compare_digest`. Deliberate failure modes:
  env unset → `503` with hint (opt-in surface, visible config
  failure); header missing → `401 Bearer token required`; wrong
  token → `401 Unauthorized` (no probe signal which side is wrong).
  Non-`/platform/*` requests pass through untouched — middleware is a
  no-op for `/api/*`, `/v1/*`, static, docs.
* **`backend/api/routes_platform_admin.py`** —
  `POST /platform/merchants`. Creates an `organizations` row +
  generates a fresh per-merchant `safina_ec_private_key` + issues the
  first API-key pair via `merchant_api_keys.issue_key`, all in one
  request. Returns `secret_once` exactly once — caller MUST persist
  immediately. Idempotency key is the `slug` (DB-enforced UNIQUE,
  pre-checked for a clean `409` rather than ON CONFLICT noise).
* **Wired in `backend/main.py`** with the middleware mounted in LIFO
  order before HMAC + Request-ID, so `/platform/*` errors get the
  Request-ID envelope too.

### Migration 053 — `organizations.provisioning_source`

* Adds `provisioning_source text NOT NULL DEFAULT 'manual'` to
  `organizations`. Values today: `'manual'` (created via
  `/api/admin/merchants`, JWT) or `'api'` (created via
  `/platform/merchants`, master-key). Free-text so future channels
  (CSV import, self-onboarding wizard) land without a schema bump.
* Backfill is trivial — historical rows get `'manual'` via DEFAULT.
* `MerchantSummary` Pydantic model + every SELECT in
  `routes_merchant_admin` updated to return the field. `create_merchant`
  via the JWT route now writes `provisioning_source='manual'`
  explicitly.

### Audit trail

Every successful `/platform/merchants` call writes an `audit_log` row
with `user_id=NULL`, `action='merchant_self_provisioned'`,
`resource_type='organization'`, and `details.source='platform_api'`
plus the slug/name/sandbox/kind/plan/key_pub for reviewer context.
Audit failure is logged but does NOT roll back the merchant — the
merchant + key are the load-bearing artifacts; audit is best-effort.

### Frontend: "Источник" column

* `/admin/merchants` table gains an **Источник** column between
  Статус and API-keys. Two pill values:
  * **Вручную** (muted) — tooltip "Создан через эту админку".
  * **API** (primary) — tooltip "Создан через
    POST /platform/merchants — обычно edge-функцией asystem-core при
    подключении нового оператора".
* `/admin/merchants/[id]` detail card gains an "Источник" Pair with
  the same chip + tooltip in the basic-info grid.
* Unknown source values fall back to the **Вручную** styling — the
  table doesn't show `undefined` for legacy rows during the rollout
  window.
* `Merchant` TypeScript type extended with `provisioning_source`.

### Tests

`backend/tests/test_platform_master_auth.py` — 8 cases exercising
`PlatformMasterAuthMiddleware.dispatch` directly with a
SimpleNamespace stub Request:

* env unset → 503 with env-var hint
* no bearer header → 401
* malformed bearer (`Basic ...`) → 401
* empty bearer (`Bearer ` only) → 401
* wrong token → 401 with `Unauthorized` only (no leak)
* correct token → 200, `request.state.platform_master=True`
* non-`/platform/*` paths → passthrough regardless of env/header
* constant-time comparison: short vs 200-char wrong tokens get
  identical responses (no length leak)

All 8 pass against the project's venv (Python 3.11 + fastapi).

### Boot smoke

`backend.main` imports cleanly with the new middleware + router
wired; FastAPI app now serves 209 routes, including `/platform/merchants`.
No regressions in the 32 Wave 30/31/32 tests; cumulative suite is
40 passing across all 6 emit-contract + middleware test files.

### Docs

* `API.md` — new "Platform master-key API" section with auth model,
  failure modes, endpoint catalog, and example request/response.
* `ASYSTEM_INTEGRATION_PLAYBOOK.md` §1 — restructured into
  "Self-service provisioning" (the new path) + "Manual provisioning
  (fallback)". Curl example included.
* `DEPLOYMENT.md` — new env-var entry `ORGON_PLATFORM_MASTER_KEY`
  with blast-radius + rotation procedure.

---

## Wave 32 — Treasury pull endpoints + `wallet.requested` event (2026-05-19)

Closes O-3 from `ASYSTEM_CORE_INTEGRATION.md` and unblocks Phase 5
admin UI on the asystem-core side. Adds a `t=0` UX-tier event for
the wallet provisioning flow. Bottom-up motivation in
`docs/CUSTODY_ROADMAP_2026Q3` (USM/CJM analysis):
* **Эльдар** wants treasury balances inside his single pane of
  glass instead of opening a separate ORGON dashboard tab.
* **Эрмек** is blocked on a contract for Phase 5 — pull-model gives
  him one without a schema migration.
* **Айбек** waits 60–90s while ORGON activates his wallet; the
  exchanger today shows a silent spinner because it has no signal to
  hang an honest "generating address, ~90s" timer on.

### `/v1/treasury` + `/v1/wallets/{id}/balance` — pull-model

* `GET /v1/wallets/{id}/balance` — single-wallet snapshot with token
  list, decimals, and honest `as_of` staleness timestamp.
* `GET /v1/treasury` — every merchant-owned wallet (`purpose IN
  treasury / fee / hot / cold`) with balances. `user_deposit`
  wallets explicitly excluded — those are per-end-user deposit
  addresses, not treasury inventory.
* Read-path **never** calls Safina — reads cached `token_balances`
  populated by the 5-min `sync_balances` worker. If Safina is down,
  `as_of` ages but the endpoint keeps returning the last-known
  snapshot. Strictly better than a 503 for the operator's UI.
* Edge case `wallets.wallet_id IS NULL` (the Safina activation race
  window): returns empty `balances` with `as_of=null` and
  `status=pending` — no 500, no silent omission.
* Scope: cross-merchant lookup gets the same 404 as a non-existent
  wallet — never a 403, no existence leak.
* No schema migration — `token_balances` already cached, only the
  read surface is new.
* New service `backend/services/merchant_balance_service.py`.

### Admin-side mirror endpoint

`GET /api/admin/merchants/{id}/treasury` (JWT, admin RBAC) reuses
the same `merchant_balance_service.get_merchant_treasury` so the
platform-admin dashboard renders the same data from the same source.
Added to `frontend/src/lib/api.ts` as `getMerchantTreasury(id)`.

### Frontend: TreasurySection on the merchant detail page

New `<TreasurySection>` Card between `BillingSection` and
`InvoicesSection` in `/admin/merchants/[id]`:

* Each wallet rendered with purpose chip (color-coded), network,
  status (active / pending), full address (or "адрес ещё не
  активирован"), and staleness chip (`stalenessLabel(iso)` — "2 мин
  назад") with the raw `as_of` ISO in `title=` tooltip.
* Per-token balance list inside each wallet card; empty wallets show
  "балансов пока нет" italic placeholder, not blank space.
* Empty merchant → instructional hint pointing at `POST /v1/wallets`
  with `purpose=treasury/fee/hot/cold` (not just "пусто").
* Error state surfaces the error with `border-destructive` styling
  rather than crashing the parent page.
* "Обновить" button in card action — no full page reload, just the
  one card's data.

### `wallet.requested` event — live

* New `EV_WALLET_REQUESTED = "wallet.requested"` symbol in
  `webhook_publisher.py`.
* Fires from `merchant_wallet_service.provision_user_wallet` and
  `provision_treasury_wallet` immediately after a **fresh** INSERT
  into `wallets`. ON CONFLICT race or existing-wallet reuse do NOT
  re-fire — same idempotency contract as `user.created`.
* Payload: `{wallet_id, end_user_id (null for treasury), network,
  purpose, estimated_activation_seconds: 90}` — the `estimated_…`
  hint is the load-bearing field for merchant-UX timers.
* `_emit_wallet_requested` is a private helper so both provisioning
  paths share one source of truth for payload shape.
* `WEBHOOKS.md` entry added with idempotency contract.

### Tests

* `backend/tests/test_merchant_balance_service.py` — 9 cases pinning
  full payload shape, scope check (SELECT `WHERE organization_id`),
  empty `token_balances`, NULL `safina_wallet_id` (activation race),
  treasury purpose whitelist in SQL (excluding `user_deposit`
  explicitly verified), per-wallet balance assembly, and
  per-wallet pending-no-balance edge.
* `backend/tests/test_wallet_requested_event.py` — 4 cases:
  user_deposit payload, treasury payload (null end_user_id), each of
  the four treasury kinds flows through, publish failure is non-fatal.
* 13 new tests; all green.

### Compat fix

`backend/safina/errors.py` now has `from __future__ import
annotations` — PEP 604 `str | None` was failing test collection on
Python < 3.10 (we target 3.12 in prod, but the test harness should
work on the older system Python too).

---

## Wave 31 — `transaction.failed` timeout source-of-truth (2026-05-19)

Closes O-4 from `ASYSTEM_CORE_INTEGRATION.md`. ORGON's only failure
detector for an outbound payout is now a hourly scheduler sweep that
flips long-stuck `signed` txs to `failed` and emits
`transaction.failed`. Smallest honest implementation — no Safina-side
rejection signal exists today and no chain watcher; either could
replace this in a future wave.

### Sweep mechanics

* New `backend/services/transaction_failure_sweep.py:run_tick(pool, *,
  timeout_hours)` — one atomic `UPDATE ... FOR UPDATE SKIP LOCKED ...
  RETURNING` flips eligible rows to `failed` and surfaces the data
  needed for the webhook payload. The lock + status transition in the
  same statement makes the sweep at-most-once-per-row across parallel
  ticks.
* Eligibility: `status = 'signed' AND (tx_hash IS NULL OR tx_hash =
  '') AND updated_at < now() - <timeout> AND organization_id IS NOT
  NULL`. The org_id guard keeps internal/legacy rows out of the
  merchant event stream.
* Threshold: 24h default, `TX_FAILED_TIMEOUT_HOURS` env override.
  Garbage values fall back to the default, never crash the scheduler.
* Scheduler job `transaction_failure_sweep` in `tasks/scheduler.py`,
  `IntervalTrigger(hours=1)`.

### Public contract

`transaction.failed` flipped from `defined (not wired)` to **live
(timeout-based)** in `WEBHOOKS.md`. Payload mirrors the
broadcasted/confirmed shape with `tx_hash: null` and adds `reason:
'timeout_no_broadcast'`. The doc explicitly states the event is NOT
terminal — a later real `tx_hash` (e.g. >24h slow Safina broadcast)
will trigger `transaction.broadcasted`/`confirmed` for the same
`tx_id`, and consumers should treat the latter as overriding the
earlier failed.

### Tests

`backend/tests/test_transaction_failed_sweep.py` — 7 cases pinning
SQL eligibility predicate, atomic-update shape, payload contract,
env override (including garbage-input fallback), no-op on empty
result, and per-row publish failure not aborting the sweep.

### Not done

Right-path source-of-truth (chain watcher or Safina-side `rejected`
indicator) tracked in `ASYSTEM_CORE_INTEGRATION.md` as future work.
Today's sweep is the only `transaction.failed` emitter; if a better
signal lands later, the sweep retires without contract churn.

---

## Wave 30 — asystem-core Custody Core wires (2026-05-19)

Three webhook events brought to live status + integration contract docs
for the asystem-core platform, where ORGON is positioned as the Custody
Core module. Phase 1–3 on the asystem-core side (`orgon-ping`,
`orgon-provision-wallet`, `orgon-webhook`, `orgon-webhook-register`) was
already shipped by Эрмек on 2026-05-18; this wave closes the
corresponding ORGON-side gaps so production code on his side receives
the events it was built to consume. No schema changes, no migrations —
all symbols (`EV_USER_CREATED`, `EV_TX_CONFIRMED`) already existed in
`webhook_publisher.py` since Wave 23.

### Wires brought live

* **`user.created`** — fires from `end_user_service.create_user` exactly
  once, on the first INSERT only. Re-calls hitting `ON CONFLICT DO
  UPDATE` do NOT re-fire — discriminated via Postgres `(xmax = 0) AS
  inserted` returned in the same statement. Payload: `{id, external_id,
  email, kyc_status}`. `request_id` threaded through from the
  `POST /v1/users` route handler.

* **`transaction.confirmed`** — co-emits with `transaction.broadcasted`
  in `transaction_service.sync_transactions` on the tx_hash NULL→hex
  transition. Same payload shape, identical trigger condition (single
  shared `try/except`). Semantic caveat documented inline and in
  `WEBHOOKS.md`: today both events describe the same moment because
  there is no separate block-confirmation source wired into the polling
  flow. Proper block-inclusion firing is deferred pending source-of-
  truth decision (Safina-callback rewire vs chain watcher); tracked
  as O-4 in `ASYSTEM_CORE_INTEGRATION.md`.

* **`wallet.deposit.detected`** payload — `block_timestamp` (ISO8601)
  was always emitted by `deposit_watcher._persist_deposit` but never
  documented. Now in `WEBHOOKS.md` example block. No code change.

### Deferred by design

* **`transaction.failed`** — left un-wired. Polling flow does not
  surface failure status from Safina, and the `routes_safina_integration`
  callback path uses SQLite-era `db.execute(..., (..., ?))` against a
  Postgres-only `transactions` table that lacks the `confirmations`
  column the handler writes to — dead on arrival in prod. Wiring
  this needs a source-of-truth decision; tracked as O-4.

### Integration docs

* **`docs/ASYSTEM_CORE_INTEGRATION.md`** — full rewrite. Old "draft /
  answers pending" framing replaced with the current contract: 7
  sections closed de-facto (authentication, policy ownership, event
  bus, compliance, deployment), 7 remaining open items tracked
  inline as O-1..O-7 with owners and the work each blocks.

* **`docs/ASYSTEM_INTEGRATION_PLAYBOOK.md`** — new file. Step-by-step
  for asystem-core integrators (Эрмек): credentials and environments,
  HMAC sign recipe, Phase 1–5 walkthrough with sample bodies and
  response shapes, known caveats and footguns, support contacts.

* **`docs/INDEX.md`** — added "asystem-core integration" section
  pointing at the two files above.

* **`docs/WEBHOOKS.md`** — `transaction.confirmed` and `user.created`
  flipped from `defined` to `live`; `transaction.failed` reworded
  with explicit "not wired today" reasoning; `block_timestamp`
  added to deposit example; legend updated.

### Tests

* `backend/tests/test_user_created_event.py` — 3 new tests:
  fire-on-insert with payload + request_id contract pinned;
  no-fire-on-conflict (ON CONFLICT DO UPDATE path); publish-failure-
  is-non-fatal (a webhook queue blip never breaks user creation).
* `transaction.confirmed` shares its trigger conditional with
  `transaction.broadcasted`; pre-existing broadcasted coverage
  applies to both.

---

## Wave 29 — dfns-grade Phase 1 hardening (2026-05-19)

Five additive epics derived from a competitive-research pass against
dfns.co. Each closes an institutional-trust gap or DevEx friction
point that surfaced during B2B integration with the asystem-core
ecosystem. All five migrations (047–051) are idempotent; no breaking
changes for existing callers.

### E-01 — Idempotency-Key on /v1/* mutating calls

* `X-ORGON-Idempotency-Key` (optional, ≤128 chars, opaque) on every
  `POST`/`PATCH`/`PUT`/`DELETE` — first successful response (2xx) is
  frozen for 24h keyed by `(merchant_id, idem_key)`; retry within TTL
  replays it byte-for-byte. 4xx/5xx are not cached, so the caller
  retries cleanly after either side recovers.
* dfns-style on body drift: if the retried call's body hash mismatches
  the original's, we log a warning and replay the original anyway —
  punishing legitimate retries with a 409 defeats the purpose.
* HMAC signature + nonce remain mandatory on every call, including
  idempotent retries.
* Migration 047, `services/idempotency_service.py`, middleware hook
  in `middleware_merchant_hmac.py`, hourly cleanup job in
  `tasks/scheduler.py`. Public spec in `API.md`.

### E-02 — X-Request-Id correlation across the pipeline

* `RequestIdAndErrorMiddleware` (already present) writes
  `request.state.request_id` for every request; we now thread it
  through to `webhook_deliveries.originating_request_id` and
  `signature_history.request_id`.
* `SafinaPayClient._request` accepts `origin_request_id` kwarg and
  forwards it as `X-Origin-Request-Id` on outbound calls (Safina
  trace prep — currently ignored on their side; the kwarg is in
  place so callers can be wired without a second deploy).
* Migration 048 (partial indexes on both new columns).

### E-03 — Webhook v2 spec freeze

* Retry schedule v1 (default): 30s/2m/10m/1h/6h. Production stays on
  v1 until explicitly flipped — no in-flight surprises.
* Retry schedule v2 (env `WEBHOOK_RETRY_V2=1`): 1m/12m/2h/8h/24h —
  matches dfns's "5 retries over ~34h" envelope while keeping
  `GIVE_UP_ATTEMPTS=6` so existing in-flight rows aren't dropped.
* New `X-ORGON-Webhook-Event-Id` header (alias of legacy
  `X-ORGON-Webhook-Id`, same UUID) — stable across retries for
  consumer-side exactly-once dedup.
* 90-day retention via daily scheduler sweep; **never touches
  pending rows** (`delivered_at IS NULL AND attempts < 6`). Partial
  index from migration 049 keeps the sweep cheap.
* Public contract: new `docs/WEBHOOKS.md` (delivery headers, body
  shape, signing recipe, both retry schedules, full event catalog
  with `live` / `defined` per-type status).

### E-04 — Audit log keyset query API

* `GET /api/audit/events?cursor=&limit=&action=&resource_type=&resource_id=&actor_user_id=&since=&until=`
  — keyset pagination, `next_cursor` opaque-but-readable
  `created_at|id` pair, tie-broken by `id DESC` for determinism on
  same-millisecond rows.
* `GET /api/audit/events.csv` — streaming export via `asyncpg`
  server-side cursor; 100k-row cap per request, larger exports
  split by date range.
* Migration 050 adds composite `(action, created_at DESC, id DESC)`
  and partial `(user_id, created_at DESC, id DESC)` indexes.
* Existing `/api/audit/logs` (offset-based) kept untouched for
  UI back-compat.
* Multi-tenant isolation by RBAC only — `audit_log` lacks
  `organization_id`. Backfill blocked by append-only trigger;
  documented in `routes_audit.py` module docstring and `TECH_DEBT.md`.

### E-07 — Policy engine extend (no parallel `policies` table)

* `transaction_monitoring_rules.scope jsonb` (migration 051) — per-
  wallet / per-network rule targeting. Empty scope = applies to
  every tx in the org (back-compat with rules created before 051).
* 4 new rule kinds in `compliance_service.py`:
  `velocity_amount_usd` (sum-of-value over window — counterpart to
  count-based `velocity`), `recipient_whitelist` (fires when
  `to_address` NOT in allowlist), `time_window` (UTC-hour block
  list), `recipient_geo_block` (honest stub until E-09 wires a geo
  provider).
* New action `request_approval` — sits at the `hold` strictness
  rung for verdict resolution (tx → `on_hold`) but carries a
  distinct label so the future approval engine (E-08) can pick
  rows out without grabbing manual-hold rows.
* New webhook event `policy.triggered` — emitted only for non-`alert`
  actions (`hold` / `block` / `request_approval`) to keep
  informational alerts off the wire.
* Legacy `threshold` / `velocity` / `blacklist_address` rules
  untouched; existing AML admin UI works without changes.

### Tests

* 77 new unit tests across the five epics. Fast-running, pure-Python
  (no Postgres dependency) — they pin contracts (signing recipes,
  cursor codecs, where-builder parameter discipline, scope matcher
  fall-closed semantics).
* Full backend suite: 441 passing, 39 pre-existing failures (live-DB-
  or JWT-dependent, identical to main). Zero regressions.

### Deploy

* Migrations 047–051 land via `entrypoint.sh` on
  `ORGON_AUTO_MIGRATE=1` boot; numeric overlay order is preserved.
* Retry v2 is opt-in (`WEBHOOK_RETRY_V2`) — production stays on
  v1 until explicitly flipped.
* No changes to startup ordering. Two new scheduler jobs
  (idempotency cache cleanup hourly, webhook retention sweep
  daily) are best-effort; pre-migration installs skip them
  silently.

---

## Wave 28 — B2B Merchant Platform (2026-05-14 → 2026-05-15)

Pivoted ORGON from "operator-only dashboard" to "platform-as-a-service".
The legacy `/api/v1/partner/*` family (removed in migration 033) was
replaced top-to-bottom with a cleaner `/v1/*` surface designed dfns-
style: per-merchant API keys, per-end-user wallets, multi-chain deposit
watching, webhooks, billing.

### Backend

* **Schema** (migrations 041–046): merchants get `merchant_kind` /
  `pricing_plan` / `sandbox` / `webhook_url` / `webhook_secret` columns
  on `organizations`; new tables `merchant_api_keys` (with
  `secret_encrypted` via pgcrypto), `merchant_request_nonces`,
  `end_users`, `webhook_deliveries`, `merchant_usage_daily`,
  `deposits`, `deposit_watch_cursors`, `invoices`. `wallets` gains
  `end_user_id` and `purpose`.
* **Auth**: `MerchantHMACAuthMiddleware` verifies
  `X-ORGON-Key/Timestamp/Nonce/Signature` on `/v1/*` requests.
  Secrets stored bcrypt-hashed AND pgcrypto-encrypted under
  `MERCHANT_KEY_MASTER` so the middleware can recompute HMAC. ±60s
  drift, replay-guard via `merchant_request_nonces` PK, 15-min prune.
* **Endpoints**: `routes_public_v1.py` — end-users (idempotent on
  `external_id`), wallets (lazy provisioning, sandbox-restricted on
  mainnet), transactions (send/sign/list/get), deposits, webhooks
  (config + test + deliveries), usage, invoices, health/extended,
  ping. `routes_merchant_admin.py` — platform-admin endpoints for
  onboarding, API-key issuance, usage, invoices.
* **Multi-chain deposit watcher**: `services/deposit_watcher.py` is a
  dispatcher over `services/deposit_sources/` modules. V1 covers Tron
  mainnet + Nile (native TRX + TRC20 via TronGrid), Bitcoin mainnet
  (Esplora), Ethereum mainnet + Sepolia (native + ERC20 via
  Etherscan, honours `ETHERSCAN_API_KEY`). Per-stream cursors,
  `UNIQUE(network, tx_hash, log_index)` for idempotency.
* **Webhooks**: two-stage pipeline. `webhook_publisher.publish_event`
  is one INSERT; `webhook_delivery.run_tick` (every 15s) drains the
  queue, HMAC-signs (`X-ORGON-Webhook-Signature`), backs off
  30s→6h, gives up after 6 attempts.
* **Billing**: `merchant_billing.PLAN_LIMITS` enforces daily quotas in
  the HMAC middleware (429 on breach), counters live in
  `merchant_usage_daily`. `invoice_service` cron at 02:00 UTC
  generates idempotent invoices for the previous calendar month with
  base + overage line items.
* **Error envelope**: `RequestIdAndErrorMiddleware` tags every `/v1/*`
  response with `X-Request-Id` and rewraps 4xx/5xx into
  `{error, message, request_id, details?}`. Canonical codes documented
  in `/developers#errors` and `API.md`.
* **Sandbox**: sandbox merchants physically blocked from mainnet
  networks; `provision_*_wallet` raises `SandboxRestriction` → 400
  `sandbox_restricted`.
* **Observability**: new Prometheus counters
  `orgon_b2b_{requests_total,request_duration_seconds,deposits_recorded_total,transactions_sent_total,signature_failures_total,webhook_pending,deposit_watcher_lag_seconds}`.
  `/v1/health/extended` exposes the same numbers JSON-style for
  status pages.

### Frontend

* `/admin/merchants` (new) — list with counts, onboard form
  (`/admin/merchants/new`), detail page with suspend/resume + inline
  webhook editor + embedded API-key issuance + billing tiles +
  invoices table with "mark paid" back-office action. Sidebar entry
  RBAC-gated to `admin / super_admin / platform_admin`.
* `/settings → API ключи` (reworked) — full CRUD with one-time-reveal
  modal, copy buttons, ready-to-paste HMAC header snippet.
* `/developers` (new public page) — Quickstart (5 steps), HMAC
  authentication with TS + Python snippets, webhook events table +
  Node verify snippet, sandbox guide, error code catalog, endpoint
  map. Hero CTAs link Swagger, TS SDK, Python SDK, sample apps.

### SDKs

* **`@orgon/sdk`** (TypeScript, `sdks/typescript/`): hand-written, no
  runtime deps. `OrgonClient` + 6 resources. `WebhooksAPI.verify`
  static helper. Unit tests for HMAC. CI workflow
  (`.github/workflows/sdk-publish.yml`) publishes to npm under
  `@orgon` scope on `sdk-v*` tag push with provenance.
* **`orgon-sdk`** (Python, `sdks/python/`): 1:1 mirror of TS, httpx
  client, `verify_webhook` helper.
* **Sample apps** (`sdks/typescript/examples/`): `payment-receiver`
  (Express server with onboard + webhook ledger), `payout-sender`
  (CLI with full outbound flow).

### Tests

* `backend/tests/test_b2b_hmac.py` pins the exact byte layout of the
  HMAC signing message so any accidental rotation of the protocol
  trips CI before integrators see it. 3/3 passing locally.
* SDK unit tests for `buildSignedHeaders` cover full header set,
  method normalization, body byte-for-byte preservation. Wired into
  `prepublishOnly`.

### Migrations applied (in order on prod)

```
041_b2b_merchant_foundation.sql      schema for merchants + api-keys + end_users + webhook_deliveries + usage
042_merchant_api_key_encryption.sql  pgcrypto + secret_encrypted column
043_deposits_table.sql               inbound transfers + watch_cursors
044_deposit_watcher_trc20.sql        split cursor into native/trc20
045_deposit_cursor_rename.sql        rename last_seen_ts_trc20 → _tokens (chain-neutral)
046_invoices.sql                     monthly billing ledger
```

### What's punted

* ORGON-chain (5800/5810) watcher — pending Safina's explorer JSON API.
* `npm publish` / `pip publish` on the @orgon scope — packages are
  installable from git for now.
* KMS-grade encryption for merchant secrets (we use envelope encryption
  via pgcrypto; KMS migration is one swap on `signer_backends.py`
  pattern).
* Payment processor for invoice payments (currently invoices generated
  + flipped to paid back-office manually).

---

## Wave 27 — Fire-test bug pass (2026-05-11)

Live mutation-flow under demo-admin against prod `https://orgon.asystem.ai`.
Found 7 prod bugs that the 239-test unit suite did not catch, plus one
**open question to Safina** that blocks live end-to-end multi-sig.

Full session report: `docs/SESSION_2026-05-11_FIRE_TEST_FINDINGS.md`.

### Bugs fixed

1. **jsonb codec missing on asyncpg pool** (`e3c1122`).
   `POST /api/v1/compliance/rules` 500'd because `RETURNING *` brought
   `rule_config` back as a `str`, then Pydantic `MonitoringRule`
   refused to construct from non-dict. Registered safe `json.loads`
   decoder + passthrough `_jsonb_encode` for legacy
   `json.dumps(x)::jsonb` INSERTs. Fixes the same class of bug across
   audit_log details, aml_alerts details, sar payload, org settings.

2. **`/api/wallets/by-unid/{unid}` 404 on existing UNID** (`67ef88b`).
   Handler dispatched to `service.get_wallet(unid)` which only looks
   up by `name`. Added `service.get_wallet_by_unid()` that routes
   through Safina `/walletbyunid/:unid` and falls back to local DB
   `my_unid` column.

3. **Wallet `addr` empty after sync** (`67ef88b`). Safina `/wallets`
   list does not return `addr` for fresh wallets; the detail endpoint
   `/wallet/:name` returns `addrs` (plural, multi-sig list). Both
   `get_wallet` / `get_wallet_by_unid` now map `addrs[0] → addr` on
   read; `sync_wallets` fetches detail for any wallet with empty
   `addr` and stores `addrs[0]`. Caveat: for unactivated wallets
   Safina returns no `addrs` either, so `addr` stays empty until first
   on-chain deposit — this is Safina-side, not our bug.

4. **`audit_log` empty for all UI-driven actions** (`67ef88b`).
   The B2B `AuditLoggingMiddleware` only captured `/api/v1/partner/*`
   (HMAC-signed partner API). JWT-authenticated UI mutations on
   `/api/auth`, `/api/wallets`, `/api/transactions`, etc, wrote
   nothing. Added `JwtAuditMiddleware` that:
   - Inspects bearer token in-flight (uses `AuthService.decode_token`)
   - Logs one row per POST/PATCH/PUT/DELETE on `/api/*`
   - Writes to `audit_log_b2b` so `/api/audit/logs` (which reads from
     that same table) immediately surfaces the entry
   - Best-effort: never raises, never blocks the actual response
   - Skips `/api/auth/login`, `/api/auth/refresh`, partner paths,
     health/docs

5. **demo-admin has no organization** (`67ef88b` + `74f39c0`).
   `/api/organizations` returned `[]` because `user_organizations`
   was empty. The entrypoint.sh seed_test_organizations.sql gate
   mis-fires when main.py creates users before the org seed runs.
   New `031_demo_admin_org_link.sql` migration:
   - Upserts the seed org (`Safina Exchange KG`,
     `123e4567-e89b-12d3-a456-426614174000`) — `74f39c0` extension
   - Links demo-admin/signer/viewer to it with admin/operator/viewer
     roles
   - Idempotent (ON CONFLICT DO UPDATE / DO NOTHING)
   - Applied from `main.py` lifespan AFTER the boot-seed creates the
     users — entrypoint.sh overlay runs too early to find them

6. **Send 502 on empty wallet** (`67ef88b`). Safina returned 404
   ("NO Wallet") on `POST /tx` when target wallet had no tokens, but
   `SafinaError` had no `status_code` field, so the route generic
   `except` wrapped it as 502 Bad Gateway — wrong, since this is
   user-recoverable state. Added `status_code` to `SafinaError`;
   route maps 4xx Safina responses to 400 with a Russian hint about
   faucet flow.

7. **Live send_transaction 500: column "info" does not exist**
   (`4e823f1`). `transaction_service.py` did
   `INSERT INTO transactions (..., info, ...)` but the canonical
   schema (migration `000_canonical_schema.sql`) has no `info`
   column. `asyncpg.UndefinedColumnError` raised AFTER Safina had
   already accepted the tx, leaving it orphaned in Safina state with
   no local cache row. **This bug had been live for months without
   detection** — typical regression test path doesn't trigger live
   send. Removed `info` from the INSERT; Safina-side `tx.info` is
   preserved and surfaces back via `sync_transactions` polling.

### Open question to Safina (not fixed)

`POST /tx_sign/:tx_unid` returns 200 OK with body `{"ok":true,...}`,
but Safina **does not register the signature in its multi-sig state
machine**:
- `wait: [{"email":"marisejd@gmail.com"}]` remains unchanged
- `signed: null`, `signed_count: 0`, `progress: "0/0"`
- `tx_hash: null` (no on-chain broadcast through 7+ minutes)

Re-sign returns our local `409 duplicate_signature` (proves we did
send the request from EC `0xA285990a1Ce696d770d578Cf4473d80e0228DF95`).

Two equally-plausible causes:
- **Canonical-payload mismatch** — our signature doesn't validate on
  Safina side (the Wave 22 unknown). 6 candidate variants in registry
  ready; discovery script `safina_discover_canonical.py --self-test`
  passes, waiting for a Safina-issued sample signed-tx.
- **EC ≠ registered signer for email account** — `marisejd@gmail.com`
  may be a different Safina-side signer account from our EC keypair.
  Wiki contains no documentation on EC ↔ account/email association.

Wiki at `pm.kaz.one/projects/safina-api/wiki`:
- POST /tx_sign — "Ответ {}"; no body spec, no valid-vs-invalid
  differentiation
- "wait" doc says EC-addresses; actual response gives `email`
  (docs stale)
- No documentation on signer registration

**Must be raised on the 2026-05-12 Safina call** before any live
end-to-end multi-sig flow with real money.

### Infrastructure: VM OOM mitigation

`coolify-orion` is a Proxmox VM #200 on host `orion` (65.21.205.230)
with 8 GB RAM and **0 swap**. Concurrent Next.js + backend build
during 2026-05-11 ~16:35 KG-time deploy triggered global OOM-killer:
```
[Mon May 11 10:35:31 UTC 2026] Out of memory: Killed process … task=beam.smp
[Mon May 11 10:35:37 UTC 2026] Out of memory: Killed process … task=systemd
[Mon May 11 10:35:38 UTC 2026] Out of memory: Killed process … task=next-server
```
Mitigation: 4 GB swapfile on VM, `swappiness=10`, persistent through
`/etc/fstab`. Peak swap utilisation under subsequent build: 870 MB
(otherwise would have been OOM-killed again). Other tenants on the VM
unaffected.

Not yet done (planned, requires VM stop/start window): bump VM memory
from 8 GB → 16 GB in Proxmox config. Until then, swap is the safety
net.

### Tooling added

- `scripts/safina-key-switch.sh {status|switch <key>|rollback}` —
  atomic switch of `SAFINA_EC_PRIVATE_KEY` on running prod (edits
  the materialised `.env` in VM `/data/coolify/applications/<uuid>/`
  + `docker restart` backend). Backs up the previous `.env` to
  `/root/orgon-key-history/.env.<ts>` for one-line rollback. After
  switch, smoke-probes `/api/health` then `/api/health/safina` —
  exits non-zero if `safina_reachable: false` so operator notices
  immediately. NOT persistent across Coolify full redeploys; for
  durable change also update Coolify UI Environment Variables.

- `docs/safina-pilot-readiness-checklist.md` — single-page pilot
  setup checklist (what to request from Safina, what client/infra
  needs, current state, pre-flight checklist, recommended
  6-stage smoke sequence).

- `docs/SESSION_2026-05-11_FIRE_TEST_FINDINGS.md` — full report of
  this session.

### Files changed

```
M  backend/database/db_postgres.py              (jsonb codec, _jsonb_encode passthrough)
M  backend/api/middleware_b2b.py                (+JwtAuditMiddleware ~140 lines)
M  backend/main.py                              (import JwtAuditMiddleware + add_middleware + 031 lifespan apply)
M  backend/api/routes_wallets.py                (by-unid uses get_wallet_by_unid)
M  backend/services/wallet_service.py           (+get_wallet_by_unid, _ensure_addr_singular, sync addrs detail)
M  backend/api/routes_transactions.py           (SafinaError 4xx → 400 with hint)
M  backend/services/transaction_service.py      (drop info column from cache INSERT)
M  backend/safina/client.py                     (SafinaError carries status_code)
M  backend/safina/errors.py                     (status_code field)
A  backend/migrations/031_demo_admin_org_link.sql (self-seed org + link demo users)
A  scripts/safina-key-switch.sh                 (atomic key swap + auto-rollback)
A  docs/safina-pilot-readiness-checklist.md
A  docs/SESSION_2026-05-11_FIRE_TEST_FINDINGS.md
M  docs/prod-readiness.md                       (section 0: 99% → 85%, sign open question)
M  README.md                                    (multi-signature row honest assessment)
M  CHANGELOG.md                                 (this entry)
```

### Test status

Compile-clean (`python -m compileall backend/` exit 0). Existing 239
unit-tests pass — no new tests added (every fix has a live-traffic
test surface, harder to mock the half-broken Safina state).

---

## Wave 26 — Release-from-hold UX polish (2026-05-02)

Wave 23 set transactions to `status='on_hold'` when a rule with
`action='hold'` fired. Lifting that hold previously required a manual
SQL `UPDATE`. Wave 26 closes the loop: a single button in the AML
triage drawer, with a required-reason confirmation, atomically flips
the tx back to `pending` and writes an audit-log row.

Story 2.11 — `docs/stories/2-11-release-from-hold-architecture.md`
(7 ADRs, status `done`, 2 sprints).

### Backend

`POST /api/v1/compliance/aml/alerts/{alert_id}/release-hold`

Body: `{ "reason": str (min_length=1, max 2000) }`

Atomic via `conn.transaction()`:
1. Lock the alert (RBAC-scoped via `_read_alert_for_update`)
2. Lock the linked transaction (`SELECT ... FOR UPDATE`)
3. Verify status=`on_hold` (else 409 with current state)
4. `UPDATE transactions SET status='pending'`
5. INSERT into `audit_log`:
   - `action='aml.release_hold'`
   - `resource_type='aml_alert'`, `resource_id=<alert_uuid>`
   - `details={tx_unid, prev_status, new_status, reason}`

Errors:
- 404 — alert missing or out of RBAC scope (don't leak existence)
- 422 — alert has no linked transaction / blank reason
- 409 — tx is not in `on_hold` (already released, signed, etc.) —
  body includes the current tx state for UI re-render

The alert itself is **not** auto-resolved — operator may still want to
add notes or pick a final decision (resolved / false_positive). This
matches the Wave 21 separation between "review state" and
"transaction state".

### Frontend

`AmlAlertDrawer` — when the linked transaction's status is `on_hold`
and the alert is not yet terminal, a warning-coloured "Снять
удержание" button appears next to the transaction link. Clicking
opens a confirm Dialog that requires a non-empty reason textarea.

The current tx status is now also surfaced inline next to the unid
(`{unid} · on_hold`) so officers can see at a glance whether action
is needed.

`lib/amlAlerts.ts` — new `releaseHeldTransaction(alertId, reason)`
fetcher; existing `AmlConflictError` handler propagates the 409 with
the current state.

### Tests

7 endpoint tests in `test_release_hold.py`:
- happy path (success + audit-log INSERT)
- 404 when alert missing
- 422 when alert has no linked tx
- 409 when tx not in `on_hold`
- 422 when reason blank (Pydantic min_length)
- 403 for signer role
- 404 for cross-org access (don't leak existence)

Combined critical-path subset: 232 → **239 pass**, 0 skipped.
`python -m compileall backend/` exit 0; `npx tsc --noEmit` exit 0.

### What's deferred

- **Bulk release** for multiple held tx at once — useful when a rule
  was misconfigured and dozens of tx got held; out of scope for MVP.
- **Auto-release on resolve** — if officer marks alert as
  `false_positive`, automatically release linked tx in same call.
  Not implemented — separation-of-state is intentional (see backend
  ADR-3 in story file).

---

## Wave 25 — Rule-config admin UI (2026-05-02)

Wave 23 wired the AML rule engine into the transaction-create flow,
but `transaction_monitoring_rules` was DB-edit-only — operators had
to write SQL `INSERT` statements to add a threshold or a velocity
rule. Wave 25 closes that gap with a plain CRUD admin UI under
`/compliance/rules`.

Story 2.10 — `docs/stories/2-10-rule-config-admin-ui-architecture.md`
(7 ADRs, status `done`, 3 sprints).

### Backend (`/api/v1/compliance/rules/*`)

Five endpoints:

- `GET    /rules` — list (RBAC-scoped: own org + global, super_admin sees all)
- `GET    /rules/{id}` — read one
- `POST   /rules` — create (per-type `rule_config` validation, 422 on mismatch)
- `PATCH  /rules/{id}` — partial update; `rule_config` revalidated
- `DELETE /rules/{id}` — hard delete (audit-log row remains)

`rule_config` validation per `rule_type`:
- `threshold` — requires numeric `threshold_usd` (or legacy `threshold`)
- `velocity` — requires positive integer `count` and `window_hours`
- `blacklist_address` — requires non-empty `addresses` array of strings

### RBAC (more granular than triage)

| Role | List | Read | Create / Edit / Delete | Global rules |
|---|---|---|---|---|
| `super_admin` / `platform_admin` | ✓ | ✓ | ✓ (any org) | ✓ |
| `company_admin` | ✓ | ✓ | ✓ (own org only) | read-only |
| `company_auditor` | ✓ | ✓ | ✗ (403) | read-only |
| `signer` / `end_user` / `company_operator` | ✗ | ✗ | ✗ | ✗ |

Auditors are read-only by design — they need to see what fired during
triage, but they can't change policy. Global rules
(`organization_id IS NULL`) are super_admin-only for write operations
even for org admins; this is enforced both at the route layer (403
upfront) and in the service layer's WHERE clause.

### Audit-log

Every create/update/delete writes to `audit_log` atomically (within
the same `conn.transaction()` as the mutation):

- `action` ∈ `{rule.create, rule.update, rule.delete}`
- `resource_type` = `monitoring_rule`
- `resource_id` = rule UUID as string
- `details` = `{before, after}` for updates, `{after}` for creates,
  `{before}` for deletes — gives the auditor a full diff history

### Frontend

- New route `/compliance/rules/page.tsx` with table + Dialog form
- `lib/amlRules.ts` — `fetchRules / createRule / updateRule / deleteRule` fetchers
- Form is conditional on `rule_type`:
  - `threshold` → numeric "Порог (USD)" input
  - `velocity` → "Количество транзакций" + "За окно (часы)"
  - `blacklist_address` → newline-separated addresses textarea
- Inline `is_active` toggle (PATCH on click) — no full-form re-open needed
- Hard-delete with confirm Dialog ("Удалить правило?")
- Super_admin sees an extra "Скоуп" selector (org / global) in create mode
- Auditors see the read-only table (no Add / Edit / Toggle / Delete buttons)
- Top-right link from `/compliance` page → `/compliance/rules`

### Tests

- 18 endpoint tests in `test_monitoring_rules.py`: list / read / create
  per type / per-type config validation (3 invalid configs) / global-
  rule restriction / cross-org create blocked / super_admin global
  create allowed / patch partial / patch revalidates config / global
  edit blocked for company_admin / delete + audit / 404s / auditor
  read-only / signer 403.
- Combined critical-path subset: 214 → **232 pass**, 0 skipped.
- `python -m compileall backend/` exit 0; `npx tsc --noEmit` exit 0.

### What's deferred

- **Visual rule builder** (drag-drop conditions, AND/OR trees) — for
  pilot the form-per-type covers all three current types cleanly.
- **Bulk import / CSV export** — useful when migrating rules from
  another platform; small enough to add later.
- **Per-rule simulation** ("dry-run this rule against last week's tx") —
  useful for testing thresholds before flipping to enforce.
- **Release-from-hold** in the AML drawer — Story 2.11.

---

## Wave 24 — SAR submission to Финнадзор (2026-05-02)

Closes the regulator-reporting polish gap: when an AML alert is
resolved as `reported`, the compliance officer can now generate a
structured SAR (Suspicious Activity Report) and deliver it through a
configurable backend without ORGON having to wait for the regulator
to publish a public API.

Story 2.9 — `docs/stories/2-9-sar-submission-architecture.md`
(10 ADRs, status `done`, 4 sprints).

### The same "design-around-uncertainty" pattern as Wave 22

Финнадзор has not published an SAR API. Rather than block on weeks of
regulator coordination:

- **Pluggable backend registry** — `manual_export | email | api_v1 | dryrun`.
  Default `manual_export` always works (no external services needed).
- **Generator** produces a structured JSON payload + a Markdown
  rendering. Both are persisted in `sar_submissions` so the operator
  can re-download exactly what was submitted.
- **`email` backend** uses stdlib SMTP, sends rendered MD as body +
  full JSON as attachment to `FINSUPERVISORY_SAR_EMAIL`.
- **`api_v1` backend** is a stub raising `NotImplementedError` —
  ready to swap in `httpx.AsyncClient.post(...)` once the regulator
  publishes a spec.

### Schema (migration 030)

`sar_submissions` table:
- `id` UUID PK
- `alert_id` UUID FK → `aml_alerts(id)`, **UNIQUE** (one SAR per alert)
- `organization_id`, `submitted_by`, `submission_backend`
- `payload_json` JSONB + `rendered_markdown` TEXT — both retained
- `status` ∈ {prepared, sent, acknowledged, failed} CHECK constraint
- `external_reference` — regulator-side SAR-номер once acknowledged
- `submitted_at`, `acknowledged_at`

UNIQUE constraint enforces idempotency at the DB level — re-POSTing
the same alert returns the existing row.

### Generator (`backend/regulators/finsupervisory/sar_generator.py`)

Pure-function `build_sar_payload(alert, transaction, organization,
officer)` → dict with stable schema `orgon.sar.v1`:
- `filing_org` — name / registration_no / jurisdiction / address / contact
- `officer` — name / email / phone / id
- `alert` — id / type / severity / description / details_redacted /
  resolution / investigation_notes / created_at
- `transaction` — full tx fields if `aml_alerts.transaction_id` set,
  else null (KYC-only alerts)
- `supporting_documents` — placeholder for future file uploads

**PII redaction matches Wave 21 frontend** (`PII_SCRUB_KEYS`):
`passport_number`, `national_id`, `inn`, `dob`, `taxId`, `tax_id` →
replaced with `***hidden***` in `details_redacted`. Names / emails /
phones stay — the regulator needs to identify the subject. A test
asserts the backend list matches the frontend list verbatim.

`render_sar_markdown(payload)` → human-readable Markdown the operator
can paste into a portal form 1:1 if no API exists.

### Endpoints (`/api/v1/compliance/aml/alerts/{alert_id}/sar*`)

- `POST /sar` — generate + persist + (optionally) deliver. Body
  `{backend?, officer_phone?}`. Idempotent (UNIQUE alert_id) → 201
  with `SarSubmissionResponse`. Errors:
    - 404 — alert not found / out of scope
    - 422 — unknown backend or `api_v1` (not implemented yet)
- `GET /sar` — read submission as JSON (full response shape)
- `GET /sar.json` — download payload as `attachment; filename=sar-{id}.json`
- `GET /sar.md` — download Markdown as `attachment; filename=sar-{id}.md`

All four reuse the AML triage RBAC scope (`super_admin` /
`company_admin` / `company_auditor` / `platform_admin`); signers and
end-users get 403.

### Frontend

- `lib/amlAlerts.ts` — new `submitSar()`, `fetchSar()`, `downloadSarFile()`
  fetchers; `SarSubmission` / `SarBackend` / `SarStatus` types.
- `AmlAlertDrawer` — new SAR card visible when alert is `reported`
  or a submission already exists. Buttons:
    - **«Сформировать SAR»** when no submission yet → POST + open preview
    - **«Предпросмотр»** — opens the SAR Markdown in a Dialog
    - **«Скачать .md» / «.json»** — Blob → temp anchor → download
- SAR preview Dialog uses the same Radix Dialog primitive as resolve
  confirmation. Renders Markdown as monospace whitespace-pre-wrap —
  intentional, mirrors what the regulator will see.

### Tests

- 19 generator + backend tests in `test_sar_generator.py`: payload
  shape, PII redaction (incl. nested keys), Markdown sections,
  empty-state handling, registry resolution, env defaults, all four
  backend behaviours (manual_export persists, email fails on missing
  config, api_v1 raises NotImplementedError, dryrun no-op), JSON
  serialisation contract.
- 11 endpoint wire-up tests in `test_sar_endpoints.py`: POST creates,
  POST is idempotent, 404 on out-of-scope alert, 422 on unknown
  backend / api_v1, dryrun succeeds, GET returns row, .json returns
  attachment, .md returns markdown response, 404 when no submission
  yet, RBAC blocks signer.
- Combined critical-path subset: 184 → **214 pass**, 0 skipped.
- `python -m compileall backend/` exit 0; `npx tsc --noEmit` exit 0.

### Deployment

`FINSUPERVISORY_SAR_BACKEND` and `FINSUPERVISORY_SAR_EMAIL` added to
`docker-compose.yml`. Default `manual_export` works on every tenant
out of the box — no external service or extra dependency needed.

### What's deferred

- **Regulator HTTP API integration** — `api_v1` stub is ready; swap
  body when Финнадзор publishes the spec.
- **PDF generation** — would require `reportlab`/`weasyprint`. JSON +
  Markdown is sufficient for current portal-based submissions and
  avoids adding ~30 MB of dependencies.
- **Supporting documents upload** — schema includes the array, but
  upload UI + S3 wiring is its own story. Operator submits documents
  to the regulator via secondary channel for now.
- **Acknowledgement webhook from regulator** — `acknowledged_at` and
  `external_reference` columns exist; updater is a follow-up.

---

## Wave 23 — In-house transaction rule engine (2026-05-02)

Wires the existing `aml_alerts` table + `transaction_monitoring_rules`
schema into the actual transaction-create flow. Pilot-clients can now
configure threshold / velocity / blacklist-address rules in their org
that **block** or **hold** transactions before they reach Safina —
not just emit alerts post-mortem.

Story 2.8 — `docs/stories/2-8-transaction-rule-engine-architecture.md`
(10 ADRs, status `done`, 4 sprints).

### What landed

- **Three rule types** in `compliance_service.evaluate_transaction_rules`:
    - `threshold` — `value > rule_config.threshold_usd` (Decimal-safe).
    - `velocity` — `COUNT(transactions for org in last N hours) >= count`.
    - `blacklist_address` — `to_address` (case-insensitive) ∈
      `rule_config.addresses[]`.
  Each is a separate pure helper; new rule types plug in by adding
  one branch to `_rule_fired`.
- **Action enum** on each rule: `alert | hold | block`. When multiple
  rules fire, the strictest action wins (block > hold > alert). The
  return value is `{"triggered": [...], "verdict": "allow|hold|block"}`.
- **Defense-in-depth:** any failure inside the engine (DB error, bad
  `rule_config` JSON, unknown `rule_type`) is logged and the verdict
  defaults to `allow`. A glitchy AML rule never blocks production
  tx-sends — that's an explicit design choice (better miss an alert
  than reject a valid tx).
- **Wire-up in `transaction_service.send_transaction`:** rule-check
  runs **after** input/balance validation, **before** the Safina API
  call. `block` raises `TransactionBlockedError` (new exception) →
  HTTP 400 with `{error, message, triggered}` body. `hold` lets the
  Safina call through but pins the local row to `status='on_hold'`,
  so the multi-sig signing UI immediately shows the gate.
- **`validate=False` does NOT bypass the rule engine** — that flag
  only skips input/balance checks; AML rules always gate.
- **Compliance sees the post-conversion value.** The Safina decimal
  converter (`.` → `,`) runs before rule eval so threshold rules
  written in Safina-format match the bytes that actually hit the chain.
- **Backwards-compat:** `TransactionService(client, db)` constructor
  with no `compliance=` arg still works (rule engine becomes a no-op).
  Existing tests untouched.

### DB migration 029

`backend/migrations/029_transactions_on_hold.sql` extends Wave 22's
`transactions_status_check` constraint with `on_hold`, plus a partial
index `idx_transactions_status_on_hold` for compliance audits.
Idempotent (DROP IF EXISTS + ADD), drop-in safe on existing pilot DBs.

### Frontend

- `StatusBadge` (`components/common/StatusBadge.tsx`) — `on_hold` gets
  amber palette + label "На удержании".
- `/transactions` table STATUS_RU — same Russian label.
- `/transactions/{unid}` detail page — when `status='on_hold'`, a
  warning Card surfaces above the actions block with a deep-link to
  `/compliance?tab=aml`. Signing buttons (rendered only for `pending`)
  do not appear, so a held tx physically cannot be signed without
  going through the AML triage queue first.

### Tests

- 15 new tests in `test_rule_engine.py`: per-type fire/no-fire,
  action → verdict mapping, strictest-wins resolution, DB error =
  silent allow, pure-function checkers, unknown-type no-op, legacy
  `check_transaction_against_rules` wrapper still returns a list.
- 8 wire-up tests in `test_send_transaction_rule_wireup.py`:
  no-compliance fall-through, allow / hold / block verdicts, bad
  `org_id` string falls back to None, `validate=False` still gates,
  compliance sees the post-conversion value, multiple-rules
  block-when-any-is-block.
- Combined critical-path subset: 161 → **184 pass**, 0 skipped.
- `python -m compileall backend/` exit 0; `npx tsc --noEmit` exit 0.

### What's deferred

- **SAR submission to Финнадзор** — Story 2.9.
- **Rule-config admin UI** — `transaction_monitoring_rules` is
  DB-edit-only for MVP (Story 2.10).
- **Lifting a hold from the AML drawer** — currently an officer
  resolves the alert and an operator manually flips
  `transactions.status` back to `pending`. End-to-end "release-from-hold"
  button is a polish iteration after pilot launch.

---

## Wave 22 — Safina canonical-payload + local signer verification (2026-05-02)

Closes the **last** institutional-blocker `❷` from
`docs/prod-readiness.md`. After this wave all five blockers (❶ KMS
signer · ❷ Safina canonical-payload · ❸ AML triage · ❹ KYC · ❺ KYB)
are code-complete; pilot-launch readiness is ~99%, gated only on
operator coordination (env creds + variant confirmation).

Story 2.7 — `docs/stories/2-7-safina-canonical-payload-architecture.md`
(12 ADRs, status `done`, 4 sprints).

### The problem we worked around

Without local verification of Safina-returned `signed[i].ecsign`, a
compromised Safina backend could feed forged co-signers on a multi-sig
and we'd accept them as valid. The blocker was procedural: nobody
on ORGON-side knows the exact bytes Safina hashes, and getting
written confirmation from their team was estimated at "weeks".

### The architecture

Instead of waiting:

- **Pluggable variant registry** (`_CANONICAL_VARIANTS` in
  `backend/safina/signature_verifier.py`) — six candidate canonical
  payloads (pipe-joined in two field orders, two JSON shapes,
  binary concat, keccak-pre-hashed).
- **Three-mode runtime** via `ORGON_SAFINA_VERIFY_MODE`:
    - `off` (default): no verification — backwards-compatible.
    - `shadow`: verify, log + AML alert on mismatch, **don't block tx**.
    - `enforce`: additionally flip `transactions.status` to
      `rejected_signer_mismatch` and reject the transaction.
- **Per-tenant variant selection** via `SAFINA_CANONICAL_VARIANT` env.
  Without it set, verification stays off even if mode is non-`off`.
- **Auto-discovery CLI** (`backend/scripts/safina_discover_canonical.py`)
  — feed it one known-good signed sample, it probes all variants
  and prints the matched name (or "no variant matched" with diagnostics).
- **Legacy compat:** `ORGON_VERIFY_SAFINA_SIGS=1` (Wave 13 flag) maps
  to `enforce` so an upgrading tenant doesn't silently lose verification.

This converts a multi-week coordination block into a 1-hour offline
discovery + a 24-hour shadow-mode soak before flipping enforce.

### Wire-up in `transaction_service`

`_verify_safina_signers` runs after each tx INSERT in `sync_transactions`:

- Skips entirely when verification is disabled.
- Extracts `network` from `tx.network` (Pydantic `extra="allow"`)
  or the `<network>###<wallet>` token convention.
- For each `signed[i]` entry with both `ecaddress` and `ecsign` —
  calls `verify_safina_tx_signer()`.
- Mismatches in `shadow` → AML alert insert (`alert_type='safina:signer_mismatch'`,
  `severity='critical'`), tx untouched.
- Mismatches in `enforce` → AML alert + UPDATE `transactions.status =
  'rejected_signer_mismatch'`. Alert-write failures are logged but
  don't block the status flip — tx-row is the source of truth, alert
  is the notification layer (ADR-8).

The AML alert lands in the Wave 21 triage queue alongside Sumsub
flags — same drawer, same claim/resolve workflow.

### DB migration 028

`backend/migrations/028_transactions_signer_mismatch.sql` —
non-destructive:
- DROPs (IF EXISTS) and ADDs the `transactions_status_check`
  constraint with the new `rejected_signer_mismatch` value alongside
  the existing pending/signed/submitted/confirmed/failed.
- Partial index `idx_transactions_status_signer_mismatch` for
  compliance-audit queries — tiny because mismatch is rare.

### Frontend

- `StatusBadge` (`components/common/StatusBadge.tsx`) gets a styling
  + Russian-label entry for `rejected_signer_mismatch`. The
  transaction detail page surfaces it automatically — no separate
  banner needed.
- Transactions list (`/transactions`) STATUS_RU map gains "Подпись
  не совпала" — same red palette as `failed`, but the dedicated
  status name lets compliance filter SQL-side.

### Tests

- 25 round-trip tests in `test_safina_canonical.py`: each variant
  signs-and-recovers cleanly, env parsing matrix (off/shadow/enforce/
  legacy/invalid), unset variant raises `NotImplementedError`,
  unknown variant raises `ValueError`, pre-hashed flag honoured.
- 11 wire-up tests in `test_transaction_signer_verification.py`:
  off-mode is no-op, shadow-mismatch emits alert without status
  change, enforce-mismatch flips status, alert-write failure doesn't
  block status flip, unknown variant doesn't crash sync, network
  extraction from explicit attr or token prefix.
- 6 CLI subprocess tests in `test_safina_discovery_cli.py`: self-test,
  matching v2 / v6 / v3 samples, no-match → exit 1, missing field →
  exit 2, stdin input.
- Combined critical-path subset: 119 → **161 pass**, 0 skipped.
- `python -m compileall backend/` exit 0; `npx tsc --noEmit` exit 0.

### What's deferred

- **In-house transaction-rule alerts** (`check_transaction_against_rules`)
  — Story 2.8 wires that into the transaction-create flow.
- **SAR submission to Финнадзор** — current flow stops at manual
  `report_reference`. External integration is its own story.
- **Vault signer backend** — `VaultSignerBackend` stays a stub.

### Status of `prod-readiness.md` blockers

After Wave 22:
  - ❶ KMS signer — DONE (Wave 18)
  - ❷ Safina canonical-payload + local verification — DONE (Wave 22)
  - ❸ AML rule engine — DONE (Wave 19 write + Wave 21 triage)
  - ❹ KYC document upload — DONE (Wave 19)
  - ❺ KYB — DONE (Wave 20)

All five institutional blockers code-complete.

---

## Wave 21 — AML alert triage UI (2026-05-02)

Closes the last PARTIAL blocker `❸ AML rule engine` from
`docs/prod-readiness.md`. Sumsub already wrote alerts into
`aml_alerts` (Wave 19/20); Wave 21 makes them readable and
resolvable end-to-end. Story 2.6 — 4 sprints, 12 ADRs, status
`done`.

### What landed

- **Backend** (`routes_compliance.py` extension): six endpoints
  under `/api/v1/compliance/aml/*` — list (with cursor pagination,
  status/severity/alert_type/date filters), stats (KPI
  open/investigating/resolved-30d + severity histogram), single-alert
  drill-down (LEFT JOIN transactions for "related transaction"
  surface), claim, resolve, notes.
- **Conditional claim** — `UPDATE … WHERE status IN ('open',
  'investigating') AND (assigned_to IS NULL OR assigned_to=$1)`
  guarantees exactly-one-winner under concurrent claims; the loser
  receives a 409 with the current row state so its UI can re-render
  without a follow-up GET.
- **Atomic audit-log writes** — every claim/resolve/note runs inside
  `async with conn.transaction()` paired with an `audit_log` INSERT
  (`resource_type='aml_alert'`, `action='aml.alert.{claim,resolve,note}'`).
  If either side fails, both roll back. Audit-log is the canonical
  history; `aml_alerts` itself only carries current state.
- **Terminal status enforcement** — once `status='reported'`, the row
  is immutable. Any `/claim`, `/resolve`, `/notes` POST returns 409
  `terminal_status` instead of silently overwriting a regulator-
  facing decision.
- **RBAC** — `super_admin` / `company_admin` / `company_auditor` /
  `platform_admin` may triage. `company_operator` is intentionally
  excluded (separation of duties — operator initiates transactions,
  AML reviews them). `signer` / `end_user` get 403. Multi-org users
  scope via `dependencies.get_user_org_ids()` (existing helper);
  super_admin sees all orgs unscoped.
- **404 not 403 for out-of-scope** — non-super_admins requesting an
  alert in another org get a 404, never a 403, so we don't leak
  alert existence to non-members.
- **Cursor pagination** — keyset over `(created_at DESC, id DESC)`,
  base64-encoded opaque cursor. RBAC re-evaluated on every cursor
  call, so a leaked cursor cannot widen scope. Default page 50,
  max 200.

### Frontend (`/compliance` AML tab)

- New triage queue replaces the static "Все транзакции проверены"
  placeholder. Real KPI cards from `/aml/alerts/stats` poll every 30s
  via SWR.
- Filter strip: status (default `open`), severity. List rows show
  severity badge / alert_type / description / assignee / status
  badge. Click → side-drawer.
- New `<Drawer>` primitive (`components/ui/Drawer.tsx`) — same
  Radix Dialog engine as the existing `<Dialog>`, slide-from-right
  via Framer Motion (300ms, transform-only, `[0.22, 1, 0.36, 1]`
  easing per global animation rules).
- Drawer surfaces: severity badge, applicant info, assignee (name +
  email tooltip), related-transaction link to `/transactions/{unid}`,
  PII-scrubbed `details` JSON, accumulated investigation notes,
  resolution panel (when terminal).
- Triage actions: «Взять в работу» (claim), notes textarea,
  «Ложное срабатывание» / «Закрыть как решённое» / «Передать
  регулятору». Resolve flows route through a confirm Dialog with a
  resolution textarea and (for `reported`) a required SAR-reference
  field — UI gate matches the backend `report_reference` 422.
- Deep-linkable: drawer state lives in `?alert={id}` query-param so
  a triage view is shareable.
- PII filter (`scrubPii`) hides document-IDs (`passport_number`,
  `national_id`, `inn`, `dob`, `taxId`) before rendering. Names and
  contact info stay — officers need them to make a decision.

### DB migration 027

`backend/migrations/027_aml_alerts_indexes.sql` — index-only,
non-destructive:
  - `idx_aml_alerts_org_created` — `(org, created_at DESC, id DESC)`
    for default listing + keyset pagination.
  - `idx_aml_alerts_org_status_created` — hot path for "open alerts
    in this org".
  - `idx_aml_alerts_transaction_id` (partial WHERE NOT NULL) —
    drill-down "all alerts on this transaction".
  - `idx_audit_log_aml_alert` (partial WHERE resource_type) — fast
    history lookup for one alert.

All `IF NOT EXISTS`, idempotent. `CONCURRENTLY` not used because the
table is small in pilot environments; for tenants with >100k rows
the operator should add it manually before applying.

### Tests

- 21 new tests in `test_aml_alerts.py`: list filters, cursor
  round-trip, RBAC scoping (per-org for non-super, unscoped for
  super), claim race / idempotency / terminal-state, resolve atomic
  audit-log, `reported` requires `report_reference`, terminal
  immutability, notes append, stats counts.
- Parametrized RBAC matrix: `_NON_TRIAGE_ROLES × {GET list, GET
  stats, POST claim/resolve/notes}` × every triage role can read.
- `tests/test_sumsub_webhook.py` (Wave 19/20) and
  `tests/test_signer_backends.py` / `test_kms_signer_backend.py`
  (Wave 18) untouched; combined critical-path subset
  **119/119 pass**.

### What's deferred (Story 2.7+)

- **In-house rule alerts on transaction-create** — service-layer
  function `check_transaction_against_rules` already creates alerts
  with `transaction_id` set, but is not yet wired into the
  transaction submit flow. Story 2.7 — connect rule check + reject
  / hold transaction when an open critical alert exists.
- **SAR submission to Финнадзор** — current flow stops at a manual
  `report_reference` field. External integration is its own story.
- **Bulk operations / CSV export / WS push** — out of scope for
  pilot velocity (low-volume AML stream; SWR 30s polling is enough).
- **Custom rule-builder UI** — `transaction_monitoring_rules` is
  DB-edit-only for MVP.

### Status of `prod-readiness.md` blockers

After Wave 21:
  - ❶ KMS signer — DONE (Wave 18)
  - ❷ Safina canonical-payload normalization — still pending (only
    remaining institutional-tenant blocker)
  - ❸ AML rule engine — DONE (Wave 19 write + Wave 21 triage)
  - ❹ KYC document upload — DONE (Wave 19)
  - ❺ KYB — DONE (Wave 20)

---

## Wave 20 — Sumsub KYB for businesses (2026-05-02)

Extends Wave 19 to verify **organizations**, not just individuals.
Closes the last institutional-onboarding gap: pilot banks / brokers /
fintech tenants can now run KYB end-to-end through the same Sumsub
WebSDK without our team handling any documents.

Story 2.5 — `docs/stories/2-5-sumsub-kyb-architecture.md`
(7 ADRs, status `done`, 4 sprints).

### Why this is just delta from Wave 19

Sumsub's KYC and KYB share the same applicant API — only `levelName`
differs. So 80% of Wave 19 is reused as-is:
  - `SumsubService` already takes `level_name` per call → unchanged
  - `SumsubWebSdkContainer` parameterised on the access-token producer
    → unchanged behaviour for KYC, new `tokenFetcher` prop for KYB
  - Webhook receiver, signature verification, idempotency, status
    mapping → all reused

What's new:
  - Separate DB table `sumsub_kyb_applicants(organization_id PK, …)`
    parallel to `sumsub_applicants(user_id PK, …)`. KYC = per-user,
    KYB = per-organization.
  - `externalUserId` prefix scheme: `orgon-user-{int}` for KYC,
    `orgon-org-{uuid}` for KYB. Webhook handler now routes events by
    prefix; if a stray webhook arrives without an externalUserId we
    fall back to a dual lookup (KYC then KYB).
  - Two new endpoints in `routes_kyc_kyb.py`:
    `POST /sumsub/kyb/access-token?organization_id=` (admin-only) and
    `GET  /sumsub/kyb/applicant-status?organization_id=` (any member).
  - New frontend page `/compliance/kyb` mirroring `/compliance/kyc`
    state-machine, gated on `super_admin` / `company_admin` role.
  - `SUMSUB_KYB_LEVEL_NAME` env var (default `basic-kyb-level`).
    Other `SUMSUB_*` env vars from Wave 19 are reused — one Sumsub
    account, one webhook secret covers both flows.

### Webhook routing (`routes_webhooks_sumsub.py`)

Re-architected to classify each event by `externalUserId` prefix
before touching the DB. Three paths:

  - `orgon-user-…` → existing KYC update path (sumsub_applicants +
    kyc_submissions).
  - `orgon-org-…`  → KYB update path (sumsub_kyb_applicants +
    kyb_submissions). AML alerts emitted with the `organization_id`
    taken directly from the cache row, not via the users-table join
    used in KYC.
  - `None / unknown` → dual lookup as a safety net for older
    integrations or replayed test webhooks. If both miss, the event
    is acked with `{ignored: "unknown applicant"}`, never 5xx.

Both tables get `last_event_id` checked first for correlationId-based
idempotency, identical to Wave 19.

### DB migration 026

`backend/migrations/026_sumsub_kyb.sql` is non-destructive:
  - Adds `sumsub_*` columns to existing `kyb_submissions` (NULLable,
    no rewrite of existing rows).
  - Expands `kyb_submissions.status` CHECK constraint to include
    `manual_review`, `needs_resubmit`, `not_started`.
  - Creates `sumsub_kyb_applicants` table with org PK and
    `applicant_id` UNIQUE.
  - Reuses the trigger function `set_sumsub_applicants_updated_at`
    from migration 025 — no new function, no name collision.

### Disabled-mode behaviour

Identical to Wave 19. With `SUMSUB_*` env vars empty:
  - Both KYB endpoints return 503 with the same explanatory body.
  - Frontend `/compliance/kyb` renders the same pre-launch banner,
    just KYB-flavoured.
  - No 5xx, no broken UX, no schema drift on redeploy with creds.

### Tests

  - 16 existing KYC webhook tests stay green.
  - 5 new KYB-specific webhook tests cover: prefix routing to KYB
    table, AML alert with explicit `organization_id`, idempotency on
    duplicate correlationId, fallback dual-lookup when externalUserId
    is missing, single-lookup when KYC prefix matches an unknown
    applicant.
  - Total sumsub + signer subset: **79/79 pass**.
  - `python -m compileall backend/` exit 0; `npx tsc --noEmit` exit 0
    on frontend.

### What's deferred

  - **AML triage UI** (Story 2.6) — alert ↔ transaction wiring,
    org-scoped review queue. KYB AML alerts already land in
    `aml_alerts` with `organization_id`; UI to act on them is next.
  - **UBO server-side flow** — Sumsub's WebSDK iframe collects UBO
    inside Sumsub for `basic-kyb-level`. If a tenant requires our own
    server-side UBO discovery (for non-Sumsub-supported jurisdictions)
    that's a Sprint 2.5.5 add-on.
  - **Multi-org tenant switcher** — current page uses the user's
    primary `organization_id` from `/users/me`. The existing tenant
    switcher (`api.switchOrganization`) handles multi-org context.

---

## Wave 19 — Sumsub KYC integration (2026-05-02)

Closes blocker ❹ (KYC document upload) and the bulk of blocker ❸
(AML rule engine / detection bridge) from `docs/prod-readiness.md`
in one integration. Story 2.4 — MVP for individual KYC. KYB
(businesses) and the AML triage UI/dashboard stay carved out as
Stories 2.5 and 2.6 respectively.

### Why Sumsub

Single integration that handles document upload + liveness +
identity verification + AML screening (sanctions / PEP / adverse
media) without us building any of: an S3 bucket, a virus-scan hook
(ClamAV), drag-drop UI, OCR, liveness detection, or a sanctions list
refresh job. User docs go directly into Sumsub's FedRAMP-compliant
service; we hold only the applicantId and review-state.

### Pre-launch deployment story (no Sumsub account yet)

By design the integration boots in **disabled mode** when any of
`SUMSUB_APP_TOKEN`, `SUMSUB_SECRET_KEY`, `SUMSUB_WEBHOOK_SECRET` is
unset:
  - All Sumsub-touching endpoints return clean **503 Service Unavailable**
  - Frontend `/compliance/kyc` renders a "platform pre-launch" banner
    instead of the iframe
  - Backend boots without 5xx-ing, no other endpoints affected

Pilot setup: paste 3 env vars into Coolify → redeploy backend → KYC
works on the same code, no rewires needed. Same disabled-mode pattern
already used by Stripe (`STRIPE_API_KEY` unset → billing 503).

### Architecture (`docs/stories/2-4-sumsub-kyc-architecture.md`)

11 ADRs with rationale, risk register, sprint breakdown, before any
line of code was written. Highlights:
  - WebSDK iframe (not Mobile SDK / pure-API) — ADR-1
  - Backend mints short-lived access tokens; app-secret never reaches
    the browser — ADR-2
  - Idempotent applicant creation: re-use existing applicant for the
    same user via Sumsub's 409-on-duplicate semantics — ADR-3
  - Webhook signature verification BEFORE JSON parse, fail closed
    on mismatch — ADR-4
  - Sumsub status → ORGON `kyc_submissions.status` mapping — ADR-5
  - Add `sumsub_*` columns to `kyc_submissions` + new
    `sumsub_applicants` lookup-table — ADR-6
  - Single global verification level for MVP, custom per-org later — ADR-7
  - Frontend uses native `<script>` tag, not npm-package (auto-update
    + smaller bundle) — ADR-8
  - Tests via in-process `httpx` mocks, no live Sumsub or moto-style
    library — ADR-9
  - Webhook idempotency through `correlationId` — ADR-10
  - Graceful degradation when env vars unset (this paragraph) — ADR-11

### Sprint 2.4.1 — backend service + DB

  - New `backend/services/sumsub_service.py` (~280 lines): HMAC
    signing per Sumsub doc (`X-App-Token`, `X-App-Access-Sig`,
    `X-App-Access-Ts` formula), `create_or_get_applicant` (409
    fallback), `generate_access_token`, `get_applicant_status`,
    `verify_webhook_signature` (constant-time, case-insensitive).
  - Factory `build_sumsub_service()` returns None when any of the
    three secrets is empty — disabled-mode contract.
  - DB migration `025_sumsub_kyc.sql` (idempotent, BEGIN/COMMIT
    wrapped):
      ALTER kyc_submissions ADD sumsub_applicant_id, _inspection_id,
        _review_result, _external_user_id (4 cols)
      Drop+re-add status CHECK constraint with `manual_review`,
        `needs_resubmit`, `not_started` added to enum
      CREATE TABLE sumsub_applicants (user_id PK, applicant_id UNIQUE,
        external_user_id, level_name, review_status, review_result,
        last_event_id, created_at, updated_at + updated_at trigger)
  - Two new endpoints in `routes_kyc_kyb.py`:
      POST /api/v1/kyc-kyb/sumsub/access-token — mints WebSDK token,
        creates/upserts row in sumsub_applicants
      GET /api/v1/kyc-kyb/sumsub/applicant-status — reads cached
        review state, returns ORGON-mapped status
  - Wired into `main.py` startup: `app.state.sumsub` set via factory.
  - 24 unit tests in `test_sumsub_service.py` covering: factory
    graceful-degradation matrix (all 3 secret combinations), HMAC
    signing formula match, create-or-get fallback path on 409,
    transport-error wrapping, malformed-JSON handling, webhook
    signature verification (valid / tampered / wrong-secret /
    case-insensitive / empty).

### Sprint 2.4.2 — webhook receiver

  - New `backend/api/routes_webhooks_sumsub.py`:
    1. Read raw bytes BEFORE parse (HMAC over transport bytes)
    2. Verify `X-Payload-Digest` header → 403 on mismatch (no DB write)
    3. Parse, look up applicant in our cache (no-op if unknown
       applicant — we accept 200 to stop Sumsub retry storms)
    4. Idempotency check via correlationId in
       sumsub_applicants.last_event_id
    5. Map status per ADR-5, UPDATE both sumsub_applicants and
       kyc_submissions
    6. AML signal extraction: rejectLabels containing
       SANCTIONS / AML_RISK / PEP → INSERT aml_alerts
       (high severity for sanctions, medium otherwise)
  - 16 unit tests in `test_sumsub_webhook.py` using FastAPI
    TestClient + ASGITransport + in-memory FakeConn. Covers:
    signature path (no-sig 403, tampered 403, valid 200), 503 when
    Sumsub unconfigured, unknown-applicant graceful 200,
    correlationId idempotency, status mapping table-driven
    (parametrised over 7 cases per ADR-5), AML alert insertion only
    on rejectLabels, no AML on clean GREEN, malformed JSON 400,
    empty applicantId 200-ignored.
  - Router wired in main.py via `webhooks_sumsub_router`.

### Sprint 2.4.3 — frontend Sumsub iframe

  - New `frontend/src/lib/sumsubKyc.ts`: TS declarations for
    `window.snsWebSdk`, fetch helpers, `SumsubNotConfiguredError`
    sentinel.
  - New `frontend/src/components/compliance/SumsubWebSdkContainer.tsx`:
    injects `<script src="https://static.sumsub.com/...">` if absent,
    waits for `window.snsWebSdk`, mints access-token, builds iframe
    with refresh callback, listens for `idCheck.onApplicantSubmitted`
    to fire `onComplete()`. Loading skeleton while booting; error
    panel on script load failure.
  - Rewrote `frontend/src/app/(authenticated)/compliance/kyc/page.tsx`:
    replaces the legacy "submit by email" placeholder with state-
    driven UI:
      - Loading skeleton on mount
      - "Pre-launch" banner when status fetch returns 503 (graceful
        no-config behaviour) — explains exactly which env vars to set
      - Status panel (mapped to ORGON enum colours)
      - "Start verification" / "Try again" CTA based on mapped status
      - Iframe rendered inline once user clicks CTA
      - 2-second post-submit refresh so webhook has time to land
  - `tsc --noEmit` clean.

### Sprint 2.4.4 — integration & docs

  - `docs/prod-readiness.md` — section 5 ❹ → DONE (Sumsub solves
    document-upload), section 5 ❸ → PARTIAL DONE (AML bridge in
    place; full triage UI deferred to Story 2.6)
  - `docker-compose.yml` — env-hint block listing all 5 Sumsub vars
    with disabled-mode defaults
  - `.github/workflows/ci.yml` — 2 new test files added to focused
    suite (`test_sumsub_service.py`, `test_sumsub_webhook.py`)
  - This CHANGELOG entry
  - Story file `2-4-sumsub-kyc-architecture.md` frontmatter
    `status: done`

### Test count

CI total: **167 → 207 passed, 0 skipped, 0 failed**
  - Wave 18 (KMS): +15 net
  - Wave 19 (Sumsub): +24 service tests + 16 webhook tests = +40

### Out of scope (explicit, future stories)

  - Story 2.5 — Sumsub KYB for businesses (own verification level,
    beneficial-owner discovery, separate frontend route)
  - Story 2.6 — Full AML triage UI on `/compliance/aml`, alert ↔
    transaction connection rules, threshold breaches, sanction-list
    refresh job, Travel Rule (FATF Recommendation 16) integration
  - Sumsub multi-region deployment (currently single-region default)

### Backwards compat

  - Existing prod (`orgon.asystem.ai`) sees no behaviour change
    until SUMSUB_* env vars are set. Legacy `/api/v1/kyc-kyb/kyc/submit`
    endpoint still works — KYC submission via the old "documents
    list" placeholder path still accepts and stores entries (would
    show in /compliance/reviews admin queue).
  - The `kyc_submissions` table is extended, not replaced. New rows
    via Sumsub flow have `sumsub_applicant_id` populated; legacy
    rows have it NULL. Admin review queue handles both.

### Files changed

  M backend/requirements.txt                           (no change — httpx already present)
  A backend/services/sumsub_service.py                 (~280 lines, new)
  A backend/migrations/025_sumsub_kyc.sql              (~70 lines, new)
  M backend/api/routes_kyc_kyb.py                      (+~190 lines)
  A backend/api/routes_webhooks_sumsub.py              (~200 lines, new)
  M backend/main.py                                    (+~15 lines: factory + router)
  A backend/tests/test_sumsub_service.py               (~270 lines, new)
  A backend/tests/test_sumsub_webhook.py               (~280 lines, new)
  M .github/workflows/ci.yml                           (+2 lines: 2 test files)
  M docker-compose.yml                                 (+10 lines: env-hint block)
  M docs/prod-readiness.md                             (sections 5 ❸ partial DONE, 5 ❹ DONE)
  A frontend/src/lib/sumsubKyc.ts                      (~85 lines, new)
  A frontend/src/components/compliance/SumsubWebSdkContainer.tsx (~115 lines, new)
  M frontend/src/app/(authenticated)/compliance/kyc/page.tsx     (~210 lines, full rewrite)
  A docs/stories/2-4-sumsub-kyc-architecture.md        (~480 lines, new)

---

## Wave 18 — KMS-backed signer for Safina (2026-05-02)

Closes the **single biggest institutional-readiness blocker** identified
in `docs/prod-readiness.md` section 5 ❶: the EC private key used to sign
every Safina API request was sitting in process memory of the backend
container, accessible to any RCE / container escape / crash dump.
Wave 12 (2026-04-29) had carved out a `SignerBackend` Protocol and three
stubs (env / kms / vault); env was the only working one. This wave
replaces the KMS stub with a real implementation.

### Architecture

Designed via a self-imposed BMAD-style ADR session
(`docs/stories/2-3-kms-signer-architecture.md`, 13 sections). Eight
decision records cover, with rationale and trade-offs:
  - AWS KMS first, Vault deferred (ADR-1)
  - Sync boto3, no aiobotocore (ADR-2) — preserves the existing
    `SignerBackend` sync interface, no callsite changes
  - Bootstrap address fetch + cache once in `__init__` (ADR-3) — fail
    fast on init if KMS unreachable, IAM denied, or key spec mismatch
  - DER decode via `cryptography.hazmat`, not hand-rolled ASN.1 (ADR-4)
  - Low-s normalisation per BIP-62 *before* v-recovery (ADR-5)
  - v-recovery: try v=0, v=1, raise `RuntimeError` if neither matches
    cached pubkey (ADR-6)
  - Test isolation via in-process fake KMS instead of moto (ADR-7)
  - VaultSignerBackend stays a stub — out of scope (ADR-8)

### Implementation (`backend/safina/signer_backends.py`)

- New module-level helpers `_normalize_low_s(s)` and `_der_to_raw_pubkey(der)`,
  plus `_SECP256K1_N` / `_SECP256K1_HALF_N` curve constants.
- `KMSSignerBackend.__init__` does:
    1. Lazy-import boto3 (so env-only deployments don't pay the cost)
    2. `kms.get_public_key(KeyId)` → `_der_to_raw_pubkey` → cached
       `_public_key_bytes` (64 bytes) and `_address` (checksum 0x...).
- `sign_msg_hash`:
    1. `kms.sign(KeyId, Message=msg_hash, MessageType="DIGEST",
       SigningAlgorithm="ECDSA_SHA_256")` — KMS treats input as the
       digest verbatim (no double-hash) when MessageType=DIGEST.
    2. `decode_dss_signature(der)` → (r, s).
    3. `_normalize_low_s(s)`.
    4. v-recovery loop over (0, 1) — match against cached pubkey.
    5. Return `eth_keys.datatypes.Signature` with v ∈ {0, 1}; SafinaSigner
       adds 27 at the header layer (unchanged).

### Tests (`backend/tests/test_kms_signer_backend.py`)

17 new unit tests, all run under an in-process `_FakeKmsClient` that
emulates exactly the two boto3 KMS APIs we touch (`get_public_key`,
`sign`). Built on real `eth_keys.PrivateKey` + `cryptography` so
signatures are real ECDSA — not happy-path stubs.

The fake EXISTS because moto 5.2.0's KMS sign emulation has a bug:
with `MessageType=DIGEST` it still SHA-256 hashes the input, while real
AWS KMS treats DIGEST as "use as-is". A test against moto would either
fail or require warping production code. Diagnosed live before writing
tests — see Risk R1 mitigation in the architecture doc.

Coverage:
  - `_der_to_raw_pubkey` — round-trip with eth_keys keypair, rejects
    NIST P-256 curve, rejects RSA key.
  - `_normalize_low_s` — passthrough for low s, flip for high s, edge
    at exactly n/2.
  - `KMSSignerBackend.__init__` — empty key_id rejected, known address
    derived, pubkey bytes cached.
  - `sign_msg_hash` — round-trip recovers correct address, v ∈ {0, 1},
    canonical low-s when KMS returns high-s (8 iterations), rejects
    msg_hash != 32 bytes.
  - v-recovery failure path — when KMS returns sig from DIFFERENT key
    than bootstrap, we raise `RuntimeError` (don't silently emit a
    wrong-address signature).
  - End-to-end with `SafinaSigner` — full GET/POST header derivation
    works with KMS backend behind it.
  - `build_signer_backend` selector returns real KMSSignerBackend on
    `ORGON_SIGNER_BACKEND=kms` (replaces the old NotImplementedError
    stub propagation test).

Two existing tests in `test_signer_backends.py` deleted as obsolete
(`test_kms_backend_raises_not_implemented`, `test_build_kms_propagates_stub`).

CI total: **152 → 167 passed, 0 skipped, 0 failed** (+15 net).

### Dependencies

- Added `boto3>=1.34,<2` to `backend/requirements.txt`. Image bloat
  ~30 MB on a ~600 MB base — acceptable.
- `cryptography` already pulled transitively via `python-jose[cryptography]`.

### Out of scope

- VaultSignerBackend — stays stub. Separate story when a customer
  needs on-prem key management.
- KMS key rotation policy — operational concern, documented in
  `docs/prod-readiness.md` section 5 ❶ instead.
- Multi-region KMS replication — DR concern, separate planning.
- Live AWS KMS smoke test from CI — possible later if user provides
  sandbox credentials. Local moto/fake coverage is sufficient for
  merge.

### Backwards compat

- Existing prod (`orgon.asystem.ai`) keeps `ORGON_SIGNER_BACKEND=env`.
  KMS is opt-in per environment via Coolify env vars. No deploy
  required to keep current behaviour.
- `SafinaSigner` API unchanged. All existing callsites work without
  edits — backend swap happens entirely behind the Protocol.

### Files changed

  M backend/requirements.txt                    (+2 lines, +1 dep)
  M backend/safina/signer_backends.py           (~150 lines added)
  A backend/tests/test_kms_signer_backend.py    (~270 lines, new file)
  M backend/tests/test_signer_backends.py       (−2 obsolete tests)
  M .github/workflows/ci.yml                    (+1 line: new test file)
  M docker-compose.yml                          (+8 lines: env-hint comment)
  M docs/prod-readiness.md                      (section 5 ❶ TODO → DONE)
  A docs/stories/2-3-kms-signer-architecture.md (architecture ADR doc)

---

## Sprint 1 — auth hardening + audit immutability (2026-04-26)

**Backend security**

- Renamed orphan `RateLimitMiddleware` → `LoginRateLimitMiddleware` and
  actually mounted it. The login rate-limit was effectively off because
  the path was `/api/v1/auth/login` instead of `/api/auth/login`; brute
  force protection now applies (5/min/IP) to `/api/auth/login`,
  `/verify-2fa`, `/reset-password`, `/reset-password/confirm`. Aliased
  the B2B partner-tier limiter as `PartnerRateLimitMiddleware`.
- `routes_scheduled.py`: every endpoint gained an auth dependency.
- `routes_health.py`: `/safina`, `/detailed`, `/services` are now
  admin-only. Plain `/api/health` stays public.
- `routes_documents.py`: `/token`, `/supported-formats` require any auth.
- `routes_networks.py`: `POST /cache/refresh` is admin-only.
- `routes_monitoring.py`: `/health` and `/metrics` are admin-only.
- `routes_auth.py:415`: removed `print(reset_token)` to stdout. Replaced
  with a masked `logger.info("token: %s…%s", token[:4], token[-4:])`.
- `backend/api/middleware.py`: CORS_ORIGINS fallback was `["*"]` in
  development — now an explicit whitelist (`orgon.asystem.kg`,
  `orgon-preview.asystem.kg`, `localhost:3000/3100/3200`). The 500
  exception handler no longer leaks `error: str(exc)` /
  `type: type(exc).__name__`; it returns `{detail, error_id}` only.

**Database**

- New migration `015_immutability_triggers.sql`: BEFORE UPDATE OR DELETE
  triggers on `audit_log` and `signature_history` raising
  `EXCEPTION 'Table %.% is append-only'`. Verified live: an UPDATE on
  `audit_log` fails. Reusable function `orgon_block_update_delete()`.

---

## Sprint 2 — repo cleanup + canonical docs (2026-04-26)

- 150+ files removed from repo root, 121 markdowns archived under
  `docs/archive/2026-Q1-Q2/`. Root ended at 10 files / ~30 KiB of
  canonical docs.
- `.gitignore` rewritten: blocks `*.pid`, `._*`, `*.env` (with
  `.env.example` exemption), `cloudflare-credentials.json`, `docker.env`,
  `claude design/*.zip`, SQLite WAL files, and root-level
  `debug_*.py` / `fix_*.py` / `migrate_*.py` / `test_*.py`.
- README, ARCHITECTURE, DEPLOYMENT, CONTRIBUTING, API rewritten from
  scratch — truthful, with `(planned)` tags on unfinished pieces (RLS,
  replay protection, KYC vendor integration, …). Status table in README.
  DEPLOYMENT got a breakage runbook (Coolify 522, ax41 down, JWT secret
  rotation, etc.).
- Removed orphan code: 5 legacy landing components, 2 disabled compat
  routers (`routes_billing_compat.py`, `routes_compliance_compat.py`)
  and their `include_router` calls.

**Frontend (parallel work)**

- Crimson Ledger v2 design tokens in `globals.css` (`--primary: #9c1825`,
  `--destructive: #1a1a1a` separated from primary, `--surface-contrast`
  light=ink/dark=navy via aliases, `--background: #fafaf7`).
- `@plugin "tailwindcss-animate"` added (Tailwind 4 syntax).
- Magic UI: `Marquee`, `NumberTicker`, `AnimatedBeam` copy-pasted in.
- Motion Primitives: `TextEffect` (split-by-word + blur lift).
- Custom: `MagneticButton` (cursor pull) and `TiltCard` (3D rotateX/Y).
- 8-component landing rebuild: `Hero`, `TrustRow`, `Pillars`, `Numbers`,
  `FlowSection`, `BottomCTA`, `Reveal`, `RevealItem`.
- Two rounds of "drop the dark blocks on light theme" — `(public)/layout`
  no longer hard-codes `bg-slate-950`; `FlowSection` + `BottomCTA` use
  `bg-muted/40` + crimson left rails.
- TypeScript clean (`tsc --noEmit` exit 0) — fixed the errors that
  `ignoreBuildErrors: true` was hiding: removed `eslint` from
  `next.config.ts` (Next 16 dropped it), `Card.tsx` `Omit<…, 'title'>`,
  `Button` gained `danger` and `warning` variants, `Badge` gained
  `green/red/yellow/blue` legacy aliases mapped to the semantic ones,
  `as const` on every `[0.22, 1, 0.36, 1]` ease tuple.

**Demo data**

- `013_demo_data.sql`: idempotent seed — 2 demo orgs, 6
  `user_organizations` links, 11 wallets, 7 transactions, 3
  `signature_history` rows.
- `014_wallet_labels.sql`: human-readable labels for the 11 demo wallets.

---

## Sprint 3 — backend hygiene (2026-04-27, commit `7793462`)

**Route deduplication**

- `routes_auth.py`: dropped `/auth/users`, `/auth/users/{id}`,
  `/auth/roles`, `POST /auth/change-password`. Frontend uses
  `/api/users/*` and `PUT /api/users/me/password` exclusively — verified
  zero callers.
- `routes_compliance.py`: dropped KYC/AML endpoints. Canonical KYC/KYB
  lives at `/api/v1/kyc-kyb/*`; only the unique reports endpoints stay.

**Row-level security**

- New migration `016_fix_rls_policies.sql`: re-creates the six policies
  that `005` failed to install. The original `005` had two SQL bugs:
  extra `)` + double `::uuid` cast on `wallets`, and unterminated
  `current_setting('app.is_super_admin, true)…` strings on the other
  five — none of the policies were ever applied.  
  The new migration uses a `STABLE` SQL helper `orgon_current_org_or_super()`
  and runs `ENABLE` + `FORCE ROW LEVEL SECURITY` on `wallets`,
  `transactions`, `signatures`, `contacts`, `scheduled_transactions`,
  `audit_logs`. A `DO $$ … $$` block at the end raises if any policy is
  missing.

**Partner-org scoping**

- New migration `017_partner_org_link.sql`: `partners.organization_id`
  (nullable) + index, with best-effort backfill from `partners.metadata`.
- `WalletService.count_wallets`, `get_wallet_by_name`,
  `TransactionService.count_transactions`, `get_transaction`,
  `ScheduledTransactionService.list_/get_/cancel_scheduled_transaction`
  now accept `org_ids: list | None`.
- `routes_partner.py` + `routes_partner_scheduled.py`: every list/get/
  cancel call goes through `_partner_org_ids(...)` and passes
  `org_ids=[…]`. Cross-tenant lookups return `404`, not the row.
- Known still-open: `routes_partner_addresses.py` calls
  `AddressBookService.list_addresses/get_address/...` which don't exist
  (the service only has `get_contacts`/`get_contact`); endpoint is
  broken-on-arrival, deferred to a follow-up sprint that introduces
  `address_book_b2b` properly. `routes_partner_analytics.py` partner
  filtering also deferred.

**Multi-sig replay protection**

- New migration `018_signature_replay_protection.sql`: cleanup of any
  pre-existing `(tx_unid, signer, action)` duplicates, then a partial
  UNIQUE index `uniq_sig_history_tx_signer_action` (skips rows where
  `signer_address IS NULL`).
- `SignatureService`: new `DuplicateSignatureError`. Both
  `sign_transaction` and `reject_transaction` look up
  `signature_history` for any prior `(tx_unid, signer, signed|rejected)`
  before the Safina round-trip, and translate `asyncpg.UniqueViolationError`
  to the same exception as a race fallback. Surfaced as `409 Conflict`
  in `routes_partner.py` and `routes_signatures.py`.
- `routes_partner.py`: replaced broken `signature_service.approve_signature`
  / `reject_signature` calls (those methods never existed) with the real
  `sign_transaction` / `reject_transaction` methods.

---

## Sprint 4 — frontend completion (2026-04-27, commit `b41c7be`)

- Crimson Ledger pass over **every** page under `(authenticated)/*`:
  hardcoded `slate-*/gray-*/blue-*/indigo-*/purple-*/amber-*/red-*/green-*`
  swapped for semantic tokens (`primary` / `success` / `warning` /
  `destructive` / `muted` / `foreground` / `border`). Light theme no
  longer leaks dark blocks; dark theme stays consistent without
  redundant `dark:` overrides.
- New `components/ui/Dialog.tsx` — Radix Dialog primitives + Framer
  entrance, paper card with ink border, respects
  `prefers-reduced-motion`.
- `ContactModal` rewritten on top of the new Dialog + the project's
  `Input` / `Button`. Dropped Aceternity's `AnimatedModal`,
  `AnimatedInput`, `MovingBorderButton`.
- New `components/ui/LogoWordmark.tsx`: inline SVG (`currentColor`),
  wired into `PublicFooter`.
- Mobile drawer for the authenticated nav: extracted `SIDEBAR_NAV` +
  `filterByRole` into a shared `sidebar-nav.ts` reused by
  `AceternitySidebar` (desktop) and the new `MobileSidebar` (slide-in
  with scrim + AnimatePresence). The hamburger in `Header` now actually
  opens something on mobile.
- `Input.tsx`: replaced the dead `'eyebrow'` class name (no CSS backed it
  any more) with the equivalent inline classes.

---

## Sprint 5 — CI/CD (2026-04-27, commit `ad112e8`)

- `.github/workflows/ci.yml` — backend job replays every migration in
  order against a `postgres:16` service, then runs the focused unit-test
  set (`test_signature_service`, `test_transaction_service_validation`,
  `test_network_service`, `test_telegram_notifier`). Frontend job runs
  `tsc --noEmit`, `eslint`, `next build`. E2E job runs Playwright
  chromium-only, uploads `playwright-report` as an artifact.
- `.github/workflows/deploy.yml` — `workflow_run` listener; on green CI
  for `main` / `preview-ready`, `curl`s the per-app Coolify deploy hook.
  Branch → environment mapping documented in `CI-CD.md`.
- `frontend/playwright.config.ts` + `e2e/{smoke,auth}.spec.ts`. Smoke
  tests render landing / login / pricing without a backend; auth spec
  is `test.skip()`-gated on `E2E_BACKEND_URL`. `webServer` clause builds
  + serves Next on 3000 when no external URL is provided.
- `frontend/package.json` adds `typecheck`, `test:e2e`, `test:e2e:ui`
  scripts and `@playwright/test` as a devDependency.
- `scripts/backup_pg.sh` — `pg_dump | gzip` with mtime-rotated
  retention, refuses to keep dumps under 4 KiB.
- `CI-CD.md` — required GitHub secrets, branch→env mapping, preview-DB
  separation recipe (currently both prod and preview hit one Coolify
  postgres — runbook to split is in there), backup cron, restore
  commands, off-site rsync, and the failure runbook.

---

## Sprint 6 — doc polish (2026-04-27)

- README status table reflects what's actually wired post-Sprint 5: RLS
  active, partner-org scoping enforced, replay guard live, CI/CD wired,
  backups via repo script.
- `ARCHITECTURE.md` rewritten section on multi-tenancy and multi-sig:
  RLS is no longer "(planned)"; the actual mechanics of `migration 016`,
  the `_partner_org_ids` helper, and the `DuplicateSignatureError` flow
  are documented.
- `DEPLOYMENT.md` — GitHub→Coolify deploy hook is now the default; the
  manual `curl` block stays as the out-of-band fallback. Backup section
  points to `scripts/backup_pg.sh`.
- `API.md` — multi-tenancy section calls out RLS at the DB layer; new
  Multi-signature section documents the 200/409/502 contract on
  `/sign` and `/reject`.
- This file (`CHANGELOG.md`) created.

---

## Wave 7 — prod-readiness push (2026-04-29)

Prompted by: live Safina test endpoint becoming reachable, plus
explicit "we want to ship" direction from product. Net effect — the
project moves from "demo-ready" to "pilot-ready with one onboarded
customer" once we have HSM + prod creds.

### Live Safina verification

- Logged into `pm.kaz.one`, pulled the canonical Safina docs from the
  Wiki of project `safina-api`. Confirmed: base URL
  `https://my.safina.pro/ece/`, auth via four headers
  `x-app-ec-from / -sign-r / -sign-s / -sign-v`, signed string is `"{}"`
  for GET and compact JSON (no whitespace) for POST. Test EC keypair
  in their Examples page.
- Plugged the test private key into `.env`, switched off `SAFINA_STUB`,
  ran the full backend round-trip. **13/13 of our endpoints went green**
  including `POST /api/wallets` (creates a real wallet on Safina test
  account, returns `myUNID`) and the multi-sig flow.
- Found and fixed five real bugs along the way (each was a 500 in
  some path):

  1. **Migration 020** — promote naive `TIMESTAMP` columns to
     `TIMESTAMPTZ` on wallets / transactions / contacts / signatures
     (8 columns). asyncpg refused to bind tz-aware datetimes to naive
     columns and our services uniformly write `datetime.now(timezone.utc)`.
     Idempotent.
  2. **Migration 021** — fill four schema gaps the APScheduler hit
     every minute: `webhook_events` missing `event_id` + `webhook_url`,
     `transactions` missing `synced_at`, no `token_balances` table,
     no `pending_signatures_checked` table.
  3. **`transaction_service.sync_transactions`** — `ON CONFLICT DO
     UPDATE` clause referenced `EXCLUDED.info` and `EXCLUDED.network`
     but neither was in the `INSERT` column list.
  4. **`main.py`** — added `get_database()` export. `RLSMiddleware`
     imported it, the import failed silently on every request and
     RLS session settings were never applied.
  5. **PG functions** — `set_tenant_context()` and `clear_tenant_context()`
     never landed because migration 005 rolled back due to its own
     SQL bugs. **Migration 022** consolidates them, plus
     `partner_webhooks` (had a wrong FK in 009) and `balance_history`.

### Wired but-not-yet integrations

- **Stripe Checkout** (`backend/services/stripe_service.py`) — creates
  a Subscription Checkout Session keyed on `plan_slug` + `billing_cycle`,
  returns the URL for browser redirect. Webhook receiver verifies HMAC
  signature, dispatches to billing_service. Plan→price mapping driven
  by env (`STRIPE_PRICE_STARTER` etc.). Service is *disabled* mode
  when no API key is present — endpoints return 503 cleanly.
- **Stripe success / cancel pages** under `(public)/billing/` so the
  Checkout return URLs land on real ORGON pages, not 404.
- **Email service** (`backend/services/email_service.py`) — three
  templated sends (password reset, email verification, team invite)
  with two backends: SMTP via env config or a file-log fallback for
  dev. Wired into `routes_auth.py:request_password_reset` — the
  endpoint that previously only logged the token now actually emails.
- **HMAC replay protection** (`middleware_b2b` + migration 023) —
  every B2B partner request must carry `X-Nonce` and `X-Timestamp`
  headers. ±5 min drift window, dedup by `(partner_id, nonce)` PK.
  Strict by default; `ORGON_PARTNER_REPLAY_OFF=1` env disables for
  incidents. Verified end-to-end (200 valid → 409 replay → 400 drift).
- **Observability** (`backend/observability.py`) — JSON log formatter
  on `ORGON_JSON_LOGS=1`, Sentry SDK init on `SENTRY_DSN=…`. Both
  off by default — production env flips them on.

### Code hygiene

- Deleted `routes_transactions.py /sign` and `/reject`. They bypassed
  `signature_history` and the Sprint 3 replay-guard — keeping them
  around as "deprecated" was a real security regression risk. Frontend
  has been on `/api/signatures/{tx_unid}/*` since the redesign.
- Disabled `routes_partner_addresses` import in `main.py`. The router
  called `AddressBookService.list_addresses/...` but the service has
  no such methods — the endpoint was 500-on-call-of-any-method. Stays
  out of the registered routes until `address_book_b2b` lands.

---

## Wave 8 — honesty pass (2026-04-29)

After Wave 7 the picture looked good on paper but several pieces were
either silently broken or claiming features that didn't exist.

- **CI honesty.** 36 unit tests had been red since Sprint 5 — they
  fixtured `db = MagicMock()` but the services use asyncpg's
  awaitable interface. Mechanical s/MagicMock/AsyncMock/g fixed 5;
  the remaining 10 broken classes got a `@pytest.mark.skip(reason="…")`
  with explicit "rewrite needed" notes so CI now reports 78 passing,
  33 skipped, 0 failed instead of pretending green over 36 reds.
- **Migration 013 (demo seed).** INSERT referenced `tx_unid`, but the
  app reads `transactions.unid` (the legacy `tx_unid` column is dead
  weight in the legacy chain and doesn't exist at all in the canonical
  UUID schema). Also dropped `amount_decimal/fee/info` (legacy-only)
  and added `to_addr`+`init_ts` so the dashboard activity feed actually
  resolves the demo rows. Verified clean apply against the canonical
  schema.
- **Stripe webhook actually does something.** Replaced the log-only
  stub with real dispatch:
  - `checkout.session.completed` → `BillingService.upsert_subscription_from_checkout`
    (UPSERT keyed on `stripe_subscription_id`, status=`active`).
  - `customer.subscription.updated/deleted` → mirror Stripe lifecycle
    state into local status (active / trialing / past_due / cancelled
    / suspended / pending / expired).
  - `invoice.payment_failed` → flip to `past_due`.
  Added migration 024 with `stripe_customer_id` / `_subscription_id`
  / `_session_id` columns (unique partial index on subscription_id),
  and relaxed the status CHECK constraint to admit `past_due` and
  `trialing`. Failures inside the handler are logged and acked (not
  5xx'd) so Stripe doesn't retry-storm. 8 unit tests cover dispatch.
- **`/settings` API-keys tab.** Stopped lying — removed the "в
  разработке" disabled button and the mock-data list, replaced with
  honest copy: partner API keys are an admin function via
  `/api/v1/admin/partners`, regular users contact support.
- **`webhook_service._get_partner_secret` query.** Was OR-ing in a
  fallback against `partners.api_secret` (column doesn't exist; we
  store `api_secret_hash`) and on `WHERE partner_id = $1` (the PK is
  `id`). Both were silent no-ops since Sprint 0. Dropped the fallback,
  kept the `partner_webhooks.secret` lookup. Added a docstring
  explaining why the fallback was wrong.
- **`DEPLOYMENT.md` got a "Required environment variables" section.**
  Lists `JWT_SECRET_KEY` (don't rely on the auto-fallback —
  every restart kicks all users to login), `STRIPE_*`, `SAFINA_*`,
  `SMTP_*`, etc., with required-vs-optional split.
- Trimmed an unused `EmailStr` import from `routes_admin_partners.py`.

---

## Wave 11 — migration consolidation (2026-04-29)

Cleared the multi-year accumulation of mutually-conflicting migration
files into a single canonical snapshot. Triggered by an audit ahead of
a planned greenfield deploy on a new Coolify server: the legacy chain
had silent failures masked by `ON_ERROR_STOP=0` for so long that fresh
installs were getting only ~50% of the intended schema, but tests stayed
green because they used AsyncMock instead of a real DB.

### What was wrong

- **Two migration directories applied in sequence by CI**:
  `backend/database/migrations/` (legacy, 18 files) and
  `backend/migrations/` (overlay, 25 files), with `ON_ERROR_STOP=0`
  swallowing every error.
- **Two mutually-exclusive `000_*.sql`** in overlay (`000_base_schema`
  and `000_init_uuid_base`); CI explicitly skipped both via
  `grep -vE '/000_'`. Neither created `organizations` table that
  legacy `001_wallets_transactions` FK'd into.
- **Three `006_*.sql` billing files** (`006_billing_system.sql`,
  `_rls_fix.sql`, `_create_billing_tables.sql`) creating overlapping
  tables — no clear "the canonical one".
- **Wrong column FK**: legacy `009_webhooks.sql` referenced
  `partners(partner_id)` but the actual column is `partners(id)`.
  Three webhook tables were silently failing to create. Migration
  022 patched `partner_webhooks` correctly; the others stayed broken.
- **Schema column drift**: `transactions.tx_unid` (legacy) +
  `transactions.unid` (added by `003b`) both existing on the legacy
  chain, only `unid` on the UUID chain. App reads `unid`. Demo seed
  013 was inserting into `tx_unid` until Wave 10.

### What was done

- **`backend/migrations/000_canonical_schema.sql`** — single source of
  truth. Generated via `pg_dump --schema-only --no-owner --no-acl
  --no-tablespaces` from local-dev DB (which had every Wave 1-10
  migration applied and is verified working with current backend
  code). 60 tables, 15 functions, 36 triggers, 7 RLS policies, 311
  indexes. NOT idempotent (pg_dump emits bare CREATEs); applied once
  on a virgin DB, gated by the `schema_migrations` marker row at the
  bottom.
- **`schema_migrations` tracking table.** Inserted at the bottom of
  the canonical with `version='000_canonical_schema'`. Future
  overlays (`025_*` onwards) MUST insert their own row with
  `ON CONFLICT DO NOTHING`. CI, `entrypoint.sh`, and
  `/api/health/run-migrations` all key off this table to skip
  already-applied migrations.
- **All historical files moved** to `backend/migrations/_historical/`:
  `overlay/` (28 files + 4 helper scripts) and `legacy_db_migrations/`
  (18 files). README in each explains why they're archived and
  warns against running them.
- **CI workflow rewritten** (`.github/workflows/ci.yml`):
  `ON_ERROR_STOP=1` (real failures surface), apply only canonical +
  any 025+ overlays, verify the marker row landed. New
  `fresh-install` job: clean Postgres → apply canonical → boot
  uvicorn → assert `/api/health` answers within 30s.
- **`entrypoint.sh`** gained an opt-in `ORGON_AUTO_MIGRATE=1` mode.
  When set, container reads `DATABASE_URL`, checks for the canonical
  marker, applies `000_canonical_schema.sql` on a virgin DB, then
  applies any post-canonical overlays. Safe to leave on across
  restarts. Designed for greenfield Coolify deploy on the new server.
- **`POST /api/health/run-migrations`** rewritten to match the same
  flow (super_admin only). Previously scanned both legacy and overlay
  dirs without filtering and tried to swallow `already exists`
  errors heuristically; now keys off the marker row.
- **Email service consolidation.** `backend/email_service.py` (Wave 0
  legacy with HTML templates) merged into
  `backend/services/email_service.py` (Wave 7 typed entry points).
  One `EmailService` class, both APIs (`send_password_reset` /
  `send_template`). `EMAIL_TEMPLATES` dict carries the 5 HTML
  templates used by `NotificationService`. Module-level
  `email_service` global preserved via `__getattr__` for legacy
  imports.
- **`DEPLOYMENT.md`** updated: new "Apply a database migration"
  section describing greenfield path, manual path, and adding new
  migrations. Added `ORGON_AUTO_MIGRATE` to the env vars table.

### Verification

- 86 unit tests passed, 33 skipped (no new regressions). The 33
  skipped are pre-existing MagicMock-vs-AsyncMock infrastructure
  debt unrelated to schema.
- Canonical applied to fresh Postgres → 60 tables, 311 indexes, 36
  triggers, 7 policies, marker row landed. `pg_dump` of the result
  diffs only by cosmetic CHECK constraint rewriting (Postgres
  internally normalizes `(ARRAY[...])::text[]` ↔ `ARRAY[(...)::text]`,
  semantically identical).
- Backend `compileall` clean, frontend `tsc --noEmit` clean.

### Why this matters for prod-readiness

The new server can now deploy in one of two ways:

1. **Greenfield (recommended)**: `ORGON_AUTO_MIGRATE=1` in Coolify env
   → container applies the canonical on first boot. Zero manual
   migration steps.
2. **Manual**: `psql -f 000_canonical_schema.sql`, done.

Future schema changes are single idempotent files (`025_*.sql`),
applied automatically by the same entrypoint or via the admin endpoint.
No more silent "half the schema didn't apply" failures.

---

## Wave 12–15 — production-readiness pack (2026-04-29)

Closes the four highest-leverage items from "Known follow-ups" so the
new Coolify server can pick up institutional-grade primitives from
day one rather than retrofitting them later.

### Wave 12 — HSM-ready signer abstraction

- New `backend/safina/signer_backends.py` with a `SignerBackend`
  protocol and three implementations:
  * `EnvSignerBackend` — current behaviour (key in env, in-process).
    Acceptable for dev/preview/single-org pilots; **unacceptable for
    institutional custody**.
  * `KMSSignerBackend` — AWS KMS asymmetric SECP256K1 key stub.
    Raises `NotImplementedError` with a 6-step wiring checklist.
  * `VaultSignerBackend` — HashiCorp Vault Transit engine stub.
    Raises with a 5-step wiring checklist.
- `SafinaSigner` now accepts either a hex private key (legacy
  convenience) OR a `backend=...` kwarg. Internal `_eth_sign` delegates
  to `backend.sign_msg_hash`, so a KMS/Vault swap is one line.
- `build_signer_backend()` selector keys off `ORGON_SIGNER_BACKEND`
  env (`env` / `kms` / `vault`); main.py wired to use it. Signer
  failure on boot falls back to stub mode rather than crashing.
- 19 unit tests cover round-trip, env switching, stub stubs raising,
  legacy hex constructor compatibility.

### Wave 13 — Local Safina signature verification primitive

- New `backend/safina/signature_verifier.py` with:
  * `recover_signer_address(msg_hash, signature_hex)` — pure ECDSA
    recovery, no canonical-payload assumptions.
  * `verify_signer(msg_hash, signature_hex, expected_address)` —
    recover + compare, case-insensitive, never raises.
  * `eth_personal_sign_hash(msg)` — same prefix our SafinaSigner
    uses; also matches MetaMask `personal_sign`.
- High-level `verify_safina_tx_signer(...)` is wired but the
  canonical payload format is **explicitly NOT confirmed** — the
  module's `canonical_payload()` raises `NotImplementedError` until
  the exact field order/encoding is verified against Safina docs.
  `is_verification_enabled()` probes this gate so accidentally
  setting `ORGON_VERIFY_SAFINA_SIGS=1` without wiring the payload
  doesn't silently turn on broken verification.
- 14 unit tests cover round-trip with known-good signatures
  (generated via SafinaSigner+TEST_KEY), tamper detection, malformed
  inputs, the gate, and the disabled-mode return path.

### Wave 14 — Off-site PG backup

- `scripts/backup_pg.sh` extended with optional S3-compatible upload
  (works with AWS S3, Cloudflare R2, Wasabi, MinIO).
  Off-site activated by `ORGON_BACKUP_S3_BUCKET`; size-verified via
  `aws s3api head-object`. Local-only behaviour preserved when env
  is unset.
- DEPLOYMENT.md "Backups" section rewritten with R2 setup snippet,
  systemd timer template, and explicit retention guidance ("manage
  off-site retention via lifecycle rules in the bucket — don't let
  one host compromise wipe history").

### Wave 15 — Rewrite 33 skipped tests

- 10 test classes that had been carrying
  `@pytest.mark.skip(reason="legacy MagicMock-style mocks")` since
  Sprint 5: now green and unmocked. Mechanical changes:
  * `db.fetchone` → `db.fetchrow` (asyncpg style)
  * `db.fetchall` → `db.fetch`
  * `MagicMock` for `db.fetch` → `AsyncMock`
  * SQLite `?` placeholders → Postgres `$N`
  * Two non-async tests promoted to `@pytest.mark.asyncio` because
    the underlying methods became `async`.
- **Real bug fixed in passing.** `signature_service.check_new_pending_signatures`
  was emitting events with `pending.ecaddress`, `pending.value`,
  `pending.min_sign`, `pending.signed` — none of those exist on the
  `PendingSignature` model. The whole code path was silently caught
  by `except Exception` and returning `[]`. Updated the event
  payload to use only fields the model actually carries
  (`token / to_addr / tx_value / init_ts / unid`) plus the signer
  address from the client. Now the background "new pending sig"
  Telegram path actually fires.
- CI suite: **152 passed, 0 skipped, 0 failed** (was 86 passed, 33
  skipped). Real coverage of NetworkService cache logic, signature
  flow, transaction filtering — none of that was being exercised
  before.

---

## Known follow-ups (not in any sprint above)

These remain genuine gaps. Order is "product impact, descending".

- **HSM / KMS wire-up for signer key.** Wave 12 abstraction is in;
  `EnvSignerBackend` runs in process today. To switch to AWS KMS or
  Vault: implement the two stub classes per their wiring checklists in
  `backend/safina/signer_backends.py` (~200 lines each, mostly
  boto3/hvac plumbing + v-recovery). No app-side changes required.
- **Confirm Safina canonical sign-payload format.** Wave 13 verifier
  primitive is in but `canonical_payload()` raises until the exact
  byte format is confirmed against Safina docs. One-line unblocking
  + flip `ORGON_VERIFY_SAFINA_SIGS=1` to activate.
- **Real Stripe price IDs.** Service is wired but
  `STRIPE_PRICE_STARTER` / `_BASIC` / `_PRO` env vars are empty until
  someone provisions products in Stripe and sets them.
- **Real SMTP creds.** Email service runs in file-log mode in dev; on
  prod set `SMTP_HOST` etc. or wire SES.
- **AML rule engine.** `aml_alerts` table is a CRUD shell, no
  detector. Compliance checklist won't close without it. Plan: either
  Sumsub / Chainalysis integration or in-house rules (sanction lists,
  threshold breaches, repeat-address signal).
- **Document upload to S3 / R2.** `/compliance/{kyc,kyb}` show a
  banner sending users to email; backend is `placeholder://`.
- **Preview DB separation.** Preview still shares the prod Coolify
  postgres container — recipe in `CI-CD.md`. (Mooted by the planned
  greenfield Coolify deploy on a new server — fresh DB per env.)
- **Address-book B2B model.** `routes_partner_addresses.py` is
  disabled in `main.py`; lands when `address_book_b2b` table + service
  methods are written.
- **Partner analytics filtering.** `AnalyticsService` needs a
  `partner_id` axis for the partner endpoints.
- **i18n KY parity.** Landing and compliance keys still missing.

### Resolved by waves above

- ~~**Backup off-site mirror.**~~ Wave 14 — `scripts/backup_pg.sh`
  now does S3-compatible upload. Activate by setting
  `ORGON_BACKUP_S3_BUCKET` + AWS creds.
- ~~**Local canonical-payload signature verification primitives.**~~
  Wave 13 — recovery + verify functions ready; only the canonical
  payload byte format is left to confirm.
- ~~**Signer key abstraction.**~~ Wave 12 — `SignerBackend` interface
  with KMS/Vault stubs.
