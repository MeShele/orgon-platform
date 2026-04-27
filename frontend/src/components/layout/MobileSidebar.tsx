"use client";

// MobileSidebar — slide-in drawer for authenticated nav on small screens.
// Uses the same NAV / role-filtering as the desktop AceternitySidebar.
// Toggled via the SidebarProvider's `open` state — Header.tsx already
// calls setOpen(true) from the hamburger.

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

export function MobileSidebar() {
  const t = useTranslations("navigation");
  const pathname = usePathname();
  const { open, setOpen } = useSidebar();
  const { user } = useAuth();
  const reduce = useReducedMotion();

  const role = (user?.role || "viewer") as SidebarRole;
  const groups = filterByRole(role);

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
              {groups.map((group, gi) => (
                <div key={gi} className="px-3 pt-3 pb-1">
                  <div className="px-2 pb-2 font-mono text-[10px] tracking-[0.16em] uppercase text-faint">
                    {t(`groups.${group.label}`)}
                  </div>
                  <ul className="flex flex-col gap-px">
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
                              "border-l-2 transition-colors",
                              isActive
                                ? "border-primary bg-sidebar-accent text-foreground"
                                : "border-transparent text-muted-foreground hover:text-foreground hover:bg-sidebar-accent",
                            )}
                          >
                            <Icon
                              icon={isActive ? item.activeIcon : item.icon}
                              className={cn("text-[18px] shrink-0", isActive && "text-primary")}
                            />
                            <span className="text-[13px] font-medium tracking-tight">
                              {t(item.label)}
                            </span>
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              ))}
            </nav>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
