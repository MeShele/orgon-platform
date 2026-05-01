"use client";

// MobileSidebar — slide-in drawer for authenticated nav on small screens.
// Uses the same NAV / role-filtering as the desktop AceternitySidebar.
// Toggled via the SidebarProvider's `open` state — Header.tsx already
// calls setOpen(true) from the hamburger.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/components/aceternity/sidebar";
import { useAuth } from "@/contexts/AuthContext";
import { useTranslations } from "@/hooks/useTranslations";
import { filterByRole, type SidebarRole } from "./sidebar-nav";

// Default open state per group; mirrors AceternitySidebar for consistency.
const DEFAULT_GROUP_OPEN: Record<string, boolean> = {
  workspace: true,
  organization: false,
  insights: false,
  platform: false,
  account: false,
  roadmap: false,
};
const STORAGE_KEY = "orgon.sidebar.groups.v1";

function loadGroupState(): Record<string, boolean> {
  if (typeof window === "undefined") return DEFAULT_GROUP_OPEN;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_GROUP_OPEN;
    const parsed = JSON.parse(raw) as Record<string, boolean>;
    return { ...DEFAULT_GROUP_OPEN, ...parsed };
  } catch {
    return DEFAULT_GROUP_OPEN;
  }
}

export function MobileSidebar() {
  const t = useTranslations("navigation");
  const pathname = usePathname();
  const { open, setOpen } = useSidebar();
  const { user } = useAuth();
  const reduce = useReducedMotion();

  const role = (user?.role || "viewer") as SidebarRole;
  const groups = filterByRole(role);

  // Group open state (mirrors AceternitySidebar via the same localStorage key).
  const [groupOpen, setGroupOpen] = useState<Record<string, boolean>>(DEFAULT_GROUP_OPEN);
  useEffect(() => {
    setGroupOpen(loadGroupState());
  }, []);

  const activeGroupLabel = useMemo(() => {
    for (const g of groups) {
      if (g.items.some((i) => pathname === i.href || pathname.startsWith(i.href + "/"))) {
        return g.label;
      }
    }
    return null;
  }, [groups, pathname]);

  const isGroupOpen = (label: string) =>
    label === activeGroupLabel ? true : !!groupOpen[label];

  const toggleGroup = (label: string) => {
    setGroupOpen((prev) => {
      const next = { ...prev, [label]: !isGroupOpen(label) };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // ignore — state still holds in memory
      }
      return next;
    });
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Scrim */}
          <motion.div
            key="mob-sb-scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={() => setOpen(false)}
            className="md:hidden fixed inset-0 z-40 bg-foreground/40 backdrop-blur-[2px]"
            aria-hidden
          />

          {/* Panel */}
          <motion.aside
            key="mob-sb-panel"
            initial={reduce ? { opacity: 0 } : { x: "-100%" }}
            animate={reduce ? { opacity: 1 } : { x: 0 }}
            exit={reduce ? { opacity: 0 } : { x: "-100%" }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] as const }}
            className="md:hidden fixed inset-y-0 left-0 z-50 w-[280px] bg-sidebar text-sidebar-foreground border-r border-sidebar-border flex flex-col"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
          >
            <header className="flex items-center justify-between gap-3 px-4 h-14 border-b border-sidebar-border">
              <Link href="/dashboard" onClick={() => setOpen(false)} className="flex items-center gap-3 text-foreground">
                <Image src="/orgon-icon.png" alt="" width={28} height={28} aria-hidden />
                <div className="leading-tight">
                  <div className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</div>
                  <div className="font-medium text-[14px] tracking-[0.06em]">ORGON</div>
                </div>
              </Link>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close menu"
                className="inline-flex items-center justify-center w-9 h-9 text-muted-foreground hover:text-foreground"
              >
                <Icon icon="solar:close-circle-linear" className="text-[20px]" />
              </button>
            </header>

            <nav className="flex-1 overflow-y-auto py-2">
              {groups.map((group) => {
                const opened = isGroupOpen(group.label);
                return (
                  <div key={group.label} className="px-3 pt-3 pb-1">
                    <button
                      type="button"
                      onClick={() => toggleGroup(group.label)}
                      aria-expanded={opened}
                      className={cn(
                        "w-full flex items-center justify-between px-2 pb-2",
                        "font-mono text-[10px] tracking-[0.16em] uppercase",
                        "transition-colors",
                        opened ? "text-faint" : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <span>{t(`groups.${group.label}`)}</span>
                      <Icon
                        icon="solar:alt-arrow-down-linear"
                        className={cn(
                          "text-[12px] transition-transform duration-150",
                          opened ? "rotate-0" : "-rotate-90",
                        )}
                      />
                    </button>
                    <AnimatePresence initial={false}>
                      {opened && (
                        <motion.ul
                          key={`${group.label}-items`}
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.18, ease: "easeOut" }}
                          className="flex flex-col gap-px overflow-hidden"
                        >
                          {group.items.map((item) => {
                            const isActive =
                              pathname === item.href ||
                              (item.href !== "/" && pathname.startsWith(item.href + "/"));
                            return (
                              <li key={item.href}>
                                <Link
                                  href={item.href}
                                  onClick={() => setOpen(false)}
                                  className={cn(
                                    "group flex items-center gap-3 h-10 px-2",
                                    "border-l-2 transition-all duration-150",
                                    isActive
                                      ? "border-primary bg-sidebar-accent text-foreground"
                                      : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted hover:border-strong",
                                  )}
                                >
                                  <Icon
                                    icon={isActive ? item.activeIcon : item.icon}
                                    className={cn("text-[18px] shrink-0", isActive && "text-primary")}
                                  />
                                  <span className="flex-1 min-w-0 flex items-center gap-2">
                                    <span className="text-[13px] font-medium tracking-tight truncate">
                                      {t(item.label)}
                                    </span>
                                    {item.roadmap && (
                                      <span className="ml-auto shrink-0 rounded bg-muted text-muted-foreground px-1.5 py-0.5 text-[9px] font-mono tracking-[0.08em] uppercase">
                                        {t("badges.comingSoon")}
                                      </span>
                                    )}
                                  </span>
                                </Link>
                              </li>
                            );
                          })}
                        </motion.ul>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </nav>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
