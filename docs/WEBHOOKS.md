# Webhooks

The B2B `/v1/*` surface delivers state changes to your endpoint via
signed HTTPS POSTs. This document is the public contract. If anything
here changes, we bump the version and give integrators a deprecation
cycle.

## Configuring an endpoint

`PUT /v1/webhooks/config` with `{ "url": "https://…", "secret": "…" }`
sets the destination and the HMAC secret. The secret is stored and
used to sign every outgoing request — rotating it disables in-flight
deliveries already in the queue (they keep signing with the previous
secret until delivered or given up).

You can fire a synthetic event for end-to-end testing via
`POST /v1/webhooks/test` (the body is your choice).

## Delivery contract

| Aspect | Value |
|---|---|
| Method | `POST` |
| Body | `application/json`, UTF-8, compact (no extra whitespace), keys sorted |
| Transport | HTTPS only (we refuse `http://` URLs at config time) |
| Connection timeout | 8 seconds — your endpoint MUST `200 OK` (or any 2xx) within that |
| Retry window | up to 6 attempts; see Retry schedule |
| Concurrency | at most 50 events drained per delivery tick (≈ 15s) |
| Retention | 90 days from `created_at` for terminal rows (delivered or given up); pending rows are never reaped |

A response in the `2xx` range marks the event delivered. Anything
else — `4xx`, `5xx`, connection error, timeout — is a retry trigger
(see schedule below).

## Headers we set on every delivery

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `User-Agent` | `Orgon-Webhook/1.0` |
| `X-ORGON-Webhook-Timestamp` | Unix milliseconds at sign time |
| `X-ORGON-Webhook-Signature` | `hex(HMAC-SHA256(secret, msg))`; see Signing |
| `X-ORGON-Webhook-Event-Id` | UUID — **stable across retries of the same event** |
| `X-ORGON-Webhook-Id` | legacy alias of `-Event-Id`; same value, kept for back-compat |
| `X-ORGON-Webhook-Event` | event type (e.g. `wallet.activated`) |

### Exactly-once consumption

`X-ORGON-Webhook-Event-Id` is the **same value across every retry of
the same event**. Your handler should dedupe on it:

```python
if not redis.set(f"orgon:event:{event_id}", "1", nx=True, ex=86400):
    return 200  # already processed — ack so we stop retrying
# … your business logic …
return 200
```

The id is identical to `body.id` (the first field in the payload); the
header is provided so a reverse proxy / WAF can dedupe before the
body is even parsed.

## Body shape

```json
{
  "id":          "8c1d4f0e-4af3-49e2-b8a3-1f0c0a9d1234",
  "type":        "wallet.activated",
  "merchant_id": "11111111-2222-3333-4444-555555555555",
  "created_at":  "2026-05-19T10:21:43.012345+00:00",
  "data":        { /* event-specific, see catalog */ }
}
```

Keys are sorted alphabetically — never rely on insertion order when
hashing the body. `created_at` is the moment we enqueued the event,
not the moment we hand it to your endpoint; for retries the value
stays stable.

## Signing

```
msg = f"{X-ORGON-Webhook-Timestamp}\n".encode() + body
sig = hex(HMAC-SHA256(webhook_secret, msg))
```

`body` is the **exact bytes** we POST — no re-serialization on your
side before verification. Use `crypto.timingSafeEqual` /
`hmac.compare_digest` for the compare.

The `@orgon/sdk` package ships `WebhooksAPI.verify(req, secret)` and
the Python SDK ships `verify_webhook(headers, body, secret)` — both
do this for you and pin the bytes shape so a future spec update can't
silently break verification.

The `Timestamp` is a freshness guard: reject anything older than ~5
minutes on your side to keep delayed retries from being replayed as
fresh events (we already throw away rows older than 90 days; this is
defence-in-depth on your side).

## Retry schedule

Six attempts per delivery, then we mark it given-up (`attempts = 6`,
`next_retry_at = NULL`, `last_error` frozen).

Schedule v1 (default; live on production today):

| attempt | wait since previous | wall-clock from first try |
|---|---|---|
| 1 | — | 0 |
| 2 | 30 s | 30 s |
| 3 | 2 m | ≈ 2.5 m |
| 4 | 10 m | ≈ 12.5 m |
| 5 | 1 h | ≈ 1 h 12 m |
| 6 | 6 h | ≈ 7 h 12 m |

Schedule v2 (env-flagged: `WEBHOOK_RETRY_V2=1`; recommended for new
environments):

| attempt | wait since previous | wall-clock from first try |
|---|---|---|
| 1 | — | 0 |
| 2 | 1 m | 1 m |
| 3 | 12 m | 13 m |
| 4 | 2 h | ≈ 2 h 13 m |
| 5 | 8 h | ≈ 10 h 13 m |
| 6 | 24 h | ≈ 34 h 13 m |

Both schedules sit well inside the 90-day retention horizon, so a
given-up row stays inspectable in `webhook_deliveries` for three
months for incident post-mortems.

## Event catalog

