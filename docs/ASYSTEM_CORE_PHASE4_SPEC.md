# ORGON ↔ asystem-core — Phase 4 spec (outgoing payouts)

> Companion to `ASYSTEM_CORE_INTEGRATION.md`. This is the contract
> asystem-core needs to consume to wire ORGON into the same
> `useCustodyCanPayout` / `CustodyPayoutDialog` flow that already
> works for DFNS. Reading order: `ASYSTEM_CORE_INTEGRATION.md` (the
> overall shape), then this file, then the existing
> `asystem-core/supabase/functions/dfns-create-transfer/index.ts` as
> the reference implementation to mirror.

Verified against Orgon code on 2026-05-21:
- `backend/api/routes_public_v1.py:608-660` — endpoints
- `backend/services/merchant_tx_service.py` — service layer
- `backend/services/transaction_service.py:625-680` — broadcast/confirm publishers
- `backend/services/transaction_failure_sweep.py:111-140` — failed publisher
- `backend/services/webhook_publisher.py:28-31` — event symbols

---

## 1. Why this exists

asystem-core has shipped Phase 4 — but only for DFNS. The relevant
asystem-core code:

- `dfns-create-transfer/index.ts` — pool-wallet → external transfer
- `dfns-transfers` table — idempotency, status tracking
- `useCustodyCanPayout` — returns `'dfns' | null`, hard-coded
- `CustodyPayoutDialog` / `PayoutActions` — only invoke `dfns-create-transfer`

ORGON-side endpoints for the same flow are live and emit the same
webhook envelope as DFNS does. What's missing is the asystem-core
consumer: an `orgon-create-transfer` edge function and a flag flip
in `useCustodyCanPayout` so ORGON operators get the same UX.

This spec is the input to that work.

---

## 2. Flow

```
         frontend                  asystem-core edge        ORGON
            │                             │                   │
            │  click "Выплатить крипту"   │                   │
            │ ───────────────────────────▶│                   │
            │                             │ POST /v1/transactions
            │                             │ ─────────────────▶│
            │                             │  ◀──── tx_id ─────│  ← pending
            │                             │                   │
            │                             │ POST /v1/transactions/{id}/sign
            │                             │ ─────────────────▶│
            │                             │  ◀── status ──────│  ← signed
            │                             │                   │
            │                             │                   │ Safina broadcasts
            │                             │                   │   ↓
            │   webhook  transaction.broadcasted              │
            │   ◀────────────────────────────────── (Orgon → asystem-core)
            │                             │                   │
            │   webhook  transaction.confirmed                │
            │   ◀────────────────────────────────── (Orgon → asystem-core)
            │                             │                   │
```

Two-step `send` then `sign` is **required** — Safina won't broadcast
without the explicit sign call. The merchant's EC sits in the
wallet's slist as the sole signatory, so `sign` always succeeds (no
m-of-n waiting). It is a separate HTTP call only because the create
path returns instantly with `pending` status and lets you abort
before commitment. Treat it as atomic from asystem-core's perspective
— call both back-to-back, fail the whole `orgon-create-transfer`
invocation if either errors.

Terminal status arrives via webhook, not the POST response.
asystem-core writes the local row, returns to the UI, and the
webhook handler moves the `orders.status` to `completed` when
`transaction.confirmed` lands. Mirrors how DFNS works.

---

## 3. Endpoint contracts

All calls go through the standard HMAC scheme already implemented
in `asystem-core/supabase/functions/_shared/orgon-client.ts`. No new
auth work.

### 3.1 `POST /v1/transactions` — create pending

**Request body:**
```jsonc
{
  "wallet_id": "8f3a…",      // Orgon UUID of the SOURCE wallet (the operator's pool)
  "to_address": "TXabcd…",   // client's wallet from order.wallet_address
  "amount": "12.5",          // decimal string (NOT base units — ORGON converts internally)
  "asset": "USDT",           // symbol on the pool wallet's network
  "info": "order:ord-…"      // optional, ≤200 chars, ends up in Safina's tx.info field
}
```

