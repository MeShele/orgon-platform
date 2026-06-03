# ORGON integration changelog

> **What lives here.** Only **breaking** or **additive** changes that
> affect a system integrating ORGON as a sub-module (asystem-core
> today; future API consumers). Anything you can ignore as an
> integrator — UI tweaks, refactors, internal performance work — goes
> in the main [`../CHANGELOG.md`](../CHANGELOG.md), not here.
>
> **How to read.** Newest first. Each entry says **what changed**,
> **does it break existing consumers**, and **what action you need to
> take** (often "none — additive").
>
> **How to subscribe.** GitHub watch on this file path is the simplest
> notification channel today. A push variant (`system.contract_changed`
> webhook) is on the roadmap — see `docs/CUSTDEV_DEVELOPER.md` DEV-7.

---

## 2026-06-03 — `GET /v1/networks` discovery + live `transaction.failed`

**Additive.** No existing flow breaks.

- **New endpoint**: `GET /v1/networks` (public, no HMAC) — authoritative
  `chain_id ↔ slug` map with `native_symbol`/`native_decimals`,
  `testnet`/`sandbox_allowed` flags, explorers, and a best-effort token
  list. Use it to build your network map instead of hardcoding
  `NETWORK_SLUG_TO_CHAIN_ID` — the ORGON-chain ids (`5800`/`5810`) are
  not guessable. Shape documented in [`API.md`](../API.md) → Supported
  networks. **Action**: optional — replace any hardcoded slug→chain_id
  table with a fetch from this endpoint.
- **`transaction.failed` is now live + immediate, not only timeout-based.**
  When Safina rejects a broadcast it returns an error string (e.g.
  `EVM error: OutOfFunds`); ORGON now flips the tx to `failed`
  immediately and fires `transaction.failed` with that verbatim string
  in `reason` (previously the only `reason` was `timeout_no_broadcast`
  after 24h). The `/v1/transactions` responses also carry a new
  `failure_reason` field (null unless failed). See
  [`WEBHOOKS.md`](WEBHOOKS.md) → `transaction.failed`. **Action**: none
  required; if you surface payout failures, you can now show `reason`.
- **`transaction.confirmed` is now a REAL on-chain confirmation**, no
  longer a same-tick duplicate of `transaction.broadcasted`. After
  `broadcasted` (tx_hash known), a sweep polls the chain explorer and
  fires `confirmed` — with a new **`block_number`** field — once the tx
  is actually mined. ORGON-chain (`5800`/`5810`) has no explorer, so
  there `confirmed` still fires immediately with `block_number: null`.
  **Action**: this is the correct signal to mark a payout final (e.g.
  order `completed`); previously `confirmed` arrived prematurely at
  broadcast time. If you were treating `broadcasted` as final, you can
  now wait for `confirmed`. See [`WEBHOOKS.md`](WEBHOOKS.md).
- **New event `transaction.canceled`** — fires when Safina abandons a
  signed tx (24h limit / slist mismatch), with the verbatim cancellation
  string in `reason`. Terminal (won't later broadcast, unlike `failed`).
  **Action**: handle it in your webhook router to mark the transfer
  `canceled` and surface retry UX (previously you'd poll forever).
- **`PHASE4_SPEC` completed** — added drop-in snippets for the remaining
  parity edge functions (`orgon-wallet-balance`, `orgon-provision-pool-
  wallet`) and the `CustodyPayoutDialog` provider-dispatch diff (§11), so
  the `orgon-*` set maps 1:1 to `dfns-*`.

---

## 2026-05-21 — Phase 4 spec + dual-custody surface

**Additive.** No existing flow breaks; new artifacts unblock work that
was previously vague.

- **New endpoint**: `GET /v1/wallets/{id}/assets` returns DFNS-shape
  `{assets: [{kind, symbol, decimals, balance, contract, verified}]}`.
  Sibling to existing `/balance` (legacy shape `{balances: [{token,
  value, decimals}]}`). Lets `PoolBalanceTile` (or any other UI built
  for the DFNS contract) read ORGON pool wallets through a thin
  passthrough edge function instead of needing a shape adapter.
- **Wallet response now includes `info` field** (mirror of `name`).
  asystem-core's `orgon_wallets.info` column will start populating
  with real values on the next deploy. Old `name` field still
  present — no rename, no break.
- **New spec doc**: [`ASYSTEM_CORE_PHASE4_SPEC.md`](ASYSTEM_CORE_PHASE4_SPEC.md)
  — outgoing-payouts contract with a drop-in `orgon-create-transfer`
  Deno edge function and a suggested `orgon_transfers` table layout.
  Mirrors the existing `dfns-create-transfer` structure so reviewers
  can diff one-to-one.
- **New self-service doc**: [`PLATFORM_API_GUIDE.md`](PLATFORM_API_GUIDE.md)
  — full `POST /platform/merchants` contract with curl + Deno samples,
  idempotency notes, audit-trail behaviour, error catalog.
- **`ASYSTEM_CORE_INTEGRATION.md` updated** for dual-custody (DFNS +
  ORGON share `exclusive_group='custody'`). O-2 (Phase 4) rewritten —
  no longer "waiting on us for a spec", now "waiting on asystem-core
  to wire `useCustodyCanPayout` through to ORGON".

**Action for integrators**: none required. If you want to consume the
new shape, start reading the new docs. Existing `/balance`,
existing wallet response keys, existing webhook envelope all
unchanged.

---

## Earlier (pre-2026-05-21)

Wave 30-38 (2026-05-19 → 2026-05-20) shipped a lot for integrators —
self-service merchants via `/platform/merchants`, `transaction.uncertain`
preview signal, `wallet.requested` event, treasury pull endpoints,
deposit lookup by tx_hash, compliance rules CRUD on `/v1/*`, etc.
Those landed in the main `CHANGELOG.md`. We did not have this
integration-only feed at the time. From this entry forward, treat
the main changelog as historical and this file as the canonical
integrator signal.

---

## Entry template (for maintainers)

```
## YYYY-MM-DD — short title

**Additive | Breaking**. One-line summary of who's affected.

- Bullet per change: what shipped, why it matters to integrators,
  which file or endpoint changed.
- Be specific about field names, status codes, header names — these
  are the things downstream code references.

**Action for integrators**:
- "None" if additive.
- Otherwise: concrete step-by-step migration.

**Deprecation**: if anything is being phased out, give a date by which
old behaviour stops working. Never break silently.
```
