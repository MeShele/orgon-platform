# ORGON ↔ asystem-core integration — current contract

> ORGON is the **Custody Core** module of the asystem-core platform.
> This document records the contract as it actually runs today,
> verified against both sides of the wire on 2026-05-19. For the
> public webhook + endpoint catalog see `WEBHOOKS.md` and `API.md`;
> for the step-by-step integrator's guide see
> `ASYSTEM_INTEGRATION_PLAYBOOK.md`.

Owner (ORGON-side): caesarclown (`Suimonkul` in asystem-core handover).
asystem-core counterpart: Эрмек.

History note — earlier revisions of this file framed every section as
an open question awaiting an answer. Those answers have since landed
de-facto in the production code on the asystem-core side (Phase 1–3
already shipped: `orgon-ping`, `orgon-provision-wallet`, `orgon-webhook`,
`orgon-webhook-register`). The text below records what is true today;
the remaining genuinely-open items live at the bottom.

---

## 1. Authentication boundary

### asystem-core → ORGON `/v1/*` — HMAC

asystem-core calls ORGON's `/v1/*` surface with our standard HMAC
contract — no Ed25519, no mesh signing, no Bearer. Per-operator
credentials (`ORGON_KEY` / `ORGON_SECRET` / `ORGON_BASE_URL` /
`ORGON_ENV`) live in their `operator_api_keys` vault, decrypted on
each call.

* canonical: `${ts_ms}\n${nonce}\n${METHOD}\n${path}\n${rawBody}`
* signature: `hex(HMAC-SHA256(secret, canonical))`
* headers: `X-ORGON-Key`, `X-ORGON-Timestamp` (ms), `X-ORGON-Nonce`
  (UUIDv4), `X-ORGON-Signature`; ±60s drift; nonce uniqueness enforced
  via `merchant_request_nonces` PK.

Verified line-for-line against
`asystem-core/supabase/functions/_shared/orgon-client.ts:65` and
`backend/api/middleware_merchant_hmac.py:234`. They match.

### End-user identity

asystem-core's `auth.users.id` (uuid) flows through to ORGON as
`external_id` on `POST /v1/users`. Email is the user's auth email, or
`${uuid}@asystem.local` when headless. ORGON's `end_users` table is
the merchant-scoped mirror, keyed by `(merchant_id, external_id)`.
KYC documents are NOT mirrored to ORGON — they stay on the operator's
asystem-core instance, governed by their `kyc-*` provider stack.

### Operator identity

Two layers run side-by-side without federation:

* ORGON operators authenticate against ORGON's own `/api/*` surface
  (JWT, RBAC, operator dashboard at `orgon.asystem.ai`).
* asystem-core operators authenticate against their Supabase auth on
  `*.asystem.ai`.

A given individual may be an operator on both sides; their identities
do not federate, and there is no SSO bridge. This is by design — it
keeps the M-of-N signing audit trail honest on the ORGON side.

---

## 2. Policy engine ownership

ORGON's in-house rule engine (`compliance_service.evaluate_transaction_rules`,
Wave 23+29) is the only policy layer on the wire. asystem-core does
**not** pre-authorize ORGON transactions through a separate policy
plane; their AML pipeline (`runAmlChainOnPaid` in their
`_shared/aml-on-paid.ts`) runs **after** ORGON tells them a deposit
landed, against their own data, on their own infra.

Practical consequences:

* ORGON enforces threshold/velocity/blacklist/recipient_whitelist/etc.
  on outbound `/v1/transactions` calls regardless of what asystem-core
  thinks. Defense-in-depth.
* `policy.triggered` webhook fires when ORGON's rule action is
  `hold` | `block` | `request_approval` (not `alert`). asystem-core
  consumes that the same way any merchant would — they pause / surface
  the operator manually.
* Approval workflow (M-of-N for non-trivial moves) lives on ORGON's
  side. asystem-core does not have its own approval engine on the
  custody path. E-08 is parked but unblocked from asystem-core's
  perspective.

---

## 3. Event bus

### Inbound (asystem-core → ORGON) — none

There is no `/v1/asystem-events` endpoint and there is no need for
one on the current contract. AML, user-suspension and mesh-policy
state live entirely on asystem-core's side; ORGON does not subscribe
to anything from them. The mesh-wide policy fan-out hypothesized in
earlier revisions of this document never materialized as an actual
asystem-core capability.

