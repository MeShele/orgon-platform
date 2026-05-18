import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function shortenAddress(address: string, startChars = 6, endChars = 4): string {
  if (!address || address.length <= startChars + endChars) {
    return address;
  }
  return `${address.slice(0, startChars)}...${address.slice(-endChars)}`;
}

/**
 * Format a financial amount preserving FULL precision.
 *
 * Earlier this helper compacted ≥1k into "1.82K", which silently lost
 * up to 99% of a balance's information (1820 TRX → "1.82K" hides
 * 15 TRX). For amounts the user can spend, that's wrong — render
 * the whole number with locale-aware grouping separators so 1820
 * shows as "1 820" / "1,820" depending on locale.
 *
 * If you actually need K/M abbreviations (chart axes, marketing
 * headline stats), use `compactValue` instead.
 */
export function formatValue(value: string | number, decimals = 2): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return "0";
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
    // useGrouping defaults to true → "1 820" or "1,820" by locale.
  }).format(num);
}

/**
 * Locale-aware compact notation (e.g. "1.8K", "2.4M") for situations
 * where the small footprint matters more than per-unit accuracy —
 * dashboard headers, chart axes. Never use this for a value the user
 * can act on (sending, signing, paying).
 */
export function compactValue(value: string | number, decimals = 1): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (!Number.isFinite(num)) return "0";
  return new Intl.NumberFormat(undefined, {
    notation: "compact",
    maximumFractionDigits: decimals,
  }).format(num);
}

export function formatTimestamp(timestamp: string | Date): string {
  try {
    const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;
    return format(date, "MMM d, yyyy HH:mm");
  } catch (e) {
    return String(timestamp);
  }
}
