// Wallet display name resolution.
//
// Backend returns wallets with `label: null` (the human-readable label
// migration is pending) and `name` populated by the random hex
// `myUNID` from Safina (e.g. "11FCEC937030E81C45258DE8002BE6F5"). This
// helper produces a presentable display name without inventing data:
//
//   1. If `label` is non-empty → return it (highest-quality source).
//   2. Else if `addr` is non-empty → "<NetworkName> · <addr_short>".
//   3. Else fall back to a UNID short form so we never show 32 chars
//      of unbroken hex on a list view.
//
// Canonical UNID stays available for tooltips / detail pages — this
// formatter is purely for column / heading display.

export interface WalletForDisplay {
  label?: string | null;
  name?: string | null;
  /** Some payloads use `wallet_name` instead of `name`. */
  wallet_name?: string | null;
  my_unid?: string | null;
  addr?: string | null;
  network?: number | string | null;
}

// Authoritative Safina network IDs (from live GET /api/networks). The
// previous mapping (5000=BSC, 5020=ETH, 5040=BTC) was a stale guess
// based on stub_client.py data and never matched production. These
// IDs come from `network_id` in Safina's response and are stable per
// tenant.
const NETWORK_NAME: Record<string, string> = {
  "1000": "BTC",
  "3000": "ETH",
  "3040": "ETH-Sepolia",
  "5000": "TRX",
  "5010": "TRX-Nile",
  "5800": "ORGON",
  "5810": "ORGON-test",
};

export function networkName(n?: number | string | null): string {
  if (n === null || n === undefined || n === "") return "Wallet";
  const key = String(n);
  return NETWORK_NAME[key] ?? `NET-${key}`;
}

export function shortenAddr(addr: string, head = 6, tail = 4): string {
  const a = addr.trim();
  if (!a) return "";
  if (a.length <= head + tail + 1) return a;
  return `${a.slice(0, head)}…${a.slice(-tail)}`;
}

function shortenUnid(unid: string, head = 8, tail = 4): string {
  const u = unid.trim();
  if (!u) return "";
  if (u.length <= head + tail + 1) return u;
  return `${u.slice(0, head)}…${u.slice(-tail)}`;
}

export function formatWalletDisplayName(w: WalletForDisplay): string {
  const rawLabel = (w.label ?? "").trim();
  if (rawLabel) return rawLabel;

  const net = networkName(w.network);
  const addr = (w.addr ?? "").trim();
  if (addr) return `${net} · ${shortenAddr(addr)}`;

  const unidSource = (w.my_unid ?? w.name ?? w.wallet_name ?? "").trim();
  if (unidSource) return `${net} · ${shortenUnid(unidSource)}`;

  return net;
}

/** Canonical UNID for tooltips / copy actions. Returns "" when missing. */
export function walletCanonicalId(w: WalletForDisplay): string {
  return (w.my_unid ?? w.name ?? w.wallet_name ?? "").trim();
}
