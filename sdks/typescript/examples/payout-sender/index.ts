import { OrgonClient, OrgonError } from "@orgon/sdk";

const args = parseArgs(process.argv.slice(2));
if (!args["user-id"] || !args.to || !args.amount) {
  console.error("usage: npm start -- --user-id <id> --to <addr> --amount <decimal> [--asset TRX] [--network 5010]");
  process.exit(2);
}

const orgon = new OrgonClient({
  apiKey: process.env.ORGON_KEY!,
  secret: process.env.ORGON_SECRET!,
  baseUrl: process.env.ORGON_BASE_URL,
});

const network = Number(args.network ?? 5010);
const asset = String(args.asset ?? "TRX");

async function main() {
  // 1. Ensure the user exists (idempotent on external_id).
  const user = await orgon.users.create({
    external_id: String(args["user-id"]),
    email: String(args.email ?? `${args["user-id"]}@example.test`),
  });
  console.log("user", user.id);

  // 2. Find or create the wallet for this network.
  const list = await orgon.wallets.listForUser(user.id);
  const existing = list.wallets.find((w) => w.network === network);
  const wallet = existing ?? (await orgon.wallets.create({ network, end_user_id: user.id }));
  console.log("wallet", wallet.id, wallet.status, wallet.address);
  if (!wallet.address) {
    console.log("wallet not activated yet — exit, try again later");
    process.exit(0);
  }

  // 3. Initiate transfer.
  const sent = await orgon.transactions.send({
    wallet_id: wallet.id,
    to_address: String(args.to),
    amount: String(args.amount),
    asset,
  });
  console.log("tx queued", sent.id, sent.status);

  // 4. Sign it (the merchant's EC key on the server signs; this call
  // tells Safina to mark the slist EC slot as signed).
  await orgon.transactions.sign(sent.id);

  // 5. Poll until tx_hash appears.
  const deadlineMs = Date.now() + 5 * 60 * 1000;
  while (Date.now() < deadlineMs) {
    await new Promise((r) => setTimeout(r, 6_000));
    const tx = await orgon.transactions.get(sent.id);
    if (tx.tx_hash) {
      console.log("broadcasted", tx.tx_hash, "status", tx.status);
      return;
    }
    console.log("…still waiting", tx.status);
  }
  console.warn("timeout — check status later via orgon.transactions.get");
}

main().catch((e) => {
  if (e instanceof OrgonError) {
    console.error(`ORGON ${e.status}:`, e.message, e.body);
  } else {
    console.error(e);
  }
  process.exit(1);
});

function parseArgs(argv: string[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a && a.startsWith("--")) {
      const k = a.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith("--")) {
        out[k] = "true";
      } else {
        out[k] = next;
        i++;
      }
    }
  }
  return out;
}
