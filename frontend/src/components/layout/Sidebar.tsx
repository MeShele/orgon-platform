"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import { useAuth } from "@/contexts/AuthContext";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import { ProfileCard } from "./ProfileCard";

interface NavItem {
  href: string;
  label: string;
  icon: string;
  activeIcon: string;
  roles?: string[];
}

const allNavItems: NavItem[] = [
  { href: "/dashboard", label: "dashboard", icon: "solar:widget-linear", activeIcon: "solar:widget-bold" },
  { href: "/wallets", label: "wallets", icon: "solar:wallet-linear", activeIcon: "solar:wallet-bold" },
  { href: "/transactions", label: "transactions", icon: "solar:transfer-horizontal-linear", activeIcon: "solar:transfer-horizontal-bold" },
  { href: "/scheduled", label: "scheduled", icon: "solar:calendar-linear", activeIcon: "solar:calendar-bold", roles: ["admin", "signer"] },
  { href: "/analytics", label: "analytics", icon: "solar:chart-linear", activeIcon: "solar:chart-bold", roles: ["admin"] },
  { href: "/signatures", label: "signatures", icon: "solar:pen-linear", activeIcon: "solar:pen-bold", roles: ["admin", "signer"] },
  { href: "/contacts", label: "contacts", icon: "solar:user-linear", activeIcon: "solar:user-bold", roles: ["admin", "signer"] },
  { href: "/documents", label: "documents", icon: "solar:document-linear", activeIcon: "solar:document-bold" },
  { href: "/organizations", label: "organizations", icon: "solar:buildings-linear", activeIcon: "solar:buildings-bold", roles: ["admin"] },
  { href: "/users", label: "users", icon: "solar:users-group-rounded-linear", activeIcon: "solar:users-group-rounded-bold", roles: ["admin"] },
  { href: "/audit", label: "audit", icon: "solar:history-linear", activeIcon: "solar:history-bold", roles: ["admin"] },
  { href: "/reports", label: "reports", icon: "solar:document-text-linear", activeIcon: "solar:document-text-bold", roles: ["admin"] },
  { href: "/billing", label: "billing", icon: "solar:bill-list-linear", activeIcon: "solar:bill-list-bold", roles: ["admin"] },
  { href: "/compliance", label: "compliance", icon: "solar:shield-check-linear", activeIcon: "solar:shield-check-bold", roles: ["admin", "viewer"] },
  { href: "/networks", label: "networks", icon: "solar:global-linear", activeIcon: "solar:global-bold", roles: ["admin"] },
  { href: "/support", label: "support", icon: "solar:chat-round-dots-linear", activeIcon: "solar:chat-round-dots-bold" },
  { href: "/profile", label: "profile", icon: "solar:user-circle-linear", activeIcon: "solar:user-circle-bold" },
  { href: "/settings", label: "settings", icon: "solar:settings-linear", activeIcon: "solar:settings-bold" },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useTranslations("navigation");
  const pathname = usePathname();
  const { user } = useAuth();
  const userRole = user?.role || "viewer";

  const navItems = allNavItems.filter(
    (item) => !item.roles || item.roles.includes(userRole)
  );

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950 dark:shadow-none transition-transform lg:static lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full"
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-5 py-4">
        <Link href="/dashboard" className="flex items-center gap-3">
          <Image src="/orgon-icon.png" alt="ORGON" width={36} height={36} className="rounded-full shrink-0" />
          <div className="flex flex-col gap-0.5">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/orgon-logo.svg" alt="ASYSTEM" className="h-3 invert dark:invert-0" />
            <span className="text-[10px] font-semibold tracking-[0.2em] text-slate-500 dark:text-slate-400">ORGON</span>
          </div>
        </Link>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-white lg:hidden">
          <Icon icon="solar:close-circle-linear" className="text-xl" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={cn(
                "group flex items-center gap-3 rounded-lg border px-3 py-2 text-sm font-medium transition-all",
                isActive
                  ? "border-slate-200 bg-slate-100 text-slate-900 shadow-sm dark:border-slate-800 dark:bg-slate-900/50 dark:text-white"
                  : "border-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-900 dark:hover:text-slate-200"
              )}
            >
              <Icon
                icon={isActive ? item.activeIcon : item.icon}
                className={cn(
                  "text-lg",
                  isActive
                    ? "text-indigo-600 dark:text-indigo-400"
                    : "text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300"
                )}
              />
              {t(item.label)}
            </Link>
          );
        })}
      </nav>

      {/* Profile Card */}
      <div className="border-t border-slate-200 p-4 dark:border-slate-800">
        <ProfileCard />
      </div>
    </aside>
  );
}
