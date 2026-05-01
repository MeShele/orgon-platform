"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useTranslations } from "@/hooks/useTranslations";
import { Icon } from "@/lib/icons";
import { useSidebar } from "@/components/aceternity/sidebar";
import { useAuth } from "@/contexts/AuthContext";
import { ProfileCard } from "./ProfileCard";
import { filterByRole, type SidebarRole } from "./sidebar-nav";

const COLLAPSED_W = 64;
const EXPANDED_W = 240;

// Default open state per group (workspace stays open; rest start collapsed
// so the sidebar feels lighter on first visit).
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
    // Merge with defaults so newly-added groups inherit the default state
    // rather than disappear because they weren't in the saved snapshot.
    return { ...DEFAULT_GROUP_OPEN, ...parsed };
  } catch {
    return DEFAULT_GROUP_OPEN;
  }
}

export function AceternitySidebar() {
  const t = useTranslations("navigation");
  const pathname = usePathname();
  const { open, hovered, setHovered } = useSidebar();
  const { user } = useAuth();

  const isExpanded = hovered || open;
  const userRole = (user?.role || "viewer") as SidebarRole;

  const groups = useMemo(() => filterByRole(userRole), [userRole]);

  // Group open/closed state. Hydrate from localStorage on mount; persist on change.
  const [groupOpen, setGroupOpen] = useState<Record<string, boolean>>(DEFAULT_GROUP_OPEN);
  useEffect(() => {
    setGroupOpen(loadGroupState());
  }, []);

  // Auto-open the group containing the active route — so deep links never
  // land in a "where am I?" collapsed state. We DON'T persist this auto-open;
  // it only applies for the current navigation. If the user closes the
  // group manually after, that wins on next click.
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
        // localStorage disabled / quota — silently ignore, state still holds in memory.
      }
      return next;
    });
  };

  return (
    <motion.aside
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      animate={{ width: isExpanded ? EXPANDED_W : COLLAPSED_W }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className="hidden md:flex shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-sidebar-border"
    >
      <SidebarLogo isExpanded={isExpanded} />

      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-2">
        {groups.map((group) => {
          const opened = isGroupOpen(group.label);
          // In collapsed-icons mode (sidebar not expanded), always show all
          // items — there's no group header to click on, so hiding items
          // would orphan them.
          const showItems = !isExpanded || opened;
          return (
            <div key={group.label} className="px-3 pt-3 pb-1">
              {isExpanded && (
                <button
                  type="button"
                  onClick={() => toggleGroup(group.label)}
                  aria-expanded={opened}
                  className={cn(
                    "w-full flex items-center justify-between px-2 pb-2 -mt-0.5",
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
              )}
              <AnimatePresence initial={false}>
                {showItems && (
                  <motion.ul
                    key={`${group.label}-items`}
                    initial={isExpanded ? { height: 0, opacity: 0 } : false}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={isExpanded ? { height: 0, opacity: 0 } : undefined}
                    transition={{ duration: 0.18, ease: "easeOut" }}
                    className="flex flex-col gap-px overflow-hidden"
                  >
                    {group.items.map((item) => {
                      const isActive =
                        pathname === item.href ||
                        (item.href !== "/" && pathname.startsWith(item.href + "/")) ||
                        (item.href !== "/" && pathname === item.href);
                      return (
                        <li key={item.href}>
                          <Link
                            href={item.href}
                            title={!isExpanded ? t(item.label) : undefined}
                            className={cn(
                              "group flex items-center gap-3 h-9 px-2",
                              "border-l-2 transition-all duration-150",
                              isActive
                                ? "border-primary bg-sidebar-accent text-foreground"
                                : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted hover:border-strong",
                            )}
                          >
                            <Icon
                              icon={isActive ? item.activeIcon : item.icon}
                              className={cn(
                                "text-[18px] shrink-0 transition-colors",
                                isActive ? "text-primary" : "group-hover:text-foreground",
                              )}
                            />
                            {isExpanded && (
                              <span className="flex-1 min-w-0 flex items-center gap-2">
                                <span className="text-[13px] font-medium tracking-tight whitespace-nowrap overflow-hidden truncate">
                                  {t(item.label)}
                                </span>
                                {item.roadmap && (
                                  <span className="ml-auto shrink-0 rounded bg-muted text-muted-foreground px-1.5 py-0.5 text-[9px] font-mono tracking-[0.08em] uppercase">
                                    {t("badges.comingSoon")}
                                  </span>
                                )}
                              </span>
                            )}
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

      <div className="border-t border-sidebar-border">
        <ProfileCard collapsed={!isExpanded} />
      </div>
    </motion.aside>
  );
}

function SidebarLogo({ isExpanded }: { isExpanded: boolean }) {
  return (
    <Link
      href="/"
      title="На главную страницу"
      className="flex items-center gap-3 px-4 h-16 border-b border-sidebar-border text-foreground hover:bg-muted transition-colors"
    >
      <Image
        src="/orgon-icon.png"
        alt="ORGON"
        width={32}
        height={32}
        className="shrink-0"
        priority
      />
      <motion.div
        initial={false}
        animate={{ opacity: isExpanded ? 1 : 0, width: isExpanded ? "auto" : 0 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
        className="overflow-hidden whitespace-nowrap"
      >
        <div className="font-mono text-[10px] tracking-[0.18em] text-faint leading-tight">ASYSTEM</div>
        <div className="font-medium text-[14px] tracking-[0.06em] leading-tight">ORGON</div>
      </motion.div>
    </Link>
  );
}

export { SidebarLogo };
