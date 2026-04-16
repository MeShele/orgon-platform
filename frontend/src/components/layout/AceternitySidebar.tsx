"use client";

import React from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { useTranslations } from '@/hooks/useTranslations';
import { Icon } from "@/lib/icons";
import {
  SidebarBody,
  SidebarLink,
  useSidebar,
} from "@/components/aceternity/sidebar";
import { ProfileCard } from "./ProfileCard";
import { useAuth } from "@/contexts/AuthContext";

const navItems = [
  // Основное
  { href: "/dashboard", label: "dashboard", icon: "solar:widget-linear", activeIcon: "solar:widget-bold", roles: ["all"] },
  { href: "/wallets", label: "wallets", icon: "solar:wallet-linear", activeIcon: "solar:wallet-bold", roles: ["all"] },
  { href: "/transactions", label: "transactions", icon: "solar:transfer-horizontal-linear", activeIcon: "solar:transfer-horizontal-bold", roles: ["all"] },
  { href: "/signatures", label: "signatures", icon: "solar:pen-linear", activeIcon: "solar:pen-bold", roles: ["admin", "signer"] },
  { href: "/scheduled", label: "scheduled", icon: "solar:calendar-linear", activeIcon: "solar:calendar-bold", roles: ["admin", "signer"] },
  { href: "/contacts", label: "contacts", icon: "solar:user-linear", activeIcon: "solar:user-bold", roles: ["admin", "signer"] },
  { href: "/fiat", label: "fiat", icon: "solar:banknote-linear", activeIcon: "solar:banknote-bold", roles: ["admin", "signer"] },
  { href: "/analytics", label: "analytics", icon: "solar:chart-linear", activeIcon: "solar:chart-bold", roles: ["all"] },
  // Управление (admin)
  { href: "/organizations", label: "organizations", icon: "solar:buildings-linear", activeIcon: "solar:buildings-bold", roles: ["admin"] },
  { href: "/partner", label: "partner", icon: "solar:hand-shake-linear", activeIcon: "solar:hand-shake-bold", roles: ["admin"] },
  { href: "/users", label: "users", icon: "solar:users-group-rounded-linear", activeIcon: "solar:users-group-rounded-bold", roles: ["admin"] },
  { href: "/networks", label: "networks", icon: "solar:global-linear", activeIcon: "solar:global-bold", roles: ["admin"] },
  { href: "/compliance", label: "compliance", icon: "solar:shield-check-linear", activeIcon: "solar:shield-check-bold", roles: ["admin"] },
  { href: "/audit", label: "audit", icon: "solar:history-linear", activeIcon: "solar:history-bold", roles: ["admin", "viewer"] },
  { href: "/reports", label: "reports", icon: "solar:document-text-linear", activeIcon: "solar:document-text-bold", roles: ["admin", "viewer"] },
  { href: "/billing", label: "billing", icon: "solar:card-linear", activeIcon: "solar:card-bold", roles: ["admin"] },
  // Прочее
  { href: "/documents", label: "documents", icon: "solar:document-linear", activeIcon: "solar:document-bold", roles: ["all"] },
  { href: "/support", label: "support", icon: "solar:chat-round-linear", activeIcon: "solar:chat-round-bold", roles: ["all"] },
  { href: "/settings", label: "settings", icon: "solar:settings-linear", activeIcon: "solar:settings-bold", roles: ["all"] },
  { href: "/help", label: "help", icon: "solar:question-circle-linear", activeIcon: "solar:question-circle-bold", roles: ["all"] },
];

export function AceternitySidebar() {
  const t = useTranslations('navigation');
  const pathname = usePathname();
  const { open, hovered } = useSidebar();
  const { user } = useAuth();
  
  const isExpanded = hovered || open;
  const userRole = user?.role || "viewer";

  const filteredItems = navItems.filter(item =>
    item.roles.includes("all") || item.roles.includes(userRole)
  );

  const links = filteredItems.map((item) => ({
    label: t(item.label),
    href: item.href,
    icon: <Icon icon={item.icon} className="text-lg" />,
    activeIcon: <Icon icon={item.activeIcon} className="text-lg" />,
  }));

  return (
    <SidebarBody className="justify-between gap-10">
        <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          <Logo />
          <div className="mt-8 flex flex-col gap-2">
            {links.map((link, idx) => {
              const isActive =
                pathname === link.href ||
                (link.href !== "/" && pathname.startsWith(link.href));
              
              return (
                <SidebarLink
                  key={idx}
                  link={link}
                  isActive={isActive}
                />
              );
            })}
          </div>
        </div>
        <div>
          <ProfileCard collapsed={!isExpanded} />
        </div>
      </SidebarBody>
  );
}

export const Logo = () => {
  const { hovered, open } = useSidebar();
  const isExpanded = hovered || open;
  
  return (
    <Link
      href="/dashboard"
      className="font-normal flex space-x-2 items-center text-sm text-black dark:text-white py-1 relative z-20"
    >
      <Image
        src="/orgon-icon.png"
        alt="ORGON"
        width={40}
        height={40}
        className="rounded-full shrink-0"
        priority
      />
      <motion.div
        initial={{ opacity: 0, width: 0 }}
        animate={{
          opacity: isExpanded ? 1 : 0,
          width: isExpanded ? "auto" : 0,
        }}
        transition={{
          duration: 0.2,
          ease: "easeInOut",
        }}
        className="flex flex-col gap-0.5 overflow-hidden"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/orgon-logo.svg"
          alt="ASYSTEM"
          className="h-3 invert dark:invert-0 whitespace-nowrap"
        />
        <span className="text-[10px] font-semibold tracking-[0.2em] text-slate-500 dark:text-slate-400 whitespace-nowrap">
          ORGON
        </span>
      </motion.div>
    </Link>
  );
};

export const LogoIcon = () => {
  return (
    <Link
      href="/dashboard"
      className="font-normal flex space-x-2 items-center text-sm text-black py-1 relative z-20"
    >
      <Image
        src="/orgon-icon.png"
        alt="ORGON"
        width={36}
        height={36}
        className="rounded-full shrink-0"
      />
    </Link>
  );
};
