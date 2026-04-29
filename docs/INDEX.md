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

_Index last updated: 2026-04-29 (end of Wave 16 doc alignment)._
