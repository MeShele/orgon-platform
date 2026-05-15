# Payment receiver

Minimal Express server that registers an end-user with ORGON,
provisions a Tron deposit wallet for them, exposes the address to a
client, and credits an internal balance ledger when ORGON sends a
`wallet.deposit.detected` webhook.

This is the smallest viable integration for a crypto-exchanger
landing page.

## Run

```bash
cp .env.example .env  # fill in ORGON_KEY / ORGON_SECRET / WEBHOOK_SECRET
npm install
npm run dev
```

Then point ORGON's webhook at your public URL:

```bash
curl -X PUT https://orgon.asystem.ai/v1/webhooks/config \
  -H "X-ORGON-Key: $ORGON_KEY" \
  -H "X-ORGON-Timestamp: $(date +%s%3N)" \
  -H "X-ORGON-Nonce: $(uuidgen)" \
  -H "X-ORGON-Signature: $SIG" \
  -d '{"url":"https://your-public-host.example.com/orgon/webhook","secret":"'$WEBHOOK_SECRET'"}'
```

(The SDK does this for you cleanly — see the snippet in `index.ts`.)