If a real use-case emerges (e.g. "freeze custody on this user when
asystem-core's compliance team flags them"), the right shape is
`PATCH /v1/users/{id}` with a custom `kyc_status` or metadata
transition — already a live `/v1/*` endpoint.

### Outbound (ORGON → asystem-core) — standard webhook

asystem-core registers a webhook URL through `PUT /v1/webhooks/config`
exactly like any other merchant. ORGON signs deliveries with
HMAC-SHA256 over `${ts_ms}\n` + body (compact, sort_keys=true JSON);
delivery worker handles retries (`30s..6h` or `1m..24h` env-flagged).

Receiver: `asystem-core/supabase/functions/orgon-webhook/index.ts`.
Verified contract match line-for-line on 2026-05-19; see
`WEBHOOKS.md` for the canonical contract.

Currently consumed by asystem-core: `wallet.deposit.detected`
(transitions their order to `paid`, triggers their AML chain) and
`wallet.activated` (refreshes deposit address when ORGON activates
asynchronously). Other live events (`transaction.broadcasted`,
`transaction.confirmed`, `user.created`, `policy.triggered`) are
emitted by ORGON; their consumers are Phase 4–5 work on the
asystem-core side.

---

## 4. Compliance and regulatory ownership

**The licensee is the operator.** Neither ORGON nor asystem-core
holds the KG VASP license itself — both are technology vendors to the
licensed entity that owns each `operator` row on asystem-core's side.
This is stated explicitly in `asystem-core/docs/COMPLIANCE.md` for
their own services and matches how ORGON is positioned in their
architecture (custody-as-a-service, not custodian-of-record).

Practical consequences:

* SAR submission to Финнадзор КР: ORGON has the data plane
  (`sar_submissions`, four submission backends: `manual_export | email
  | api_v1 | dryrun`), but the submitter-of-record is the operator's
  compliance officer using the operator's GSFR credentials. ORGON
  produces the file; the operator submits it.
* Sumsub-WebSDK is platform-shared today (single Sumsub account
  across all merchants). For asystem-core operators with distinct KG
  VASP licenses, this is wrong long-term — every operator should have
  their own Sumsub workspace. Tech debt; not blocking for the current
  asystem-core integration because they aren't using ORGON's KYC.
* Travel Rule (FATF): unresolved. See §6.

---

## 5. Deployment topology

Single shared ORGON instance for the entire asystem-core platform.
Per-operator separation is enforced by `merchant_id` scoping (one
ORGON merchant = one asystem-core operator, with its own
`okl_…`/`oksl_…` keys living in the operator's
`operator_api_keys` vault).

Production endpoint: `https://orgon.asystem.ai` (Coolify, single
Postgres, single backend, single frontend). asystem-core's
self-hosted operators (`install.sh` path) still call this same shared
ORGON URL — they don't get their own ORGON deploy. They just have
their own keys in their own self-hosted Supabase vault.

Per-tenant ORGON instances (one Postgres per VASP license, KG vs RU
data residency, etc.) are an unsolved problem and not blocking the
current integration. See §6.

---

## 6. Genuinely-open questions

These are the only items in the integration contract that are still
unresolved. Everything else above is fixed.

| # | Question | Owner | Blocks |
|---|---|---|---|
| ~~O-1~~ | ~~**Mainnet chain_id mapping.**~~ — **ANSWERED 2026-05-20**. Authoritative values from prod `networks_cache` (verified via `GET /api/networks`): `bitcoin-mainnet=1000`, `eth-mainnet=3000`, `eth-sepolia=3040`, `tron-mainnet=5000`, `tron-nile=5010`, `orgon-mainnet=5800`, `orgon-testnet=5810`. Pattern: mainnet base × 1000, testnet offset +10/+40. asystem-core's `NETWORK_SLUG_TO_CHAIN_ID` extension lands the mainnet rows when ready. | — | — |
| O-2 | **Phase 4 contract: outgoing payouts.** ORGON has `POST /v1/transactions` + `POST /v1/transactions/{id}/sign` (two-step flow). asystem-core hasn't built the consumer side. Need confirmation that two-step is acceptable, or spec a single-shot variant. | Эрмек | Phase 4 |
| ~~O-3~~ | ~~**Phase 5 contract: treasury balance.**~~ — **CLOSED 2026-05-19**. Pull-model shipped: `GET /v1/wallets/{id}/balance` + `GET /v1/treasury` return cached `token_balances` with honest `as_of` staleness (Wave 32). Excludes `user_deposit` purpose. No migration. Push variant (`treasury.balance.updated` webhook) intentionally deferred — added only if 5-min staleness becomes a real UX problem; design in `PHASE5_TREASURY_FEASIBILITY.md`. | — | — |
| ~~O-4~~ | ~~**`transaction.failed` source-of-truth.**~~ — **CLOSED 2026-05-19**. Wired via timeout sweep (`backend/services/transaction_failure_sweep.py` + hourly scheduler job): tx in `signed` without `tx_hash` for >24h (env-tunable `TX_FAILED_TIMEOUT_HOURS`) → flipped to `failed`, emit `transaction.failed` with `reason: 'timeout_no_broadcast'`. Not terminal — see `WEBHOOKS.md` caveat. Proper Safina-side `rejected` indicator or chain watcher is the right-path future replacement. | — | — |
| O-5 | **Travel Rule.** When asystem-core users send crypto out via ORGON, who carries the originator-VASP id — asystem-core's operator-level VASP, or a shared one? Implementation deferred to Phase 4 anyway, but answer needed before E-09. | Legal first, then both | E-09 |
| O-6 | **Pricing plan for asystem-core operators.** ORGON's `organizations.pricing_plan` drives `/v1/*` quota. What plan do we put new asystem-core operator merchants on — `sandbox`, a custom enterprise tier, something else? | caesarclown | Onboarding flow |
| O-7 | **Per-tenant ORGON instances + data residency.** If a KG VASP operator and a RU VASP operator on asystem-core must keep their custody data in separate jurisdictions, we need per-region ORGON deploys. Not blocking today; flag for the moment somebody asks. | Defer | Future |

When one of these closes, replace it inline with the answer.
This file is the single PR-able source-of-truth for the integration
contract — no Slack, no email, those decay.
