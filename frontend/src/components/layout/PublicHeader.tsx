// PublicHeader v2 — landing chrome (тонкий, без burger-mobile drawer для упрощения)
// Лого: наш существующий orgon-icon.png + "ASYSTEM / ORGON" wordmark

"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "./ThemeToggle";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

// Detect a logged-in user purely from cookies/localStorage (no API call)
// so the public header can swap "Войти / Демо" → "Кабинет" instantly.
function useSignedInState(): { signedIn: boolean; ready: boolean } {
  const [signedIn, setSignedIn] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hasCookie = document.cookie
      .split("; ")
      .some((c) => c.startsWith("orgon_access_token="));
    const hasStorage = !!localStorage.getItem("orgon_access_token");
    setSignedIn(hasCookie && hasStorage);
    setReady(true);
  }, []);
  return { signedIn, ready };
}

const NAV = [
  { href: "/features", label: "Возможности" },
  { href: "/pricing",  label: "Тарифы" },
  { href: "/about",    label: "О компании" },
];

export function PublicHeader() {
  const [open, setOpen] = useState(false);
  const { signedIn, ready } = useSignedInState();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 h-16 flex items-center justify-between gap-6">
        {/* Brand — our own logo */}
        <Link href="/" className="flex items-center gap-3 -ml-1 px-1 py-1 hover:opacity-80 transition-opacity text-foreground">
          <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} priority className="shrink-0" />
          <div className="hidden sm:flex flex-col leading-tight">
            <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
            <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
          </div>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-7">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {n.label}
            </Link>
          ))}
        </nav>

        {/* Right cluster — swaps Login/Demo → Dashboard when authenticated. */}
        <div className="hidden md:flex items-center gap-3">
          <ThemeToggle />
          {ready && signedIn ? (
            <Link href="/dashboard">
              <Button variant="primary" size="sm">В кабинет&nbsp;→</Button>
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="text-[13px] text-muted-foreground hover:text-foreground transition-colors"
              >
                Войти
              </Link>
              <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
                <Button variant="primary" size="sm">Демо</Button>
              </a>
            </>
          )}
        </div>

        {/* Mobile burger */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="md:hidden inline-flex items-center justify-center w-10 h-10 border border-border text-foreground"
          aria-label="Toggle menu"
        >
          <Icon icon={open ? "solar:close-circle-linear" : "solar:hamburger-menu-linear"} className="text-[20px]" />
        </button>
      </div>

      {/* Mobile drawer */}
      <div className={cn("md:hidden overflow-hidden transition-[max-height]", open ? "max-h-[500px]" : "max-h-0")}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-4 border-t border-border space-y-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              onClick={() => setOpen(false)}
              className="block px-2 py-2 text-[14px] text-foreground hover:bg-muted"
            >
              {n.label}
            </Link>
          ))}
          <div className="pt-4 mt-4 border-t border-border space-y-2">
            {ready && signedIn ? (
              <Link href="/dashboard" onClick={() => setOpen(false)}>
                <Button variant="primary" size="sm" fullWidth>В кабинет&nbsp;→</Button>
              </Link>
            ) : (
              <>
                <Link href="/login" onClick={() => setOpen(false)}>
                  <Button variant="secondary" size="sm" fullWidth>Войти</Button>
                </Link>
                <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request" onClick={() => setOpen(false)}>
                  <Button variant="primary" size="sm" fullWidth>Демо</Button>
                </a>
              </>
            )}
            <div className="pt-2 flex justify-center">
              <ThemeToggle />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
