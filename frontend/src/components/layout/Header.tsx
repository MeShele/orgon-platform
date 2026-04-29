"use client";

import Link from "next/link";
import { useWebSocket } from "@/contexts/WebSocketContext";
import { Icon } from "@/lib/icons";
import { useSidebar } from "@/components/aceternity/sidebar";
import { OrganizationSwitcher } from "@/components/organizations/OrganizationSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

export function Header({ title }: { title: string }) {
  const { connected } = useWebSocket();
  const { setOpen } = useSidebar();
  const { user } = useAuth();

  const initials = (user?.full_name || user?.email || "··")
    .split(/[\s@]/)[0]
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 h-14 sm:h-16 bg-background/90 backdrop-blur-md border-b border-border">
      <div className="h-full flex items-center justify-between px-3 sm:px-6">
        {/* Left cluster */}
        <div className="flex items-center gap-3 sm:gap-5 min-w-0">
          <button
            onClick={() => setOpen(true)}
            className="md:hidden inline-flex items-center justify-center w-9 h-9 border border-border text-foreground"
            aria-label="Open menu"
          >
            <Icon icon="solar:hamburger-menu-linear" className="text-[18px]" />
          </button>

          <div className="flex flex-col min-w-0">
            <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint hidden sm:block">
              ORGON / {title}
            </div>
            <h1 className="text-[15px] font-medium tracking-tight text-foreground truncate">{title}</h1>
          </div>

          <div className="hidden md:block h-6 w-px bg-border" />

          <div className="hidden md:block">
            <OrganizationSwitcher />
          </div>

          {/* Connection status */}
          <div
            className={cn(
              "hidden lg:inline-flex items-center gap-2 px-2.5 py-1 border font-mono text-[10px] tracking-[0.08em] uppercase",
              connected
                ? "border-success/40 text-success bg-success/5"
                : "border-border text-faint",
            )}
          >
            <span className={cn("relative flex h-1.5 w-1.5", connected && "")}>
              {connected && (
                <span className="absolute inline-flex h-full w-full rounded-full bg-success opacity-50 animate-ping" />
              )}
              <span className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", connected ? "bg-success" : "bg-faint")} />
            </span>
            {connected ? "Sync · Live" : "Offline"}
          </div>
        </div>

        {/* Right cluster */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Search ⌘K placeholder (functional later) */}
          <div className="hidden lg:flex items-center gap-2 h-9 px-3 border border-border text-faint min-w-[220px]">
            <Icon icon="solar:magnifer-linear" className="text-[14px]" />
            <span className="text-[12px]">Поиск</span>
            <span className="ml-auto font-mono text-[10px] tracking-tight">⌘K</span>
          </div>

          {/* Exit back to public landing — explicit way out of the dashboard. */}
          <Link
            href="/"
            title="На главную страницу"
            className={cn(
              "inline-flex items-center justify-center w-9 h-9 border border-border",
              "text-muted-foreground",
              "hover:text-foreground hover:bg-muted hover:border-strong",
              "active:scale-95",
              "transition-all duration-150",
            )}
            aria-label="На главную страницу"
          >
            <Icon icon="solar:home-2-linear" className="text-[16px]" />
          </Link>

          <ThemeToggle />

          {/* Avatar — links to /profile with explicit hover. */}
          <Link
            href="/profile"
            title={user?.full_name || user?.email || "Профиль"}
            className={cn(
              "inline-flex items-center justify-center w-9 h-9",
              "bg-primary text-primary-foreground font-mono text-[11px] font-semibold",
              "ring-0 ring-offset-2 ring-offset-background",
              "hover:ring-2 hover:ring-primary/40",
              "active:scale-95",
              "transition-all duration-150",
            )}
            aria-label="Профиль"
          >
            {initials}
          </Link>
        </div>
      </div>
    </header>
  );
}
