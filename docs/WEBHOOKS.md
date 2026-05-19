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
> **defined** — symbol exists in `webhook_publisher.py` but no
> publisher wires it yet; we will not silently start firing — there
> will be a CHANGELOG entry when it goes live.

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
  "deposit_id":   "…",
  "wallet_id":    "…",
  "end_user_id":  "…",       // null for treasury wallets
  "network":      5010,
  "asset":        "USDT",     // "" for native
  "amount":       "100.000000",
  "tx_hash":      "0x…",
  "log_index":    0,
  "from_address": "T…",
  "to_address":   "T…",
  "block_number": 12345678,
  "confirmations": 0          // bumped by subsequent re-detection
}
```

### `transaction.broadcasted` — live

Fires once per outbound transaction the moment Safina returns a
`tx_hash` (signing is complete, the network has accepted the broadcast
but the tx may still be unconfirmed).

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

### `transaction.confirmed` — defined

Will fire on first network confirmation (block inclusion). Currently
not wired — `EV_TX_CONFIRMED` exists in code but no publisher.

### `transaction.failed` — defined

Will fire on terminal failure (rejection by Safina, dropped from
mempool, signer-mismatch detection). Currently not wired.

### `user.created` — defined

Will fire when `POST /v1/users` (or its idempotent re-call) inserts a
new `end_users` row. Currently not wired.

---

If you need an event we don't ship — file a ticket
([support@orgon.asystem.kg](mailto:support@orgon.asystem.kg)) with the
trigger condition and the data shape you'd consume. We'd rather
publish a real event than have you poll us.
