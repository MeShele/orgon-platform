"use client";

/**
 * ThemeToggle — switches between light and dark, persists to `orgon_theme`
 * cookie (read by RootLayout on next request).
 *
 * On mount it syncs from cookie / system preference so SSR mismatch is
 * avoided. Mutating `document.documentElement.classList` directly so the
 * change is instant; the cookie is only consulted on next full request.
 */

import * as React from "react";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

type Theme = "light" | "dark";
const COOKIE = "orgon_theme";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const found = document.cookie.split("; ").find((c) => c.startsWith(name + "="));
  return found ? decodeURIComponent(found.split("=").slice(1).join("=")) : null;
}

function writeCookie(name: string, value: string, maxAgeDays = 365) {
  if (typeof document === "undefined") return;
  const maxAge = maxAgeDays * 24 * 60 * 60;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAge}; samesite=lax`;
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
}

export function ThemeToggle({ className }: { className?: string }) {
  const [theme, setTheme] = React.useState<Theme>("light");

  // Sync from current DOM class on mount (it was set by SSR via cookie)
  React.useEffect(() => {
    const initial: Theme = document.documentElement.classList.contains("dark") ? "dark" : "light";
    setTheme(initial);
  }, []);

  const toggle = React.useCallback(() => {
    setTheme((prev) => {
      const next: Theme = prev === "dark" ? "light" : "dark";
      applyTheme(next);
      writeCookie(COOKIE, next);
      return next;
    });
  }, []);

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
      className={cn(
        "inline-flex items-center justify-center w-9 h-9 border border-border",
        "text-muted-foreground",
        "hover:text-foreground hover:bg-muted hover:border-strong",
        "active:scale-95",
        "transition-all duration-150",
        className,
      )}
    >
      <Icon
        icon={theme === "dark" ? "solar:sun-linear" : "solar:moon-linear"}
        className="text-[16px]"
      />
    </button>
  );
}

export default ThemeToggle;
