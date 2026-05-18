// Per-network display + chain-explorer config.
//
// Single source of truth used by the wallet detail view, send form,
// transaction history etc. so we don't sprinkle TRX/Tronscan literals
// around any time we render something network-dependent.

export type NetworkFamily = "btc" | "evm" | "tron" | "orgon";

export interface NetworkConfig {
  id: number;
  shortName: string;        // "BTC" / "ETH" / "TRX" / "ORGON"
  fullName: string;         // "Bitcoin" / "Ethereum" / "Tron" / "ORGON"
  family: NetworkFamily;
  isTestnet: boolean;
  nativeSymbol: string;     // currency code shown in amount field
  addressPlaceholder: string;
  explorerName: string;     // "Blockstream" / "Etherscan" / "Tronscan" / "ORGONScan"
  explorerTxBase: string;   // hash gets appended directly
  explorerAddrBase: string;
}

const CONFIGS: Record<number, NetworkConfig> = {
  1000: {
    id: 1000,
    shortName: "BTC",
    fullName: "Bitcoin",
    family: "btc",
    isTestnet: false,
    nativeSymbol: "BTC",
    addressPlaceholder: "bc1q… или 1… (Bitcoin)",
    explorerName: "Blockstream",
    explorerTxBase: "https://blockstream.info/tx/",
    explorerAddrBase: "https://blockstream.info/address/",
  },
  3000: {
    id: 3000,
    shortName: "ETH",
    fullName: "Ethereum",
    family: "evm",
    isTestnet: false,
    nativeSymbol: "ETH",
    addressPlaceholder: "0x… (Ethereum)",
    explorerName: "Etherscan",
    explorerTxBase: "https://etherscan.io/tx/",
    explorerAddrBase: "https://etherscan.io/address/",
  },
  3040: {
    id: 3040,
    shortName: "ETH-Sepolia",
    fullName: "Ethereum Sepolia (testnet)",
    family: "evm",
    isTestnet: true,
    nativeSymbol: "ETH",
    addressPlaceholder: "0x… (Sepolia)",
    explorerName: "Sepolia Etherscan",
    explorerTxBase: "https://sepolia.etherscan.io/tx/",
    explorerAddrBase: "https://sepolia.etherscan.io/address/",
  },
  5000: {
    id: 5000,
    shortName: "TRX",
    fullName: "Tron",
    family: "tron",
    isTestnet: false,
    nativeSymbol: "TRX",
    addressPlaceholder: "T… (Tron)",
    explorerName: "Tronscan",
    explorerTxBase: "https://tronscan.org/#/transaction/",
    explorerAddrBase: "https://tronscan.org/#/address/",
  },
  5010: {
    id: 5010,
    shortName: "TRX-Nile",
    fullName: "Tron Nile (testnet)",
    family: "tron",
    isTestnet: true,
    nativeSymbol: "TRX",
    addressPlaceholder: "T… (Tron Nile)",
    explorerName: "Nile Tronscan",
    explorerTxBase: "https://nile.tronscan.org/#/transaction/",
    explorerAddrBase: "https://nile.tronscan.org/#/address/",
  },
  5800: {
    id: 5800,
    shortName: "ORGON",
    fullName: "ORGON",
    family: "orgon",
    isTestnet: false,
    nativeSymbol: "ORGON",
    // ORGON addresses use the same Base58 layout as Tron (single-byte
    // prefix, length 34). Until a dedicated ORGON explorer ships, show
    // a generic placeholder.
    addressPlaceholder: "адрес ORGON",
    explorerName: "ORGON Explorer",
    explorerTxBase: "",   // explorer not public yet
    explorerAddrBase: "",
  },
  5810: {
    id: 5810,
    shortName: "ORGON-test",
    fullName: "ORGON TestNet",
    family: "orgon",
    isTestnet: true,
    nativeSymbol: "ORGON",
    addressPlaceholder: "адрес ORGON-test",
    explorerName: "ORGON Explorer",
    explorerTxBase: "",
    explorerAddrBase: "",
  },
};

/** Returns the canonical config for a network id, or null when we don't
 *  know it (caller should render conservatively). */
export function getNetworkConfig(n?: number | string | null): NetworkConfig | null {
  if (n === null || n === undefined || n === "") return null;
  const k = Number(n);
  if (!Number.isFinite(k)) return null;
  return CONFIGS[k] ?? null;
}

/** Tx-explorer URL for a given (network, hash). Returns `null` when the
 *  network has no public explorer configured yet. */
export function explorerTxUrl(n: number | string | null | undefined, hash: string): string | null {
  if (!hash) return null;
  const cfg = getNetworkConfig(n);
  if (!cfg || !cfg.explorerTxBase) return null;
  return cfg.explorerTxBase + hash;
}

/** Address-explorer URL for a given (network, addr). Same null contract. */
export function explorerAddrUrl(n: number | string | null | undefined, addr: string): string | null {
  if (!addr) return null;
  const cfg = getNetworkConfig(n);
  if (!cfg || !cfg.explorerAddrBase) return null;
  return cfg.explorerAddrBase + addr;
}