> Status legend:
> **live** — fires from production code today.
> **defined (not wired)** — symbol exists in `webhook_publisher.py`
> but no publisher wires it yet; we will not silently start firing —
> there will be a CHANGELOG entry when it goes live.

### `wallet.requested` — live

Fires once, **immediately** after `POST /v1/wallets` enqueues a new
wallet provisioning request — long before Safina returns an address.
Purpose: give merchants a `t=0` signal so their UI can show an honest
"generating address, usually ~90s" timer instead of a silent spinner.
`wallet.activated` follows when Safina actually fills `addr`.

Idempotency: fires only on a **fresh** INSERT into `wallets`. A
re-call to `POST /v1/wallets` that hits the existing-row early return
does NOT re-fire — same semantics as `user.created`.

```json
"data": {
  "wallet_id":                    "…",
  "end_user_id":                  "…",        // null for treasury wallets
  "network":                       5010,
  "purpose":                      "user_deposit",  // or treasury|fee|hot|cold
  "estimated_activation_seconds":  90
}
```

### `wallet.activated` — live

Fires once per wallet when Safina has provisioned a chain address and
the wallet flips from awaiting-activation to usable.

```json
"data": {
  "wallet_id":   "…",
  "end_user_id": "…",        // null for treasury wallets
  "network":     5010,
  "address":     "T…",
  "my_unid":     "…"
}
```

### `wallet.deposit.detected` — live

Fires when the multi-chain deposit watcher sees a new inbound
transfer on a merchant's wallet (native or token).

```json
"data": {
  "deposit_id":     "…",
  "wallet_id":      "…",
  "end_user_id":    "…",        // null for treasury wallets
  "network":        5010,
  "asset":          "USDT",      // "" for native
  "amount":         "100.000000",
  "tx_hash":        "0x…",
  "log_index":      0,
  "from_address":   "T…",
  "to_address":     "T…",
  "block_number":   12345678,
  "block_timestamp": "2026-05-19T10:21:43.012345+00:00",  // ISO8601, may be null on chains
                                                          // that don't surface block ts
  "confirmations":  0             // bumped by subsequent re-detection
}
```

### `transaction.broadcasted` — live

Fires once per outbound transaction the moment Safina returns a
`tx_hash` (signing is complete, the network has accepted the broadcast
but the tx may still be unconfirmed).

`tx_id` in all `transaction.*` payloads is the **public** transaction
id — the same value `POST /v1/transactions` returns as `id` — so you
can match it against your stored reference. `tx_unid` is a duplicate
kept for compatibility. (Before 2026-06-04 `tx_id` mistakenly carried
an internal uuid the public API never exposes.)

```json
"data": {
  "tx_id":       "…",
  "tx_unid":     "…",
  "tx_hash":     "0x…",
  "wallet_name": "…",
  "to_address":  "T…",
  "amount":      "100.0",
  "token":       "USDT"
}
```

### `policy.triggered` — live

Fires when the in-house rule engine matches a rule whose action is
NOT `alert` — i.e. `hold`, `block`, or `request_approval`. Pure
informational `alert` actions do NOT emit a webhook (noise control —
they live in the AML alerts queue).

```json
"data": {
  "rule_id":   "…",
  "rule_name": "high-value send",
  "rule_type": "threshold",      // or velocity, velocity_amount_usd, …
  "severity":  "high",
  "action":    "request_approval",   // hold | block | request_approval
  "alert_id":  "…",              // matching row in aml_alerts (null on insert race)
  "tx": {
    "transaction_id": "…",
    "to_address":     "T…",
    "value":          "50000.000000",
    "token":          "USDT",
    "network":        5010,
    "wallet_id":      "…"
  }
}
```

`action="request_approval"` is a forward-compat marker for the
approval workflow (E-08). Today it behaves identically to `hold` —
the tx goes to `on_hold`, an `aml_alerts` row opens. When the
approval engine ships, rows tagged `request_approval` will be routed
to the approval queue automatically instead of waiting on manual
release.

### `transaction.confirmed` — live (real on-chain confirmation)

Fires when the tx is actually included in a block — **no longer**
co-emitted with `transaction.broadcasted`. After `broadcasted` (Safina
returned a `tx_hash`), a confirmation sweep polls the chain's public
explorer for that hash and fires `confirmed` once it's mined, carrying
the `block_number`. This is the signal to treat a payout as final
(e.g. mark an order `completed`).

Timing: typically seconds-to-minutes after `broadcasted`, depending on
the chain. ORGON-chain (`5800`/`5810`) has no public explorer yet, so
there `confirmed` fires immediately after `broadcasted` with
`block_number: null` (broadcast is the best signal we have); documented
so you don't wait forever on a block number that won't come.

```json
"data": {
  "tx_id":        "…",
  "tx_unid":      "…",
  "tx_hash":      "0x…",
  "wallet_name":  "…",
  "to_address":   "T…",
  "amount":       "100.0",
  "token":        "USDT",
  "block_number": 12345678          // null on ORGON-chain (no explorer)
}
```

