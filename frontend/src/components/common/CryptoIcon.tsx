"use client";

import { cn } from "@/lib/utils";
import Image from "next/image";
import { TokenIcon, NetworkIcon as Web3NetworkIcon } from "@web3icons/react/dynamic";

function FallbackIcon({ label, className }: { label: string; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground dark:bg-muted dark:text-muted-foreground",
        className
      )}
    >
      {label.slice(0, 2).toUpperCase()}
    </div>
  );
}

function OrgonIcon({ size }: { size: number }) {
  return <Image src="/orgon-icon.png" alt="ORGON" width={size} height={size} className="rounded-full" />;
}

function isOrgon(name: string): boolean {
  return name.toUpperCase() === "ORGON";
}

export function CryptoIcon({
  token,
  size = "md",
  className,
}: {
  token: string;
  size?: "sm" | "md";
  className?: string;
}) {
  const dim = size === "sm" ? 24 : 32;
  const sizeClass = size === "sm" ? "h-6 w-6" : "h-8 w-8";

  return (
    <div className={cn("flex items-center justify-center", sizeClass, className)}>
      {isOrgon(token) ? (
        <OrgonIcon size={dim} />
      ) : (
        <TokenIcon
          symbol={token.toUpperCase()}
          size={dim}
          variant="branded"
          fallback={<FallbackIcon label={token} className={sizeClass} />}
        />
      )}
    </div>
  );
}

const networkMap: Record<string, string> = {
  bitcoin: "bitcoin",
  btc: "bitcoin",
  ethereum: "ethereum",
  etherium: "ethereum",
  eth: "ethereum",
  tron: "tron",
  trx: "tron",
};

function resolveNetworkName(name: string): string | null {
  const lower = name.toLowerCase();
  for (const [key, value] of Object.entries(networkMap)) {
    if (lower.includes(key)) return value;
  }
  return null;
}

export function NetworkIcon({
  networkName,
  isTestnet = false,
  size = "md",
  className,
}: {
  networkName: string;
  isTestnet?: boolean;
  size?: "sm" | "md";
  className?: string;
}) {
  const dim = size === "sm" ? 24 : 32;
  const sizeClass = size === "sm" ? "h-6 w-6" : "h-8 w-8";
  const resolved = resolveNetworkName(networkName);

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-lg",
        isTestnet ? "opacity-60" : "",
        sizeClass,
        className
      )}
    >
      {networkName.toLowerCase().includes("orgon") ? (
        <OrgonIcon size={dim} />
      ) : resolved ? (
        <Web3NetworkIcon
          name={resolved}
          size={dim}
          variant="branded"
          fallback={<FallbackIcon label={networkName} className={sizeClass} />}
        />
      ) : (
        <FallbackIcon label={networkName} className={sizeClass} />
      )}
    </div>
  );
}
