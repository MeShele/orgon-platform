# Phase 5 treasury balance — feasibility memo

> Audience: caesarclown + Эрмек, deciding on the source-of-truth shape
> for asystem-core's Phase 5 admin UI (treasury wallets, per-wallet
> balance, debug deliveries). Resolves the open item O-3 in
> `ASYSTEM_CORE_INTEGRATION.md`.

Status: research only, no code. Wave 30 + 31 just landed; this is the
input for the Phase 5 design decision.

---

## What ORGON has today

Balance data is already cached in ORGON's Postgres. The flow:

```
Safina /user_tokens     ──┐
Safina /wallet_tokens   ──┤
                          │   sync_balances every 300s
                          ▼   (env `sync.balance_interval_seconds`)
                  ┌──────────────────────┐
                  │  token_balances      │   varchar value, hex backup,
                  │  (Postgres)          │   wallet_id = Safina UUID
                  └──────────────────────┘
                          │
                          ▼
                  ┌──────────────────────┐
                  │  balance_snapshots   │   daily history rows
                  └──────────────────────┘
```

Key facts (verified by reading the code):

| Concern | Reality |
|---|---|
| Where balance lives | `public.token_balances` (canonical schema) — `wallet_id varchar, network, token, value varchar, decimals, value_hex, updated_at` |
| What populates it | `BalanceService` + `sync_service.sync_balances()` calling Safina `/user_tokens` + per-wallet `/wallet_tokens` and UPSERTing |
| Refresh cadence | Cron every 300s (5 min) — `tasks/scheduler.py:sync_balances_job` |
| Per-tenant scoping | `multi_tenant_sync.sync_balances_all_tenants` runs the same flow under each tenant's EC. No `organization_id` column on `token_balances` — tenancy is inferred via `JOIN wallets ON tb.wallet_id = w.wallet_id` and `wallets.organization_id` |
| Wallet_id encoding | `token_balances.wallet_id` and `wallets.wallet_id` are both Safina's wallet UUID (varchar), NOT our internal `wallets.id` UUID — the JOIN is on the Safina-side identifier |
| Change detection | None today. `sync_balances` blindly UPSERTs; there is no `prev_value != new_value` branch and no event emit |
| Historical data | `balance_snapshots` table populated by `BalanceService.record_balance_snapshot()` after each sync. Used for 7-day history dashboard |

---

## Option A — Pull-model (`GET /v1/wallets/{id}/balance`)

Add a new `/v1/*` endpoint that returns the cached balance for a wallet.

### Sketch

```http
GET /v1/wallets/{wallet_id}/balance
```

```json
{
  "wallet_id": "<our uuid>",
  "network":   5010,
  "address":   "T...",
  "as_of":     "2026-05-19T10:23:14+00:00",   // token_balances.updated_at
  "balances": [
    { "token": "USDT", "value": "1234.56", "decimals": 6 },
    { "token": "TRX",  "value": "10.0",    "decimals": 6 }
  ]
}
```

And a merchant-wide companion:

```http
GET /v1/treasury
```

Returns balances of every non-`user_deposit` wallet (`purpose IN
('treasury', 'fee', 'hot', 'cold')`) grouped by network + token.

### Effort

- Backend: ~1 day. Two routes, each ~50 LOC. SQL is a single JOIN
  (`token_balances` × `wallets`) filtered by `merchant_id` via
  `request.state.merchant_id` after HMAC.
- Schema: no changes. `token_balances.wallet_id = wallets.wallet_id`
  works as-is.
- Tests: ~30 min. Same fake-pool pattern as Wave 30 tests.
- Docs: 1 paragraph each in `API.md` + a section in
  `ASYSTEM_INTEGRATION_PLAYBOOK.md`.

### Trade-offs

| ✅ Pros | ❌ Cons |
|---|---|
| No schema migration | Up to 5 min stale (sync cadence) |
| No new event symbol | asystem-core has to render-time call us — adds latency to UI |
| Trivially backwards compatible | Caching is on consumer side |
| Same merchant-scoping pattern as existing endpoints | Doesn't notify on big balance moves (lost funds, drain attempt) |
| Easy to deprecate later if push lands | — |

### Risks

