# @orgon/sdk

Official TypeScript SDK for the [ORGON](https://orgon.asystem.ai) B2B custodial
wallet API. Used by exchangers, banks, and exchanges to provision per-user
wallets, receive deposit webhooks, and send transactions through Safina Pay
under the hood.

Full API reference: <https://orgon.asystem.ai/api/docs>.
Quickstart with copy-paste snippets: <https://orgon.asystem.ai/developers>.

## Install

```bash
npm i @orgon/sdk
# or
pnpm add @orgon/sdk
```

Node ≥ 18 (we use the built-in `fetch`, `crypto.randomUUID`, and `crypto.createHmac`).

## Usage

```ts
import { OrgonClient, OrgonError } from "@orgon/sdk";

const orgon = new OrgonClient({
  apiKey: process.env.ORGON_KEY!,    // okl_... (live) or okt_... (sandbox)
  secret: process.env.ORGON_SECRET!, // shown ONCE in Settings → API ключи
});

// 1. Register an end-user (idempotent on external_id)
const user = await orgon.users.create({
  external_id: "user-123",
  email: "alice@example.com",
});

// 2. Provision a Tron deposit wallet
const wallet = await orgon.wallets.create({
  network: 5010,                 // Tron Nile testnet
  end_user_id: user.id,
});
// wallet.address is null until Safina activates (a confirmation
// email is sent to alice@example.com; ~5–10 min after click).

// 3. Send TRX
const tx = await orgon.transactions.send({
  wallet_id: wallet.id,
  to_address: "TGt6Y5Phic5CHgbzkYE7omUMxs6WHfgoDB",
  amount: "1.5",
  asset: "TRX",
});
await orgon.transactions.sign(tx.id);

// 4. Errors come back typed
try {
  await orgon.wallets.get("00000000-0000-0000-0000-000000000000");
} catch (e) {
  if (e instanceof OrgonError) {
    console.error(e.status, e.body);
  }
}
```

## Webhooks

Configure your callback URL:

```ts
await orgon.webhooks.config.update({
  url: "https://api.your-exchange.com/orgon/webhook",
  secret: "long-random-string-stored-in-your-vault",
});
```

Then verify incoming events in your HTTP handler — use the static helper so
you don't have to recreate the signature check:

```ts
import { WebhooksAPI } from "@orgon/sdk";

app.post("/orgon/webhook", express.raw({ type: "application/json" }), (req, res) => {
  const ok = WebhooksAPI.verify({
    secret: process.env.WEBHOOK_SECRET!,
    timestamp: req.header("X-ORGON-Webhook-Timestamp")!,
    signature: req.header("X-ORGON-Webhook-Signature")!,
    rawBody: req.body,        // Buffer thanks to express.raw
  });
  if (!ok) return res.status(401).end();

  const event = JSON.parse(req.body.toString("utf8"));
  switch (event.type) {
    case "wallet.deposit.detected":
      // credit user balance, mark order paid, etc.
      break;
    case "transaction.confirmed":
      // mark payout completed
      break;
  }
  res.json({ ok: true });
});
```

## Supported networks (V1)

| ID    | Name                | Native | Tokens               |
|-------|---------------------|--------|----------------------|
| 1000  | Bitcoin             | BTC    | —                    |
| 3000  | Ethereum            | ETH    | USDT, USDC           |
| 3040  | Ethereum Sepolia    | ETH    | (per contract)       |
| 5000  | Tron                | TRX    | USDT, USDC, LDFT, …  |
| 5010  | Tron Nile testnet   | TRX    | USDT, LDFT, …        |

Sandbox keys (prefix `okt_`) are restricted to testnet networks.

## License

Apache-2.0
