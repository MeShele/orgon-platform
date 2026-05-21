# ORGON documentation index

The truthful, current docs live at the **repo root**, not in this folder.
This `docs/` directory contains business analysis, Safina protocol HTML
references, and historical phase notes that are kept for archeology.

---

## Where to actually go

For day-to-day work, ignore this folder and open one of these at the repo root:

| File | What |
|---|---|
| [`../README.md`](../README.md) | Project overview, status table, quick start |
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | Stack, middleware, multi-sig, signer, RLS |
| [`../API.md`](../API.md) | Auth, multi-tenancy, partner API, webhook contracts |
| [`../DEPLOYMENT.md`](../DEPLOYMENT.md) | Coolify procedures, env vars, fresh-DB apply, backups |
| [`../CI-CD.md`](../CI-CD.md) | GitHub Actions, deploy hooks, backup runbook |
| [`../CHANGELOG.md`](../CHANGELOG.md) | Sprint/wave-by-wave changelog (Waves 1–15) |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Branch strategy, PR process, tests |
| [`../AGENTS.md`](../AGENTS.md) | Cheat sheet for AI assistants working on the repo |
| [`../backend/migrations/README.md`](../backend/migrations/README.md) | Canonical schema flow, how to add a 025+ overlay |

---

## What lives here (and is still useful)

### Business analysis (`orgon_analysis/`)

Long-form notes on the product side — roles, flows, regulatory posture,
margin model, UX guidelines. Useful when scoping a new vertical or
preparing investor materials.

- [`orgon_analysis/01_business_roles_and_flows.md`](orgon_analysis/01_business_roles_and_flows.md)
- [`orgon_analysis/02_platform_architecture.md`](orgon_analysis/02_platform_architecture.md) — *some details predate Wave 11; cross-check against `../ARCHITECTURE.md`*
- [`orgon_analysis/03_api_gap_analysis.md`](orgon_analysis/03_api_gap_analysis.md) — *Phase 2 era, much shipped since*
- [`orgon_analysis/04_margin_calculator.md`](orgon_analysis/04_margin_calculator.md)
- [`orgon_analysis/05_implementation_phases.md`](orgon_analysis/05_implementation_phases.md) — *historical roadmap*
- [`orgon_analysis/06_regulatory_compliance.md`](orgon_analysis/06_regulatory_compliance.md)
- [`orgon_analysis/07_ux_guidelines.md`](orgon_analysis/07_ux_guidelines.md)

### Safina protocol references (HTML)

Pulled from Safina's wiki / examples site. These are the spec source.

- `Examples.html` — Node.js reference implementation of EC signing
- `H2K_Pay.html` — payment widget integration
- `Wiki (1).html`, `safina 2.html`, `safina exp.html` — endpoint tables

### Compliance / partner-onboarding

- [`PARTNER_ONBOARDING.md`](PARTNER_ONBOARDING.md) — partner go-live checklist (verify currency before sharing externally)

### asystem-core integration (Custody Core)

**Reading order for a new integrator:**

1. [`ASYSTEM_INTEGRATION_PLAYBOOK.md`](ASYSTEM_INTEGRATION_PLAYBOOK.md) — step-by-step Phase 1-5 guide; §0 points to the smoke harness — start there
2. [`ASYSTEM_CORE_INTEGRATION.md`](ASYSTEM_CORE_INTEGRATION.md) — integration contract, current state, dual-custody architecture, open items
3. [`PLATFORM_API_GUIDE.md`](PLATFORM_API_GUIDE.md) — self-service merchant provisioning via `/platform/merchants`
4. [`ASYSTEM_CORE_PHASE4_SPEC.md`](ASYSTEM_CORE_PHASE4_SPEC.md) — outgoing-payouts contract + drop-in `orgon-create-transfer` Deno snippet
5. [`ORGON_FOR_EXCHANGES.md`](ORGON_FOR_EXCHANGES.md) — operator-facing guide your end-customers will read
6. [`INTEGRATION_CHANGELOG.md`](INTEGRATION_CHANGELOG.md) — integrator-only changelog (skip the main `CHANGELOG.md` noise)

**Design memos:**

- [`PHASE5_TREASURY_FEASIBILITY.md`](PHASE5_TREASURY_FEASIBILITY.md) — pull-vs-push design memo for treasury balance (O-3 input)
- [`CUSTDEV_OPERATOR_END_USER.md`](CUSTDEV_OPERATOR_END_USER.md) — role-walkthrough findings for exchange operators + end users
- [`CUSTDEV_DEVELOPER.md`](CUSTDEV_DEVELOPER.md) — role-walkthrough findings for asystem-core developers integrating us

**Webhook + endpoint reference (root-level):**

- [`../WEBHOOKS.md`](../WEBHOOKS.md) — full webhook event catalog with payload shapes
- [`../API.md`](../API.md) — both `/api/*` and `/v1/*` surfaces; HMAC spec; error catalog
- [`../sdks/typescript/`](../sdks/typescript/) — TS SDK + Deno-native smoke harness at `examples/asystem-smoke/`

---

## What lives here and is OUTDATED

The `PHASE*_*.md`, `IMPLEMENTATION_SUMMARY.md`, `QUICKSTART_CHECKLIST.md`,
`ROADMAP*.md`, `CRITICAL_REFERENCE.md`, `GOTCHA_API_IMPLEMENTATION_PLAN.md`,
`MIGRATION_GUIDE.md`, `DATABASE_SCHEMA_MULTITENANT.md`, and all of the
`*_REPORT.md` / `*_AUDIT*.md` files describe states of the project from
Phase 1–4 (Q1 2026) and earlier. They are preserved for git history and
context but **must not be used as current truth** — refer to the
root-level docs above instead.

If a phase doc claims something contradicts the live root doc, the root
doc wins. If you find yourself relying on a phase doc, that's a signal
the root docs need to be extended — please update them rather than
patching the phase doc.

---

_Index last updated: 2026-05-21 (dual-custody + custdev role walkthroughs)._