**Response 201:**
```jsonc
{
  "id": "tx_…",                  // Safina tx_unid — primary key for /sign and /get
  "wallet_name": "operator-hot",
  "to_address": "TXabcd…",
  "value": "12.5",
  "token": "5010:::USDT###operator-hot",
  "network": 5010,
  "tx_hash": null,               // null until broadcast
  "status": "pending",
  "created_at": "2026-05-21T…",
  "updated_at": "2026-05-21T…"
}
```

**Error cases:**
- `404` — `wallet_id` not found under caller's merchant. The message
  is intentionally the same as cross-merchant access ("wallet not
  found") to avoid leaking existence.
- `400` — sandbox merchant trying to use a mainnet network.

**Idempotency:** the endpoint itself is **not** idempotent — every
POST creates a new `transactions` row. Idempotency is the caller's
job (see §5).

### 3.2 `POST /v1/transactions/{tx_id}/sign` — approve

**Request:** empty body.

**Response 200:** same shape as `POST /v1/transactions`, with status
upgraded to `signed` (or `broadcasted` if Safina was fast).

**Errors:**
- `404` — tx not found under merchant.

### 3.3 `GET /v1/transactions/{tx_id}` — poll

**Response 200:** same shape; status reflects current state.

Polling is acceptable but not the primary status channel — that's the
webhook (§4). Use this for reconciliation or admin debugging.

### 3.4 Status state machine

```
  pending  ──▶  signed  ──▶  broadcasted  ──▶  confirmed
     │            │              │                  ▲
     │            ▼              ▼                  │
     │         canceled        canceled         (terminal)
     ▼
   failed
```

| Local status | Meaning | Webhook fires |
|---|---|---|
| `pending` | Created on Safina, awaiting sign | — |
| `signed` | Merchant EC signed, queued for broadcast | — |
| `broadcasted` | Safina pushed tx to chain, `tx_hash` present | `transaction.broadcasted` |
| `confirmed` | On-chain confirmation observed | `transaction.confirmed` |
| `canceled` | Safina canceled (24h limit, slist mismatch) | (none — open question) |
| `failed` | Error during send/sign, or stuck >24h in `signed` | `transaction.failed` |

> Caveat from `WEBHOOKS.md`: `transaction.failed` is currently
> fired only by `transaction_failure_sweep` (24h timeout in
> `signed` without `tx_hash`). It is **not** terminal — a future
> chain-watcher integration may add real-time failure detection.

---

## 4. Webhook payloads

Envelope unchanged from Phase 3 (see `WEBHOOKS.md` and
`asystem-core/supabase/functions/orgon-webhook/index.ts`):

```jsonc
{
  "id": "wh_…",                      // delivery_id, stable across retries
  "type": "transaction.broadcasted",
  "merchant_id": "…",
  "created_at": "2026-05-21T…",
  "data": { …event-specific… }
}
```

### 4.1 `transaction.broadcasted` (transaction_service.py:654)

```jsonc
{
  "tx_id": "…",                      // Orgon's transactions.id (uuid)
  "tx_unid": "tx_…",                 // Safina id — same as response id from §3.1
  "tx_hash": "0xabc…",
  "wallet_name": "operator-hot",
  "to_address": "TX…",
  "amount": "12.5",
  "token": "5010:::USDT###operator-hot"
}
```

### 4.2 `transaction.confirmed` (transaction_service.py:660)

Same shape as `broadcasted`. Fires when on-chain confirmations cross
the threshold for the chain.

### 4.3 `transaction.failed` (transaction_failure_sweep.py:124)

```jsonc
{
  "tx_id": "…",
  "tx_unid": "tx_…",
  "tx_hash": null,
  "wallet_name": "operator-hot",
  "to_address": "TX…",
  "amount": "12.5",
  "token": "…",
  "reason": "timeout_no_broadcast"   // currently the only reason emitted
}
```

### 4.4 What to do on each event

Mirror `dfns-webhook/index.ts` event routing for the DFNS analog:

| Event | Action |
|---|---|
| `transaction.broadcasted` | `UPDATE orgon_transfers SET status='broadcasted', tx_hash=…, broadcasted_at=now()` |
| `transaction.confirmed` | `UPDATE orgon_transfers SET status='confirmed', confirmed_at=now()`; then `UPDATE orders SET status='completed' WHERE id = transfer.order_id` |
| `transaction.failed` | `UPDATE orgon_transfers SET status='failed', error_text=reason, failed_at=now()`. Do NOT auto-revert the order — keep it in `paid` so operator can retry or manual-payout. |

Order resolution: webhook `data.tx_id` (or `tx_unid`) links to
`orgon_transfers.orgon_tx_unid`, which has FK to `orders.id`. Same
join pattern as `dfns_transfers.order_id`.

---

## 5. Idempotency: one payout per order

Critical to avoid double-pay. ORGON cannot enforce this itself — it
doesn't know about `order_id`; the deduplication lives entirely on
the asystem-core side.

Pattern (lifted from `dfns-create-transfer/index.ts:165-181`):

```ts
// Inside orgon-create-transfer, BEFORE calling Orgon:
const { data: existing } = await admin
  .from('orgon_transfers')
  .select('id, orgon_tx_unid, status, tx_hash')
  .eq('order_id', orderId)
  .in('status', ['pending', 'signed', 'broadcasted', 'confirmed'])
  .order('created_at', { ascending: false })
  .limit(1)
  .maybeSingle()
if (existing) {
  return jsonResponse({
    ok: true, reused: true,
    transfer_id: existing.id,
    orgon_tx_unid: existing.orgon_tx_unid,
    status: existing.status,
    tx_hash: existing.tx_hash,
  })
}
```

Then insert a preliminary `orgon_transfers` row in status `pending`
**before** the POST to Orgon — so a crash between POST-send and
recording-id still surfaces the in-flight transfer on retry (it'll
match the dedup query above and short-circuit).

---

## 6. Suggested asystem-core schema: `orgon_transfers`

Mirror `dfns_transfers` (see `asystem-core/supabase/migrations/
20260523_001_dfns_transfers.sql`) with the Orgon-specific columns:

```sql
CREATE TABLE orgon_transfers (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  operator_id   uuid NOT NULL REFERENCES operators(id),
  order_id      uuid NOT NULL REFERENCES orders(id),
  source_wallet_id uuid NOT NULL REFERENCES orgon_wallets(id),
  orgon_tx_unid varchar(128),     -- Orgon's tx_unid (Safina-side), populated after POST succeeds
  external_id   varchar(50),      -- our short id sent as info
  status        varchar(24) NOT NULL,  -- pending|signed|broadcasted|confirmed|failed
  network       varchar(32) NOT NULL,
  to_address    text NOT NULL,
  amount        text NOT NULL,    -- decimal string as sent
  asset         varchar(32) NOT NULL,
  tx_hash       text,
  raw_response  jsonb,
  error_text    text,
  created_at    timestamptz NOT NULL DEFAULT now(),
  broadcasted_at timestamptz,
  confirmed_at  timestamptz,
  failed_at     timestamptz
);

CREATE UNIQUE INDEX orgon_transfers_order_active_uniq
  ON orgon_transfers(order_id)
  WHERE status IN ('pending','signed','broadcasted','confirmed');

CREATE INDEX orgon_transfers_orgon_tx_unid_idx
  ON orgon_transfers(orgon_tx_unid)
  WHERE orgon_tx_unid IS NOT NULL;
```

The partial unique on `(order_id) WHERE status NOT IN failed terminal`
enforces the "one active payout per order" rule at the DB level.

---

## 7. Reference implementation: `orgon-create-transfer/index.ts`

Drop-in Deno edge function mirroring `dfns-create-transfer` structure.
Uses the already-shipped `_shared/orgon-client.ts`.

```ts
/**
 * ORGON Custody Phase 4 — outgoing payout (buy/swap orders).
 *
 * Flow:
 *  1. Receive { operator_id, order_id }
 *  2. Authz (admin / operator_admin / staff с orders.complete permission)
 *  3. Load order: status='paid', operator matches, wallet_address present
 *  4. Resolve pool wallet: orgon_wallets WHERE operator+network purpose='hot'
 *  5. Idempotency: existing active orgon_transfers for order_id → reuse
 *  6. Insert preliminary 'pending' row
 *  7. POST /v1/transactions с {wallet_id, to_address, amount, asset}
 *  8. POST /v1/transactions/{id}/sign (sole-signatory slist → instant)
 *  9. UPDATE row → orgon_tx_unid + status='signed' (or whatever Orgon returned)
 * 10. Return { transfer_id, status }. Order stays 'paid' — webhook flips to
 *     'completed' on transaction.confirmed.
 */
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { handleOptions, jsonResponse } from '../_shared/cors.ts'
import { loadOrgonCreds, orgonRequest } from '../_shared/orgon-client.ts'

interface OrgonTxResponse {
  id?: string
  status?: string
  tx_hash?: string | null
  network?: number
  created_at?: string
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return handleOptions()
  if (req.method !== 'POST') return jsonResponse({ error: 'POST only' }, 405)

  try {
    const authHeader = req.headers.get('Authorization') ?? ''
    if (!authHeader.startsWith('Bearer ')) {
      return jsonResponse({ error: 'Bearer token required' }, 401)
    }

    const body = await req.json().catch(() => ({}))
    const operatorId = body.operator_id as string | undefined
    const orderId = body.order_id as string | undefined
    if (!operatorId || !orderId) {
      return jsonResponse({ error: 'operator_id, order_id required' }, 400)
    }

    const admin = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    )

    // … authz (identical to dfns-create-transfer:86-115) …

    // Load order
    const { data: order } = await admin
      .from('orders')
      .select('id, operator_id, status, wallet_address, network, to_amount, to_currency')
      .eq('id', orderId)
      .maybeSingle()
    if (!order) return jsonResponse({ stage: 'load_order', error: 'not found' }, 404)
    if (order.operator_id !== operatorId) {
      return jsonResponse({ stage: 'load_order', error: 'cross-operator' }, 403)
    }
    if (order.status !== 'paid') {
      return jsonResponse({
        stage: 'check_status',
        error: `order must be 'paid' (current: ${order.status})`,
      }, 400)
    }

    // Resolve operator's pool wallet — ORGON uses `purpose` not `wallet_role`.
    // 'hot' is the equivalent of DFNS pool. Operators preconfigure these via
    // the ORGON admin UI; we just look up by (operator, network).
    //
    // NB: orgon_wallets.network is the chain_id as varchar
    //     (e.g. "5010"), whereas order.network is whatever the
    //     frontend wrote (slug or chain_id depending on the path).
    //     Normalize before the lookup.
    const networkId = String(order.network).replace(/^.*-/, '')  // sketch — see real impl
    const { data: pool } = await admin
      .from('orgon_wallets')
      .select('id, orgon_wallet_id, deposit_address, status')
      .eq('operator_id', operatorId)
      .eq('network', networkId)
      .eq('purpose', 'hot')  // or list ['hot','treasury'] — operator's choice
      .maybeSingle()
    if (!pool?.orgon_wallet_id) {
      return jsonResponse({
        stage: 'resolve_pool',
        error: `no hot wallet for (operator, ${networkId})`,
        hint: 'Создайте hot-кошелёк в ORGON admin UI и добавьте сюда',
      }, 400)
    }

    // Idempotency
    const { data: existing } = await admin
      .from('orgon_transfers')
      .select('id, orgon_tx_unid, status, tx_hash')
      .eq('order_id', orderId)
      .in('status', ['pending', 'signed', 'broadcasted', 'confirmed'])
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()
    if (existing) {
      return jsonResponse({
        ok: true, reused: true,
        transfer_id: existing.id,
        orgon_tx_unid: existing.orgon_tx_unid,
        status: existing.status,
        tx_hash: existing.tx_hash,
      })
    }

    // ORGON expects decimal string amount. order.to_amount is decimal already.
    const amount = String(order.to_amount)
    const asset = order.to_currency       // e.g. 'USDT'
    const externalId = `o:${orderId.replace(/-/g, '').slice(0, 8)}:` +
                       `${crypto.randomUUID().replace(/-/g, '').slice(0, 12)}`

    // Preliminary insert
    const { data: row, error: insertErr } = await admin
      .from('orgon_transfers')
      .insert({
        operator_id: operatorId,
        order_id: orderId,
        source_wallet_id: pool.id,
        external_id: externalId,
        status: 'pending',
        network: networkId,
        to_address: order.wallet_address!,
        amount,
        asset,
      })
      .select('id')
      .single()
    if (insertErr || !row) {
      return jsonResponse({ stage: 'insert_transfer', error: insertErr?.message }, 500)
    }

    // Load credentials
    let creds
    try {
      creds = await loadOrgonCreds(admin, operatorId)
    } catch (e) {
      return jsonResponse({
        stage: 'load_creds',
        error: e instanceof Error ? e.message : 'creds error',
      }, 400)
    }

    // Step 1: POST /v1/transactions
    const sendRes = await orgonRequest<OrgonTxResponse>(creds, {
      method: 'POST',
      path: '/v1/transactions',
      body: {
        wallet_id: pool.orgon_wallet_id,
        to_address: order.wallet_address,
        amount,
        asset,
        info: externalId,
      },
    })
    if (!sendRes.ok || !sendRes.data?.id) {
      await admin.from('orgon_transfers').update({
        status: 'failed',
        error_text: sendRes.errorText ?? 'no tx id in send response',
        failed_at: new Date().toISOString(),
      }).eq('id', row.id)
      return jsonResponse({
        stage: 'orgon_send', status: sendRes.status,
        error: sendRes.errorText, request_id: sendRes.requestId,
      }, 502)
    }

    const txUnid = sendRes.data.id

    // Step 2: POST /v1/transactions/{id}/sign — instant because slist
    // is sole-signatory operator EC.
    const signRes = await orgonRequest<OrgonTxResponse>(creds, {
      method: 'POST',
      path: `/v1/transactions/${txUnid}/sign`,
    })
    if (!signRes.ok) {
      await admin.from('orgon_transfers').update({
        status: 'failed',
        orgon_tx_unid: txUnid,
        error_text: signRes.errorText ?? 'sign call failed',
        failed_at: new Date().toISOString(),
      }).eq('id', row.id)
      return jsonResponse({
        stage: 'orgon_sign', status: signRes.status,
        error: signRes.errorText, request_id: signRes.requestId,
      }, 502)
    }

    const orgonStatus = (signRes.data?.status ?? 'signed').toLowerCase()
    // ORGON statuses: pending|signed|broadcasted|confirmed|canceled|failed
    // Map to ours 1:1 (we share the vocabulary).
    const ourStatus = ['signed','broadcasted','confirmed','failed'].includes(orgonStatus)
      ? orgonStatus : 'signed'

    const updates: Record<string, unknown> = {
      orgon_tx_unid: txUnid,
      status: ourStatus,
      raw_response: signRes.data as unknown as Record<string, unknown>,
    }
    if (signRes.data?.tx_hash) updates.tx_hash = signRes.data.tx_hash
    if (ourStatus === 'broadcasted') updates.broadcasted_at = new Date().toISOString()
    if (ourStatus === 'confirmed') updates.confirmed_at = new Date().toISOString()

    await admin.from('orgon_transfers').update(updates).eq('id', row.id)

    return jsonResponse({
      ok: true, reused: false,
      transfer_id: row.id,
      orgon_tx_unid: txUnid,
      status: ourStatus,
      tx_hash: signRes.data?.tx_hash ?? null,
    })
  } catch (e) {
    return jsonResponse({
      ok: false, error: e instanceof Error ? e.message : 'Internal error',
    }, 500)
  }
})
```

---

## 8. `useCustodyCanPayout` extension

Today (asystem-core/src/hooks/useCustodyCanPayout.ts):

```ts
interface CustodyPayoutInfo {
  canPayout: boolean
  poolAddress: string | null
  provider: "dfns" | null   // ← hard-coded
  reason: CustodyPayoutReason
}
```

Suggested extension to honor ORGON:

```ts
interface CustodyPayoutInfo {
  canPayout: boolean
  poolAddress: string | null
  provider: "orgon" | "dfns" | null
  reason: CustodyPayoutReason
}

// inside the hook:
if (provider === 'orgon') {
  const { data: pool } = useQuery({
    queryKey: ["custody-pool", operatorId, provider, network],
    queryFn: async () => {
      if (!operatorId || !network) return null
      const { data } = await supabase
        .from("orgon_wallets")
        .select("deposit_address, status")
        .eq("operator_id", operatorId)
        .eq("network", network)
        .eq("purpose", "hot")      // hot wallet is ORGON's payout source
        .maybeSingle()
      return data
    },
    enabled: !!operatorId && !!network && provider === "orgon",
    staleTime: 30 * 1000,
  })
  const active = !!pool?.deposit_address &&
    (pool.status === 'active' || pool.status === 'Active')
  if (!active) {
    return { canPayout: false, poolAddress: null, provider: 'orgon', reason: 'no-pool' }
  }
  return {
    canPayout: true,
    poolAddress: pool.deposit_address!,
    provider: 'orgon',
    reason: null,
  }
}
```

`CustodyPayoutDialog` and `PayoutActions` then dispatch to
`provider === 'dfns' ? 'dfns-create-transfer' : 'orgon-create-transfer'`,
same pattern as `useSellOrder` already does for provisioning.

---

## 9. Sandbox testing checklist for Эрмек

When the asystem-core side is built:

1. Activate `orgon-custody` on a test operator (deactivates
   `dfns-custody`).
2. Provision an ORGON `hot` wallet on Tron Nile (chain_id 5010)
   through ORGON's admin UI; fund it from a faucet.
3. Configure the operator's `manual_wallet_address` to include
   that hot wallet so the sell-order flow can target it.
4. Run a sell-order end-to-end on a sandbox merchant:
   buy USDT → pays USDT-TRC20 to client wallet → expects ORGON
   to broadcast and the webhook to flip order to `completed`.
5. Verify `orgon_transfers` row reaches `confirmed` within ~2 min
   on TronNile, and `orders.status = 'completed'`.
6. Replay test: call `orgon-create-transfer` twice for the same
   `order_id`; the second call should return `reused: true` with
   the same `transfer_id`.

Sandbox credentials (`ORGON_KEY` / `ORGON_SECRET` / `ORGON_BASE_URL`)
are unchanged from the Phase 1–3 sandbox merchant — no new key
issuance needed.

---

## 10. Open questions for this phase

- **`asset` vs `contract`.** ORGON accepts a symbol (`USDT`); DFNS
  uses `kind=Erc20 + contract=0x…`. On non-EVM chains (Tron), symbol
  is unambiguous. On EVM chains with multiple USDT-named tokens, the
  symbol-only path may be wrong. Action: ORGON-side, decide whether
  `POST /v1/transactions` needs an optional `contract` param. Not
  blocking for Tron / sandbox.
- **`canceled` webhook.** Status `canceled` exists locally but no
  publisher emits it as a webhook. Decide if asystem-core needs it
  (likely yes — to unblock manual retry UX).
- **Rate-limit / fee budget signaling.** Not in scope here, but
  asystem-core will eventually want a `fees_estimate` endpoint
  before pushing transfers. Tracked separately.