### `transaction.uncertain` — live (10-min preview signal)

Fires once per tx, ~10 minutes after Safina accepts the signature
(env-tunable `TX_UNCERTAIN_TIMEOUT_MINUTES`, default 10). Tells the
merchant: "this payout is taking longer than expected, but it might
still land — show your end-user a 'checking, please wait' UI and a
contact-support CTA, don't declare it dead yet."

This event is **non-terminal** by design. Three possible futures
after `uncertain`:

1. Safina catches up — next polling sync emits
   `transaction.broadcasted` + `transaction.confirmed` for the same
   `tx_id`. Treat that as "false alarm resolved" and clear the
   warning in your UI.
2. Stays stuck for 24h — `transaction.failed` fires (separate
   sweep). Treat as "definitively dead", surface in compliance
   queue.
3. Some other resolution (admin manual reject, etc.) — handled by
   the JWT-side workflows; the only signal you'll see on `/v1/*` is
   the eventual `transaction.failed`.

```json
"data": {
  "tx_id":          "…",
  "tx_unid":        "…",
  "tx_hash":        null,                // not broadcast yet
  "wallet_name":    "…",
  "to_address":     "T…",
  "amount":         "100.0",
  "token":          "USDT",
  "stuck_seconds":  720,                 // how long since signature
  "next_check_in":  "transaction.failed will fire at the 24h mark if not broadcast by then"
}
```

Fires **at most once per tx**, gated on a per-row
`uncertain_emitted_at` timestamp set in the same atomic UPDATE that
selects rows for the sweep. A retry-tick caused by webhook queue
hiccup won't re-fire.

### `transaction.failed` — live (two triggers)

Fires on either of:

1. **Immediate rejection.** Since Safina's 2026-06-03 ETH fix, a
   rejected broadcast no longer hangs silently — Safina writes an
   error string into the `tx` field (e.g. `EVM error: OutOfFunds`).
   The polling sync recognises this (a non-empty, non-hash,
   non-cancellation value), flips the tx straight to `status='failed'`
   and fires this event on the same tick. `reason` carries Safina's
   verbatim string.
2. **Timeout.** A tx stuck in `status='signed'` without a `tx_hash`
   for longer than the window (default 24h, tunable via
   `TX_FAILED_TIMEOUT_HOURS`) — the fallback for the case where Safina
   never returns anything at all. `reason` is `timeout_no_broadcast`.

```json
"data": {
  "tx_id":       "…",
  "tx_unid":     "…",
  "tx_hash":     null,                    // always null — broadcast never happened
  "wallet_name": "…",
  "to_address":  "T…",
  "amount":      "100.0",
  "token":       "USDT",
  "reason":      "global: Returned error: EVM error: OutOfFunds"  // Safina string, or "timeout_no_broadcast"
}
```

> **`failed` is NOT terminal.** Today it's a timeout heuristic, not a
> Safina-confirmed rejection. If Safina later returns a real `tx_hash`
> for the same tx (e.g. an unusually slow >24h broadcast), the polling
> sync will flip status back to `confirmed` and re-emit
> `transaction.broadcasted` + `transaction.confirmed` for the same
> `tx_id`. Treat `broadcasted` / `confirmed` as overriding any earlier
> `failed` event for the same `tx_id`.
>
> Other failure modes (Safina-side rejection, signer-mismatch, mempool
> drops) are not detected by this sweep — they'd surface either as
> "stuck forever and eventually time out" or "broadcast confirmed,
> later reorganized" (the latter we don't track at all). Proper Safina-
> side `rejected` signal or chain-watcher integration is the long-term
> right-path.

### `transaction.canceled` — live

Fires when Safina abandons a signed tx — it writes a cancellation
string into the `tx` field (commonly `"Transaction canceled, 1 day
limit."`, also slist-mismatch cases). The polling sync flips the tx to
`canceled` and fires this once, with Safina's verbatim string in
`reason`. Terminal (unlike `failed`, a `canceled` tx will not later
broadcast). Use it to unblock retry UX instead of polling forever.

```json
"data": {
  "tx_id":       "…",
  "tx_unid":     "…",
  "tx_hash":     null,
  "wallet_name": "…",
  "to_address":  "T…",
  "amount":      "100.0",
  "token":       "USDT",
  "reason":      "Transaction canceled, 1 day limit."
}
```

### `user.created` — live

Fires when `POST /v1/users` inserts a new `end_users` row. Idempotent
re-calls (same `external_id`, going through `ON CONFLICT DO UPDATE`)
do NOT re-fire this event — only the original creation does.

```json
"data": {
  "id":          "…",      // our UUID for the user
  "external_id": "…",      // your id, as you passed it
  "email":       "…",
  "kyc_status":  null       // or 'pending' | 'approved' | 'rejected'
}
```

---

If you need an event we don't ship — file a ticket
([support@orgon.asystem.kg](mailto:support@orgon.asystem.kg)) with the
trigger condition and the data shape you'd consume. We'd rather
publish a real event than have you poll us.
