// Minimal payment-receiver. Real code, not pseudocode — runs as-is
// after `cp .env.example .env && npm install && npm run dev`.

import express from "express";
import { OrgonClient, WebhooksAPI, OrgonError } from "@orgon/sdk";

const PORT = Number(process.env.PORT ?? 4242);
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET!;
if (!WEBHOOK_SECRET) throw new Error("WEBHOOK_SECRET must be set");

const orgon = new OrgonClient({
  apiKey: process.env.ORGON_KEY!,
  secret: process.env.ORGON_SECRET!,
  baseUrl: process.env.ORGON_BASE_URL,
});

// In-memory ledger. Use Postgres in production.
const balances = new Map<string, Map<string, number>>(); // user_id → asset → amount

function credit(userId: string, asset: string, delta: number) {
  if (!balances.has(userId)) balances.set(userId, new Map());
  const m = balances.get(userId)!;
  m.set(asset, (m.get(asset) ?? 0) + delta);
}

const app = express();

// IMPORTANT: webhook handler needs the *raw* body to verify HMAC.
// Mount express.raw BEFORE express.json so the order matters per
// route.
app.post(
  "/orgon/webhook",
  express.raw({ type: "application/json" }),
  (req, res) => {
    const tsHeader = req.header("x-orgon-webhook-timestamp");
    const sigHeader = req.header("x-orgon-webhook-signature");
    if (!tsHeader || !sigHeader) return res.status(401).send("missing signature");

    const ok = WebhooksAPI.verify({
      secret: WEBHOOK_SECRET,
      timestamp: tsHeader,
      signature: sigHeader,
      rawBody: req.body as Buffer,
    });
    if (!ok) return res.status(401).send("bad signature");

    const event = JSON.parse((req.body as Buffer).toString("utf8"));
    switch (event.type) {
      case "wallet.deposit.detected": {
        const d = event.data;
        const userId: string | null = d.end_user_id;
        if (userId) {
          credit(userId, d.asset, Number(d.amount));
          console.log(
            `[deposit] +${d.amount} ${d.asset} → user ${userId} (tx ${d.tx_hash})`,
          );
        }
        break;
      }
      case "webhook.test":
        console.log("[test] received", event.data);
        break;
      default:
        console.log("[event]", event.type);
    }
    res.json({ ok: true });
  },
);

// Rest of the app uses json body parsing as normal.
app.use(express.json());

// Onboard endpoint your frontend hits after sign-up. Returns the
// user's per-network deposit address.
app.post("/api/onboard", async (req, res) => {
  const { external_id, email, network } = req.body as {
    external_id: string;
    email: string;
    network?: number;
  };
  try {
    const user = await orgon.users.create({ external_id, email });
    const wallet = await orgon.wallets.create({
      network: network ?? 5010,
      end_user_id: user.id,
    });
    res.json({ user, wallet });
  } catch (e) {
    if (e instanceof OrgonError) {
      return res.status(e.status).json({
        error: e.message,
        body: e.body,
      });
    }
    res.status(500).json({ error: String(e) });
  }
});

// Internal balance check.
app.get("/api/balance/:userId", (req, res) => {
  const m = balances.get(req.params.userId);
  if (!m) return res.json({ assets: {} });
  res.json({ assets: Object.fromEntries(m) });
});

app.listen(PORT, () => {
  console.log(`payment-receiver listening on http://localhost:${PORT}`);
});
