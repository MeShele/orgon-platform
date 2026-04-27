"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Icon } from "@/lib/icons";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";

interface NavLink {
  href: string;
  label: string;
  external?: boolean;
}

const NAV: NavLink[] = [
  { href: "/", label: "Главная" },
  { href: "/features", label: "Возможности" },
  { href: "/pricing", label: "Тарифы" },
  { href: "https://orgon-preview-api.asystem.kg/api/redoc", label: "Документация", external: true },
  { href: "/about", label: "О компании" },
];

export function PublicHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-background/85 backdrop-blur-md border-b border-border">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10">
        <div className="flex h-16 items-center justify-between">
          {/* Brand */}
          <Link href="/" className="flex items-center gap-3 text-foreground">
            <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} className="shrink-0" priority />
            <div className="hidden sm:flex flex-col leading-tight">
              <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
              <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
            </div>
          </Link>

          {/* Desktop nav */}
          <ul className="hidden md:flex items-center gap-7">
            {NAV.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  target={link.external ? "_blank" : undefined}
                  rel={link.external ? "noopener noreferrer" : undefined}
                  className="text-[13px] font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                  {link.external && (
                    <Icon icon="solar:arrow-right-up-linear" className="inline-block ml-1 text-[12px]" />
                  )}
                </Link>
              </li>
            ))}
          </ul>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-2">
            <ThemeToggle />
            <Link href="/login">
              <Button variant="ghost" size="sm">Войти</Button>
            </Link>
            <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request">
              <Button variant="primary" size="sm">
                Запросить демо
                <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
              </Button>
            </a>
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
          <div className="py-4 border-t border-border space-y-1">
            {NAV.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                target={link.external ? "_blank" : undefined}
                rel={link.external ? "noopener noreferrer" : undefined}
                onClick={() => setOpen(false)}
                className="block px-2 py-2 text-[14px] text-foreground hover:bg-muted"
              >
                {link.label}
                {link.external && <Icon icon="solar:arrow-right-up-linear" className="inline-block ml-1 text-[12px]" />}
              </Link>
            ))}
            <div className="pt-4 mt-4 border-t border-border space-y-2">
              <Link href="/login" onClick={() => setOpen(false)}>
                <Button variant="secondary" size="sm" fullWidth>Войти</Button>
              </Link>
              <a href="mailto:sales@orgon.asystem.kg?subject=ORGON%20demo%20request" onClick={() => setOpen(false)}>
                <Button variant="primary" size="sm" fullWidth>Запросить демо</Button>
              </a>
              <div className="pt-2 flex justify-center">
                <ThemeToggle />
              </div>
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
}