* `wallet_id` mismatch — `token_balances` joins on Safina's wallet_id
  varchar, not our UUID. If a wallet exists in `wallets` but Safina
  hasn't synced yet, the response will have empty `balances`. Fine,
  but the API contract should make this honest with `as_of: null`.
* Sync lag during incidents — if Safina is down, `token_balances.updated_at`
  ages. UI should surface staleness.

---

## Option B — Push-model (`treasury.balance.updated` webhook)

Add a new event that fires whenever a token balance for a treasury-
or fee-purpose wallet changes value.

### Sketch

```json
{
  "id":          "...",
  "type":        "treasury.balance.updated",
  "merchant_id": "...",
  "created_at":  "2026-05-19T...",
  "data": {
    "wallet_id":     "<our uuid>",
    "purpose":       "treasury",
    "network":       5010,
    "token":         "USDT",
    "value_before":  "1234.56",
    "value_after":   "1334.56",
    "delta":         "+100.00",
    "as_of":         "2026-05-19T10:23:14+00:00"
  }
}
```

Fires from inside `sync_balances` after each UPSERT, gated on a
`value_before != value_after AND wallet.purpose != 'user_deposit'`
check.

### Effort

- Migration: add `organization_id uuid` column to `token_balances` (so
  we can publish merchant-scoped events without a JOIN inside the
  emit hot-path). Backfill via `UPDATE...FROM wallets WHERE ...`.
  Idempotent overlay. ~30 min.
- Sync code: refactor `sync_balances` to snapshot pre-UPSERT value,
  diff, emit on change. ~2 hours including treasury-purpose filter.
- New event symbol `EV_TREASURY_BALANCE_UPDATED` in
  `webhook_publisher.py`; `WEBHOOKS.md` entry.
- Tests: payload-pinning + change-detection edge cases (no-op on
  identical value, no-emit for user_deposit wallets). ~1 hour.
- Total: ~3-4 hours of actual work, but adds a schema migration.

### Trade-offs

| ✅ Pros | ❌ Cons |
|---|---|
| Near-real-time (≤ sync cadence) | Schema migration adds risk |
| asystem-core stays passive — UI renders from local cache | Need merchant-side cache to keep up |
| Surfaces unusual moves (drains, sweeps) loudly | Noisy if balances move frequently — needs noise control |
| Reuses Wave 30 webhook infra (replay-protection, retries) | Doesn't replace render-time lookups for fresh new wallets |

### Risks

* **Noise.** A busy treasury (hot wallet handling 1000 user_deposit
  consolidations a day) would emit a flood. Mitigation: only emit
  for `purpose IN ('treasury', 'fee', 'cold')` — exclude `hot` if
  it's the consolidation target.
* **Decimal precision.** `value_before/value_after/delta` must use
  string-decimal (same as `wallet.deposit.detected.amount`), not
  float — otherwise we accumulate rounding errors in `delta`
  computation.
* **`value` column is varchar.** Diffing strings is fine for equality
  but `delta` requires `Decimal(value_after) - Decimal(value_before)`,
  watch for malformed Safina-side values.

---

## Recommendation

**Ship Option A (pull) first.** Reasoning:

1. asystem-core's stated Phase 5 ask is "admin UI for treasury wallets,
   balance, debug deliveries" — render-time pull fits an admin UI
   pattern naturally and adds no new event-handling code on Эрмек's
   side.
2. Option A is 1 day of work with no migration; Option B is 3-4 hours
   plus a schema change plus a noise-budget conversation.
3. Pull and push are **not mutually exclusive**. Option B can land
   later as a second event without touching the pull endpoint.
4. The risks for Option A are bounded (5-min staleness, honest
   `as_of` header). The risks for Option B include schema churn and
   noise calibration in production.

If Эрмек pushes back ("our UI wants live updates, polling our edge
function adds latency"), the right move is to layer Option B on top
of A in a follow-up wave — not to skip A.

---

## What I need from Эрмек

* Confirm pull-first model is acceptable.
* Specify which `purpose` values asystem-core actually wants in the
  treasury view (likely `treasury, fee, cold` — confirm).
* Decide if `GET /v1/treasury` (merchant-wide summary) is needed for
  Phase 5, or if per-wallet `GET /v1/wallets/{id}/balance` is enough.
* Confirm we're OK with a 5-min staleness budget.

Once these four answers land, Option A ships in one PR (~1 day).
