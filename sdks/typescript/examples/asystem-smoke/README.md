# asystem-core ↔ ORGON smoke harness

Standalone Deno script that exercises the integration contract
asystem-core's edge functions actually rely on. A green run proves
that, against the target environment:

* HMAC signing in `${ts}\n${nonce}\n${METHOD}\n${path}\n${rawBody}`
  shape matches what ORGON's middleware expects (Phase 1).
* `POST /v1/users` is idempotent on `(merchant_id, external_id)` and
  returns the same `id` on re-call (Phase 2).
* `POST /v1/wallets` accepts `network` as a string-numeric chain_id
  and returns the documented shape (Phase 2).
* `GET /v1/wallets/{id}` round-trips the wallet for the polling
  pattern asystem-core uses while waiting for activation.
* `PUT/GET /v1/webhooks/config` and `POST /v1/webhooks/test` close
  the loop on Phase 3 deliverability.
* The synthetic test delivery shows up in
  `GET /v1/webhooks/deliveries`.

If any step fails, the script exits immediately with the first
failure context — no cascade.

## Run

```bash
ORGON_KEY=okt_… \
ORGON_SECRET=okst_… \
ORGON_BASE_URL=https://orgon.asystem.ai \
  deno run --allow-net --allow-env smoke.ts
```

Defaults `ORGON_BASE_URL` to `https://orgon.asystem.ai` if omitted.
Use a sandbox key (`okt_…` / `okst_…`) — the script provisions a
real `end_user` row and a real wallet on each run; against a live
key this would burn quota and leave permanent rows.

## Sample output (success)

```
ORGON smoke against https://orgon.asystem.ai
Key: okt_3f9a…

Phase 1 — HMAC + ping
  ✓ 1. GET /v1/ping authenticates — merchant=11111111-…

Phase 2 — user + wallet provisioning
  ✓ 2. POST /v1/users creates user — id=aaaaaaaa-…
  ✓ 3. POST /v1/users idempotent on external_id — same id on re-call
  ✓ 4. POST /v1/wallets provisions — id=… status=pending addr=<pending>
  ✓ 5. GET /v1/wallets/{id} returns the same row

Phase 3 — webhook config + synthetic delivery
  ✓ 6. PUT /v1/webhooks/config persists url+secret
  ✓ 7. GET /v1/webhooks/config reads back what we wrote
  ✓ 8. POST /v1/webhooks/test queued — delivery=cccccccc-…
  ✓ 9. GET /v1/webhooks/deliveries surfaces the test delivery

All 9 checks passed against https://orgon.asystem.ai.
HMAC, idempotency, provisioning, and webhook surfaces match the asystem-core contract.
```

## What this does NOT cover

* `POST /v1/transactions` + `/sign` (Phase 4 outgoing payouts).
  Adding a step here requires a treasury wallet with funded balance —
  too stateful for a smoke harness. Test manually with `payout-sender`
  in the sibling example folder instead.
* `wallet.deposit.detected`, `wallet.activated` webhook **delivery**.
  We register a `https://example.invalid` URL so we don't accidentally
  cross-fire real consumers; the actual webhook receive path lives
  in asystem-core's `orgon-webhook` edge function and gets exercised
  by integration tests on their side.
* `transaction.failed` from the timeout sweep (Sprint 2 of Wave 31).
  That fires on a 24h+ stale-signed condition, too long for a smoke
  pass; covered by `backend/tests/test_transaction_failed_sweep.py`.

## When to run

* After ORGON deploy to a sandbox env — catches regressions before
  they hit Эрмек's Supabase edge.
* After asystem-core changes their `orgon-client.ts` HMAC code —
  a divergence between this script's signing and theirs surfaces in
  Phase 1 immediately.
* Before sharing fresh sandbox credentials with a new integrator —
  proves the keys work end-to-end without them having to wire
  everything just to discover a quota or signature issue.

## Why standalone (no `@orgon/sdk`)

asystem-core runs in Deno (Supabase Functions). The SDK uses
`node:crypto`; Deno can polyfill that but the contract verification
goal is to test **the wire**, not the SDK. Inlining the HMAC code
here keeps a divergence from showing up only in production.
