# ASystem Core ↔ ORGON — integration playbook

Audience: asystem-core integrators wiring ORGON as their Custody Core
module. Companion to `WEBHOOKS.md` (public webhook contract),
`API.md` (full endpoint catalog), `ASYSTEM_CORE_INTEGRATION.md`
(integration-contract record).

This document is the shortest path from "I have ORGON credentials in
my operator vault" to "deposits land in our DB and payouts go out."
If something here disagrees with the live `/v1/*` behavior, the live
behavior wins — file an issue at `support@orgon.asystem.kg`.

---

## TL;DR

| Phase | Done? | Note |
|---|---|---|
| 1. HMAC + `/v1/ping` | ✅ asystem-core has it (`orgon-ping`) | tested 2026-05-18 |
| 2. user + wallet provisioning | ✅ asystem-core has it (`orgon-provision-wallet`) | sandbox tested |
| 3. incoming webhook (`wallet.deposit.detected`) | ✅ asystem-core has it (`orgon-webhook`) | live |
| 4. outgoing payouts | ⏳ contract below; build when ready |
| 5. admin UI (treasury / balance / debug) | ⏳ contract below; needs new ORGON endpoint, see §6 |

---

## 1. Credentials and environments

### Self-service provisioning (recommended)

asystem-core's edge layer can create a fresh Orgon merchant + first
API-key pair in one call, without pinging us via Telegram:

```bash
curl -X POST https://orgon.asystem.ai/platform/merchants \
  -H "Authorization: Bearer $ORGON_PLATFORM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name":         "ACME Exchange Ltd",
    "slug":         "acme-exchange",
    "merchant_kind":"exchanger",
    "pricing_plan": "sandbox",
    "sandbox":      true,
    "label":        "asystem-core acme-exchange"
  }'
```

Response carries `api_key.secret_once` — you MUST persist it in your
operator's vault immediately, we never show it again.

`slug` is the idempotency key. Use a value tied stably to your
operator (e.g. the asystem-core `operator_id` or its slug) — a retry
with the same slug returns `409` with the existing `merchant_id` in
the message, so retries are safe.

`ORGON_PLATFORM_MASTER_KEY` is issued out-of-band to one trusted
asystem-core operator on your side. We rotate by flipping the env
var and reissuing — no DB migration, no merchant downtime.

### Manual provisioning (fallback)

If self-service is disabled for any reason, file a ticket at
`support@orgon.asystem.kg` with the desired merchant name + slug;
we'll provision via the admin UI and hand back creds out-of-band.

### Key formats

ORGON issues two key pairs per merchant:

| Env | Key prefix | Secret prefix | Networks allowed |
|---|---|---|---|
| sandbox | `okt_<32hex>` | `okst_<32hex>` | testnets only (5010, 3040, 5810, 1010, 3010) |
| live | `okl_<32hex>` | `oksl_<32hex>` | all (mainnet TBD per O-1) |

Operator vault entries (per-operator on asystem-core side):

```
ORGON_KEY          — public part (okt_… or okl_…)
ORGON_SECRET       — private part (okst_… or oksl_…)
ORGON_BASE_URL     — https://orgon.asystem.ai for prod
ORGON_ENV          — "sandbox" | "live"
ORGON_WEBHOOK_SECRET — 64-hex, set by orgon-webhook-register (Phase 3)
```

Today every asystem-core operator gets a **distinct** ORGON merchant
(one ORGON `okl_…` = one asystem-core operator). Quota and per-tenant
isolation are enforced on ORGON-side; do **not** share keys across
operators.

---

## 2. Phase 1 — sign every request

Canonical message (must be reproduced byte-for-byte):

```
${ts_ms}\n${nonce}\n${METHOD}\n${path}\n${rawBody}
```

* `ts_ms` — `String(Date.now())`
* `nonce` — `crypto.randomUUID()` (UUIDv4, unique per request — server
  remembers nonces ±60s)
