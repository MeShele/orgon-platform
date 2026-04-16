"use client";

import { useWebSocket } from "@/contexts/WebSocketContext";
import { cn } from "@/lib/utils";
import { Icon } from "@/lib/icons";
import { useSidebar } from "@/components/aceternity/sidebar";
import { OrganizationSwitcher } from "@/components/organizations/OrganizationSwitcher";

export function Header({ title }: { title: string }) {
  const { connected } = useWebSocket();
  const { setOpen } = useSidebar();

  return (
    <header className="sticky top-0 z-30 flex h-14 sm:h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-2 sm:px-4 md:px-6 lg:px-8 shadow-sm backdrop-blur-md dark:border-slate-800 dark:bg-slate-950/80 dark:shadow-none transition-colors">
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Mobile menu button */}
        <button
          onClick={() => setOpen(true)}
          className="lg:hidden rounded-lg p-1.5 text-slate-800 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800 transition-colors"
          aria-label="Open menu"
        >
          <Icon icon="solar:hamburger-menu-linear" className="text-xl sm:text-2xl" />
        </button>
        
        <h1 className="text-sm font-semibold text-slate-900 dark:text-white lg:text-base">{title}</h1>

        <div className="hidden h-4 w-px bg-slate-200 dark:bg-slate-800 sm:block" />

        {/* Organization Switcher */}
        <OrganizationSwitcher />

        <div className="hidden h-4 w-px bg-slate-200 dark:bg-slate-800 sm:block" />

        {/* Sync status */}
        <div className={cn(
          "hidden items-center gap-2 rounded-full border px-2.5 py-0.5 text-xs font-medium sm:flex",
          connected
            ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
            : "border-slate-300/20 bg-slate-100 text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
        )}>
          <span className="relative flex h-1.5 w-1.5">
            {connected && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
            <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${connected ? "bg-emerald-500" : "bg-slate-400"}`} />
          </span>
          {connected ? "Sync Live" : "Offline"}
        </div>
      </div>

      {/* Empty right section - all controls moved to ProfileCard in Sidebar */}
      <div />
    </header>
  );
}
