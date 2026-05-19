# ORGON ↔ asystem-core integration — open questions

> Discovery document. ORGON is being positioned as the **custody
> module** for the asystem-core ecosystem (mesh hermes nodes,
> LightRAG, asystem.kg/asystem.ai). Before we plan Phase 2 of the
> dfns-grade hardening, we need a contract with asystem-core
> defining who owns what.
>
> If asystem-core already has half the things we'd otherwise build
> (auth, policy, event bus), our Phase 2 risks duplicating their
> control plane. If they don't, we ship — but at least we shipped
> with intent, not by default.

Authors: ORGON team. Review: Urmat (mesh), caesarclown (operator).
Status: **draft / awaiting answers**.

---

## 1. Authentication boundary — whose identity, whose token?

### Q1.1 — How does asystem-core identify itself to ORGON?

Today's `/v1/*` surface accepts one credential shape: HMAC-signed
requests with `X-ORGON-Key` + secret. Every B2B integrator looks
the same.

asystem-core nodes already speak Ed25519-signed control plane
(see `https://mesh.asystem.kg/api/lightrag/query` — every request
is signed with a node's Ed25519 key, verified by the mesh router).

**Options:**

| Option | Implication |
|---|---|
| A. asystem-core treats ORGON as just another HMAC B2B integrator | Simplest. We issue them `okl_…` / `oksl_…` like any merchant. They drop their Ed25519 layer when talking to us. |
| B. ORGON accepts asystem-core's Ed25519 signatures natively | We add Ed25519 verification path in `MerchantHMACAuthMiddleware` (or a parallel middleware). One mesh-issued key replaces our key issuance for asystem-core. |
| C. Both, gated by configuration per merchant | `organizations.auth_kind = 'hmac' | 'mesh_ed25519'`. Compatible with future identity sources (OIDC, SPIFFE…). |

**Open question for asystem-core team:**

> Should ORGON treat the mesh as one tenant with one HMAC key, or
> should every mesh node have its own identity at the ORGON
> boundary? Are you willing to drop Ed25519 at our edge, or do you
> want it carried end-to-end?

### Q1.2 — End-user identity

Who is the **end-user** when an asystem.kg consumer initiates a
crypto operation?

* If asystem-core has its own user DB → ORGON's `end_users` is
  just a mirror keyed by `external_id`. No KYC duplication.
* If asystem-core delegates user-management to ORGON → we have
  to surface our `POST /v1/users` to their UI directly.
* If asystem-core wants embedded wallet UX (passkey signing at
  the user's browser) → that's E-13 territory and depends on Q1.1.

**Open question:**

> Where does the end-user live? Whose DB is authoritative for
> KYC status, email, metadata? Whose UI mints the user → wallet
> association?

### Q1.3 — Operator identity inside ORGON

Distinct from Q1.1/1.2: ORGON has its own operator dashboard
(`/api/*` surface, JWT-auth, RBAC roles `super_admin /
platform_admin / company_admin / company_operator / company_auditor`).
This is a **separate** identity layer from anything asystem-core
sends us.

If we ship E-05 (multi-credential model — passkey for operators,
plus recovery codes), that's a parallel WebAuthn implementation
to whatever mesh is doing for its nodes.

**Open question:**

> Should ORGON operators federate against asystem-core SSO
> (if one exists), or keep a separate identity (JWT + passkey)?
> The latter is the current default — it's the safer assumption
> while we wait for an answer.

---

## 2. Policy engine ownership

### Q2.1 — Is there an asystem-core policy layer above ORGON?

E-07 just extended `transaction_monitoring_rules` to support
scope, new rule kinds, `request_approval` action, and
`policy.triggered` webhook. This is **a policy engine inside
ORGON**.

If asystem-core has its own policy layer (e.g. mesh-wide rules
like "no withdrawals from a node flagged by Урmat as compromised"),
the two have to coexist without contradiction.

| Option | Implication |
|---|---|
| A. ORGON's engine is the only one | Mesh writes rules into ORGON via `/api/v1/compliance/rules` (admin-gated, JWT). asystem-core treats ORGON's rule DB as a service. |
| B. asystem-core has its own engine, ORGON enforces nothing | We rip out E-07's `compliance_service.evaluate_transaction_rules` and trust an inbound `X-ORGON-Policy-Decision` header from asystem-core. Risky — defense-in-depth gone. |
| C. Both engines run, ORGON's enforces a subset | ORGON enforces local invariants (thresholds, replay, blacklists) regardless of asystem-core verdict; asystem-core overlays mesh-wide policy. |

**Open question:**

> Does asystem-core run its own policy/rule engine? If so, what's
> the contract — does it pre-approve tx-sends, post-validate, or
> only emit alerts?

### Q2.2 — Approval workflow ownership

E-07 added `request_approval` action as a forward-compat marker.
E-08 (planned) would wire it to an approval-groups workflow
inside ORGON.

If asystem-core has approval workflows (e.g. mesh maintainers
approve high-value moves), E-08 might just be a webhook-out plus
a status-in surface, not a self-contained engine.

**Open question:**

> Should ORGON own M-of-N approval state machines, or should we
> emit a `policy.triggered` event with `action=request_approval`
> and trust asystem-core to call us back with an approve/reject
> decision?

---

## 3. Event bus shape

### Q3.1 — Inbound: what events does asystem-core send ORGON?

Right now ORGON has zero inbound event subscriptions from
asystem-core. Hypothetically useful events:
* User suspended in mesh → freeze that user's wallets in ORGON
* Node flagged as compromised → block tx from wallets created on it
* Mesh-wide AML alert → tighten thresholds organization-wide
* Operator promoted/demoted in mesh → mirror RBAC role in ORGON

**Option:**
* Webhook-out from asystem-core to ORGON: `POST /v1/asystem-events`
  with mesh's Ed25519 signature.
* Or pull-based: ORGON polls mesh's `/api/events?since=…` periodically.

**Open question:**

> Does asystem-core have an event bus we can subscribe to? If
> not, is webhook-out viable on your side? What's the menu of
> events you'd publish to a custody module?

### Q3.2 — Outbound: what events does ORGON send asystem-core?

ORGON's webhook publisher (`webhook_publisher.py`) today emits:
`wallet.activated`, `wallet.deposit.detected`,
`transaction.broadcasted`, `policy.triggered` (Wave 29 live).
Defined-but-not-wired: `transaction.confirmed`, `transaction.failed`,
`user.created`.

Question is whether asystem-core wants to be one consumer of this
stream (just point a URL at us) or whether they want a richer
contract — e.g. SSE feed, or push into their mesh-internal bus.

**Open question:**

> Does asystem-core consume webhooks the standard way (configured
> URL + HMAC verification), or do you want a different transport?

---

## 4. Compliance and regulatory ownership

ORGON ships KYC/KYB (Sumsub-WebSDK), AML alerts, SAR submission,
and per-rule audit. KG/KZ/RU regulatory perimeter applies.

### Q4.1 — Who handles the regulator-facing side?

* SAR submission to **Финнадзор КР**: ORGON's `sar_submissions` table.
* KYC/KYB document custody: currently `placeholder://` in ORGON.
* Travel Rule (FATF): data model only on ORGON side; no provider wired.

If asystem-core is the regulated entity (licensed VASP), ORGON
is its compliance arm. Then everything we ship (Sumsub
integration, SAR pipeline) feeds asystem-core's regulatory reports.

If ORGON is the licensed entity, asystem-core is just a customer
and we surface compliance status to them via API.

**Open question:**

> Which legal entity holds the KG VASP license — ОсОО АСИСТЕМ
> directly, or a sister entity that runs asystem-core? Does ORGON
> sit under that license as a module, or is it a separate licensee?

### Q4.2 — Travel Rule

Planned E-09 (Notabene or Sumsub Travel Rule integration). The
choice matters for cost and for who counts as the originator
VASP on outbound transfers.

**Open question:**

> When asystem-core users send crypto out via ORGON, does the
> Travel Rule originator field carry asystem-core's VASP id, or
> ORGON's, or do we have a shared one?

---

## 5. Deployment topology

### Q5.1 — Where does ORGON live in the mesh?

Today: prod on `orgon.asystem.ai` (Coolify on hetzner-ax41 →
`asystem-proxmox` 10.30.30.132). One Postgres, one
backend, one frontend.

If asystem-core wants ORGON deployable per-tenant or per-mesh-node:
* Containerization is already there (`Dockerfile`, `docker-compose.yml`).
* Migrations are deterministic (single canonical + 25+ overlays).
* What's missing: configuration story for **multi-instance**
  (every instance points at its own Safina account? At its own
  AML rule set? At its own webhook URLs?).

**Open question:**

> Is ORGON a single-instance shared service for the whole mesh,
> or do you want a deployment-per-tenant model? If the latter,
> what configuration parameters change between instances?

### Q5.2 — Data residency

KG/KZ regulators are tightening on data residency. If a mesh tenant
in RU has different storage requirements than a KZ tenant, we
need per-instance Postgres at different DCs.

**Open question:**

> Do we need per-tenant data residency separation? If so, which
> jurisdictions and what's the customer mix?

---

## 6. SLA + observability

### Q6.1 — What SLOs does asystem-core need from ORGON?

* Availability: 99.9% / 99.95% / 99.99%?
* Webhook delivery latency: p50 / p99?
* Deposit detection lag: max acceptable seconds from on-chain
  confirmation to webhook out?

Without a contract here, we can't size infrastructure or write
runbooks.

**Open question:**

> What numbers does ORGON need to hit? Today we have JSON logs
> (`ORGON_JSON_LOGS=1`) + Sentry (`SENTRY_DSN=…`) + Prometheus
> counters. We do not have alert rules. What's the on-call
> chain — ORGON team, mesh on-call, or both?

### Q6.2 — Audit trail consumer

E-04 added `/api/audit/events` + `.csv` export. If asystem-core
wants real-time audit feed (not pull-based), we'd add another
webhook type or a server-sent events endpoint.

**Open question:**

> Does asystem-core need a live audit feed, or is daily/weekly
> CSV pull-based sufficient?

---

## 7. Roadmap interactions

These are tactical questions that depend on the above answers.

| Phase 2/3 epic | Blocks on |
|---|---|
| E-05 multi-credential (passkey/recovery) | Q1.3 (operator identity boundary) |
| E-06 user-action signing | Q1.1, Q1.3 (whose tokens count as user-action) |
| E-08 approval workflow | Q2.2 (where M-of-N state lives) |
| E-09 Travel Rule | Q4.2 (originator VASP id) |
| E-13 embedded wallet SDK | Q1.2, Q1.3 (end-user vs operator identity) |

If asystem-core has its own auth + policy + approval, **E-05 /
E-06 / E-08 may collapse to "webhook bridge"** — much smaller
scope. We need answers before committing engineering hours to
the larger versions.

---

## How to use this document

1. **Send this to Urmat / asystem-core lead.** Add answers inline
   under each section as comments or in a follow-up PR.
2. **For each question, the answer should be one of:**
   * "Yes, asystem-core does this → ORGON adapts to call us."
   * "No, asystem-core does NOT do this → ORGON owns this layer."
   * "Both, here's the split: …"
   * "Not decided yet — let's revisit by 2026-MM-DD."
3. **Once answers land**, rewrite Phase 2 roadmap. Some epics
   collapse, some grow, some get cancelled.
4. **This file stays version-controlled** — when an answer
   changes, we see the diff. Avoid Slack/email for these
   decisions; they decay.