* `METHOD` — uppercase (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`)
* `path` — pathname **only**, no query string (`/v1/users`,
  `/v1/wallets/abc123`)
* `rawBody` — exact bytes of the request body; for `GET` use `""`;
  for JSON use `JSON.stringify(body)` with no extra whitespace.

Signature: `hex(HMAC-SHA256(secret, canonical))`.

Headers:

```
X-ORGON-Key: ${ORGON_KEY}
X-ORGON-Timestamp: ${ts_ms}
X-ORGON-Nonce: ${nonce}
X-ORGON-Signature: ${signature}
```

No `Authorization: Bearer …` on `/v1/*`. The four `X-ORGON-*` headers
are the only auth surface.

### Smoke test

```bash
curl https://orgon.asystem.ai/v1/ping \
  -H "X-ORGON-Key: $ORGON_KEY" \
  -H "X-ORGON-Timestamp: $TS_MS" \
  -H "X-ORGON-Nonce: $UUID" \
  -H "X-ORGON-Signature: $SIG"

# 200 → {"ok": true, "merchant_id": "…", "scopes": […], "api_key_id": "…"}
# 401 → recompute signature; check ts skew (±60s); check nonce uniqueness
```

Reference implementation: `_shared/orgon-client.ts` in asystem-core.
This is the canonical signer — re-use, don't re-roll.

---

## 3. Phase 2 — provisioning end-users and wallets

### `POST /v1/users` — idempotent on `external_id`

Request body:

```json
{
  "external_id": "<your-user-uuid>",
  "email":       "user@example.com",
  "kyc_status":  "approved",            // optional: pending|approved|rejected|null
  "metadata":    { "any": "json" }       // optional
}
```

* Idempotent on `(merchant_id, external_id)`. Re-call refreshes
  `email`, `kyc_status`, `metadata` — does NOT 409. Returns `201`
  whether the row was inserted or updated.
* The `user.created` webhook fires **exactly once** — on the very
  first INSERT only. Re-calls do not re-fire (see WEBHOOKS.md).

Response:

```json
{
  "id":          "<orgon-side uuid>",   // store this; pass into /v1/wallets later
  "external_id": "<your-user-uuid>",
  "email":       "...",
  "kyc_status":  "approved",
  "metadata":    { ... },
  "created_at":  "ISO8601",
  "updated_at":  "ISO8601"
}
```

### `POST /v1/wallets` — lazy provisioning, idempotent per (user, network)

Request body:

```json
{
  "network":     "5010",                // STRING-numeric chain_id, not slug
  "end_user_id": "<orgon-side user uuid from /v1/users response>"
}
```

* `network` is the chain_id as a string. Current sandbox mapping:
  `tron-nile=5010, eth-sepolia=3040, orgon-testnet=5810`. Mainnet
  chain_ids are an open question (see `ASYSTEM_CORE_INTEGRATION.md`
  O-1) — do not deploy to live until ORGON confirms.
* Or `treasury: 'treasury' | 'fee' | 'hot' | 'cold'` for merchant-owned
  wallets (mutually exclusive with `end_user_id`).
* Idempotent at `(merchant_id, end_user_id, network, purpose='user_deposit')`
  — a re-call returns the existing wallet.

Response:

```json
{
  "id":          "<orgon-side wallet uuid>",
  "name":        "...",
  "network":     5010,
  "address":     "T...",                 // null when status='pending'
  "status":      "active",               // or "pending"
  "purpose":     "user_deposit",
  "end_user_id": "...",
  "created_at":  "ISO8601"
}
```

### When `status='pending'`

Wallets activate asynchronously (Safina, ~60–90s typical). Three
signals to drive your UI:

1. **`wallet.requested` webhook** — fires the **same instant** you
   call `POST /v1/wallets`. Use it to show a deterministic "generating
   address, usually ~90s" timer in your UI from `t=0` instead of a
   silent spinner. The payload includes `estimated_activation_seconds:
   90` as the hint.
2. **`wallet.activated` webhook** (preferred terminal signal):
   subscribe and update your row when it arrives. Payload includes
   `wallet_id` and `address`.
3. **Poll `GET /v1/wallets/{id}`**: fallback for environments where
   you can't yet consume webhooks (or as a tail-recovery for a missed
   `wallet.activated`). Returns the same shape, with `status` flipped
   to `active` and `address` populated.

Use all three together is fine — the handlers should be idempotent on
`wallet_id`.

---

## 4. Phase 3 — receiving webhooks

ORGON delivers each event with:

* method `POST`, JSON body, sorted keys, compact (no whitespace).
* headers `X-ORGON-Webhook-Signature`, `-Timestamp` (ms),
  `-Id` (UUID, **stable across retries**), `-Event` (event type),
  `User-Agent: Orgon-Webhook/1.0`.
* canonical: `${ts_ms}\n` + body bytes — sign with the secret you
  set via `PUT /v1/webhooks/config`.

```
expected = hex(HMAC-SHA256(webhook_secret, `${ts}\n${rawBody}`))
```

Dedupe on `X-ORGON-Webhook-Id` (== `body.id`). asystem-core's
`orgon_webhook_deliveries` table already does this — re-use.

Retry: up to 6 attempts on any non-2xx, on a `30s / 2m / 10m / 1h /
6h` (v1) or `1m / 12m / 2h / 8h / 24h` (v2 opt-in) backoff. Your
endpoint must `2xx` within 8 seconds or the delivery worker treats it
as failed and queues a retry.

### Events your handler should expect today

| Event | Status | Use |
|---|---|---|
| `wallet.requested` | live | fires **immediately** after `POST /v1/wallets` — drive a "generating address, ~90s" timer in your UI |
| `wallet.deposit.detected` | live | mark order paid; run AML chain (already wired) |
| `wallet.activated` | live | refresh `deposit_address` when ORGON activates async |
| `transaction.broadcasted` | live | Phase 4 — payout left Safina towards chain |
| `transaction.confirmed` | live | co-emits with broadcasted today; treat broadcasted as authoritative (see §7) |
| `transaction.uncertain` | live | tx stuck `signed` >10min → preview warning. NON-terminal — show "проверяем" in UI, **do not** treat as failure |
| `transaction.failed` | live (timeout-based) | tx stuck `signed` >24h → marked failed. NOT terminal — a later `broadcasted` for the same `tx_id` overrides it |
| `policy.triggered` | live | ORGON's rule engine paused / blocked a tx. Surface to compliance UI |
| `user.created` | live | informational — confirms ORGON-side user row exists |

Subscribe to events your business logic actually needs. Unsubscribed
events still deliver if you accept them — your handler should
`200`/noop them rather than 4xx (4xx triggers retries).

---

## 5. Phase 4 — outgoing payouts (when you build it)

Two-step flow. **Not yet implemented on asystem-core side** — this
section is the spec to build against.

### Step 1: `POST /v1/transactions`

```json
{
  "wallet_id":  "<orgon-side wallet uuid — source wallet>",
  "to_address": "T...",
  "amount":     "100.5",        // decimal string
  "asset":      "USDT",          // optional, default TRX
  "info":       "order #1234"    // optional, ≤200 chars
}
```

Returns `201` with the tx in `pending` state (signature still pending):

```json
{
  "tx_id":   "...",
  "tx_unid": "...",
  "status":  "pending",
  ...
}
```

### Step 2: `POST /v1/transactions/{tx_id}/sign`

Signs and submits to chain. Returns `200` with the updated tx record.
Status flips through `signed → broadcasted` as Safina returns a
tx_hash.

### Listening for completion

ORGON emits `transaction.broadcasted` once tx_hash appears. Today
`transaction.confirmed` co-emits at the same moment (see WEBHOOKS.md
caveat) — treat `broadcasted` as the authoritative signal for "money
left ORGON towards the chain."

`transaction.failed` is reserved but **not wired** yet — if you need a
hard-fail signal for Phase 4, raise the issue in
`ASYSTEM_CORE_INTEGRATION.md` O-4 and we'll pick a source-of-truth
together.

---

## 6. Phase 5 — admin UI (treasury / balance / debug)

This section is the **least-defined** part of the integration today
(see O-3). The ask from asystem-core is:

* Treasury wallets — listing, balance, status.
* Per-merchant webhook delivery debug feed.
* Per-merchant usage / quota view.

Available on `/v1/*` today:

* `POST /v1/wallets` with `treasury: 'treasury'|'fee'|'hot'|'cold'`
  for creating merchant-owned wallets.
* **`GET /v1/wallets/{id}/balance`** — single-wallet balance with
  honest `as_of` staleness timestamp (Wave 32).
* **`GET /v1/treasury`** — merchant-wide snapshot of every wallet
  with `purpose IN ('treasury', 'fee', 'hot', 'cold')` (Wave 32).
  Excludes `user_deposit` — those are per-end-user deposit addresses,
  not treasury inventory.
* `GET /v1/usage?days=30` — current quota + N-day history.
* `GET /v1/webhooks/deliveries` — last N delivery rows for debug.
* `GET /v1/invoices` — past invoices.

### Pull semantics

Both balance endpoints read from a locally-cached `token_balances`
table that we refresh every ~5 min via the `sync_balances` worker.
We **never** call Safina from the read path — if Safina is down,
`as_of` ages but the endpoint keeps returning the last-known snapshot.
That's preferable to a 503 for your admin UI.

Sample shape (`GET /v1/treasury`):

```json
{
  "wallets": [
    {
      "wallet_id":   "aaaa…",
      "name":        "treasury-tron-1",
      "network":     5010,
      "address":     "T…",
      "status":      "active",
      "purpose":     "treasury",
      "end_user_id": null,
      "as_of":       "2026-05-19T10:23:14+00:00",
      "balances": [
        { "token": "USDT", "value": "1234.56", "decimals": "6" },
        { "token": "TRX",  "value": "10.0",    "decimals": "6" }
      ]
    }
  ]
}
```

Same shape per-wallet in `GET /v1/wallets/{id}/balance` (without the
outer `wallets` array). Surface `as_of` in your UI — a staleness
chip ("обновлено 2 мин назад") so the operator can tell when sync
last completed.

### Push variant (deferred)

A push webhook (`treasury.balance.updated`) is on the table for
near-real-time updates instead of 5-min polled staleness. Trade-offs
documented in `docs/PHASE5_TREASURY_FEASIBILITY.md` — recommendation
is to keep the pull endpoints as primary and add push only if real
UX feedback says 5-min lag is a problem.

---

## 7. Known caveats and footguns

### `transaction.confirmed` ≡ `transaction.broadcasted` today

Both events fire at the same moment, on Safina returning a `tx_hash`.
ORGON does not currently track block-confirmation depth in the polling
flow. Treat `broadcasted` as authoritative; ignore `confirmed` for now,
or dedupe aggressively if you handle it. A future revision will fire
`confirmed` on real block inclusion and add a `confirmations` field.

### `transaction.uncertain` → `failed` → `broadcasted` ordering

For an outgoing tx, you may see this sequence over ~24h+ if Safina
stalls:

```
0:00  POST /v1/transactions → tx in 'pending'
0:01  POST /v1/transactions/{id}/sign → tx in 'signed'
… stuck (Safina has not broadcast yet)
~10m  transaction.uncertain  ← UI: "проверяем, обычно ~1 мин"
… still stuck
24h   transaction.failed      ← UI: "выплата зависла, контакт поддержки"
… later, if Safina eventually broadcasts
+Xs   transaction.broadcasted ← UI: "false alarm, выплата прошла"
+Xs   transaction.confirmed
```

State machine for your handler:

* `uncertain` → set UI flag "checking". Don't update DB status.
* `failed` → set DB status to failed, surface in compliance queue.
* `broadcasted` for a `tx_id` that previously got `uncertain` or
  `failed` → **clear** the warning / unset the failed flag. The
  broadcast is the authoritative signal.

Dedupe on `(tx_id, event_type)` — repeat `uncertain` deliveries from
webhook retries are gated on our side via `uncertain_emitted_at`, but
defence-in-depth is cheap.

### Sandbox keys must use sandbox networks

ORGON enforces this server-side: a sandbox merchant calling
`POST /v1/wallets` with a mainnet network gets `400 sandbox_restricted`.
Whitelisted testnet chain_ids: `{1010, 3010, 3040, 5010, 5810}`. This
catches "accidentally pointed staging to mainnet" before any money
moves.

### `wallet.deposit.detected` ordering vs `wallet.activated`

A deposit can land **before** `wallet.activated` fires (if ORGON
detected a credit at the same instant Safina activated the wallet).
Don't gate deposit processing on `wallet.activated` ever firing — use
deposits as the authoritative signal and let `wallet.activated` just
refresh the `deposit_address` field if you cache it.

### Idempotency-Key header is optional but recommended

`X-ORGON-Idempotency-Key: <your-uuid>` on any mutating call (POST/PUT/
PATCH/DELETE) gives you 24h response replay keyed by
`(merchant_id, key)`. ORGON adds `X-ORGON-Idempotent-Replay: 1` on a
replayed response so you can distinguish. Use this whenever a network
hiccup might cause your retry.

### Webhook URL rotation

`PUT /v1/webhooks/config` with a new URL or secret takes effect on
**newly-queued** events — in-flight deliveries already in the retry
window continue with the old secret. Don't rotate while you have
pending retries you need to land.

### Wrong-network deposits — there is now a tool

Most common KG-crypto support ticket: user sends USDT-TRC20 to your
Ethereum-watcher address (or vice versa). ORGON never sees the
deposit because the watcher only listens on the wallet's registered
network. Before Wave 35 support had to manually copy the tx_hash
into tronscan/etherscan and decode.

Now use `GET /v1/deposits/lookup?tx_hash=…` — returns either:

* `found: true` with the deposit row(s) (the rare case where the
  deposit IS in our DB but the user just didn't see the webhook,
  e.g. webhook URL was wrong or hit retry window) — show the user
  amount + confirmations, all resolved.
* `found: false` + a structured `hint` string explaining the
  wrong-network failure mode + the explorer to check.

```bash
curl "https://orgon.asystem.ai/v1/deposits/lookup?tx_hash=0xabc…" \
     -H "$(your-hmac-headers)"
```

Cross-network discovery (we look it up FOR you on tronscan/etherscan)
is reserved via `include_offchain=true` but currently returns a
"not yet supported" structured hint — implementation is a separate
epic (chain explorer integration, rate-limit handling).

---

## 8. AML rule management (mirror compliance config)

For asystem-core operators whose compliance officer manages AML
rules inside the asystem-core admin (not jumping to a separate ORGON
dashboard), `/v1/compliance/rules` exposes the same CRUD that the
ORGON dashboard's `/compliance/rules` page uses.

Rules created here get `source: "api"` automatically, so ORGON's
dashboard renders them with an "API" badge — the operator sees the
two channels are mirroring each other.

### Endpoints (all HMAC-signed, same as the rest of /v1/*)

```
GET    /v1/compliance/rules                    list
POST   /v1/compliance/rules                    create
GET    /v1/compliance/rules/{rule_id}          read
PATCH  /v1/compliance/rules/{rule_id}          partial update
DELETE /v1/compliance/rules/{rule_id}          hard delete (204)
```

### Sample create

```bash
curl -X POST https://orgon.asystem.ai/v1/compliance/rules \
  -H "$(your-hmac-headers)" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name":   "high-value-tron-send",
    "rule_type":   "threshold",
    "rule_config": { "threshold_usd": 10000 },
    "action":      "hold",
    "severity":    "high",
    "is_active":   true
  }'
```

Response shape:

```json
{
  "id":              "…",
  "organization_id": "…",
  "rule_name":       "high-value-tron-send",
  "rule_type":       "threshold",
  "description":     null,
  "rule_config":     { "threshold_usd": 10000 },
  "action":          "hold",
  "severity":        "high",
  "is_active":       true,
  "source":          "api",
  "created_at":      "…",
  "updated_at":      "…"
}
```

### Supported `rule_type` + `action` values

Full set (E-07 expanded):

* `rule_type`: `threshold` · `velocity` · `blacklist_address` ·
  `velocity_amount_usd` · `recipient_whitelist` · `time_window` ·
  `recipient_geo_block` (last is a stub until E-09 wires a geo
  provider — config accepted, no firing).
* `action`: `alert` · `hold` · `block` · `request_approval`.
* `severity`: `low` · `medium` · `high` · `critical`.

### What this surface does NOT do

* **Global rules** (`organization_id IS NULL`) are platform-wide
  policy set by ORGON, never visible to `/v1/*`. A direct GET by a
  global rule's id returns `404`.
* **Other merchants' rules** also return `404` — never `403`, to
  avoid leaking existence.
* **`scope.wallet_ids`** restriction (limiting a rule to specific
  wallet UUIDs) is supported by the engine but not yet exposed
  through `/v1/*` Pydantic — coming in a future wave. Today, any
  rule applies to every tx within the merchant.

### `policy.triggered` is the live result

Whenever your rule's `action` is `hold`, `block`, or
`request_approval` and a transaction matches, ORGON emits the
`policy.triggered` webhook (already live, payload documented in
WEBHOOKS.md). Wire that handler to your AML review queue.

## 9. Smoke harness

A standalone Deno script that exercises every contract point this
playbook describes lives at
`sdks/typescript/examples/asystem-smoke/smoke.ts`. Run it against a
sandbox merchant any time you want to confirm that HMAC signing,
idempotency, provisioning, and webhook deliverability all behave —
end-to-end, in under 5 seconds, without bringing up
`orgon-provision-wallet` first:

```bash
ORGON_KEY=okt_… ORGON_SECRET=okst_… \
  deno run --allow-net --allow-env \
  sdks/typescript/examples/asystem-smoke/smoke.ts
```

Green = your edge functions can call ORGON safely. Red exits on the
first failure with full context. See its README for what's covered
and what isn't.

## 10. Support

* Production: `https://orgon.asystem.ai`
* Status page: `GET /v1/health/extended` — JSON with `webhook_queue` /
  `deposit_watcher` health
* Support email: `support@orgon.asystem.kg`
* GitHub issues: `MeShele/orgon-platform` (private)
* Direct: caesarclown (`Suimonkul` on the asystem-core handover doc)
