// Single source of truth for the authenticated sidebar navigation.
// Used by both AceternitySidebar (desktop) and MobileSidebar (drawer).

export type SidebarRole = "all" | "admin" | "signer" | "viewer";

export interface SidebarItem {
  href: string;
  /** i18n key under `navigation.*` namespace */
  label: string;
  icon: string;
  activeIcon: string;
  roles: SidebarRole[];
  /** When true, item renders with a "Скоро" badge — feature is scaffolded
   *  but not yet a real flow. Visible in the sidebar so the customer sees
   *  product breadth, but signposted as coming. */
  roadmap?: boolean;
}

export interface SidebarGroup {
  /** i18n key under `navigation.groups.*`; falls back to literal */
  label: string;
  items: SidebarItem[];
}

export const SIDEBAR_NAV: SidebarGroup[] = [
  {
    label: "workspace",
    items: [
      { href: "/dashboard",    label: "dashboard",    icon: "solar:widget-linear",                  activeIcon: "solar:widget-bold",                  roles: ["all"] },
      { href: "/wallets",      label: "wallets",      icon: "solar:wallet-linear",                  activeIcon: "solar:wallet-bold",                  roles: ["all"] },
      { href: "/transactions", label: "transactions", icon: "solar:transfer-horizontal-linear",     activeIcon: "solar:transfer-horizontal-bold",     roles: ["all"] },
      { href: "/signatures",   label: "signatures",   icon: "solar:pen-linear",                     activeIcon: "solar:pen-bold",                     roles: ["admin", "signer"] },
      { href: "/scheduled",    label: "scheduled",    icon: "solar:calendar-linear",                activeIcon: "solar:calendar-bold",                roles: ["admin", "signer"] },
      { href: "/contacts",     label: "contacts",     icon: "solar:user-linear",                    activeIcon: "solar:user-bold",                    roles: ["admin", "signer"] },
      { href: "/fiat",         label: "fiat",         icon: "solar:banknote-linear",                activeIcon: "solar:banknote-bold",                roles: ["admin", "signer"] },
    ],
  },
  {
    label: "organization",
    items: [
      { href: "/organizations", label: "organizations", icon: "solar:buildings-linear",     activeIcon: "solar:buildings-bold",     roles: ["all"] },
      { href: "/partner",       label: "partner",       icon: "solar:hand-shake-linear",    activeIcon: "solar:hand-shake-bold",    roles: ["admin"] },
      { href: "/billing",       label: "billing",       icon: "solar:card-linear",          activeIcon: "solar:card-bold",          roles: ["admin"] },
    ],
  },
  {
    label: "insights",
    items: [
      { href: "/analytics", label: "analytics", icon: "solar:chart-linear",         activeIcon: "solar:chart-bold",         roles: ["all"] },
      { href: "/audit",     label: "audit",     icon: "solar:history-linear",       activeIcon: "solar:history-bold",       roles: ["admin", "viewer"] },
      { href: "/reports",   label: "reports",   icon: "solar:document-text-linear", activeIcon: "solar:document-text-bold", roles: ["admin", "viewer"] },
    ],
  },
  {
    label: "platform",
    items: [
      { href: "/networks",                label: "networks",  icon: "solar:global-linear",              activeIcon: "solar:global-bold",              roles: ["admin"] },
      { href: "/settings/keys",           label: "apiKeys",   icon: "solar:key-linear",                 activeIcon: "solar:key-bold",                 roles: ["admin"] },
      { href: "/settings/webhooks",       label: "webhooks",  icon: "solar:bolt-linear",                activeIcon: "solar:bolt-bold",                roles: ["admin"] },
      { href: "/settings/system",         label: "system",    icon: "solar:server-linear",              activeIcon: "solar:server-bold",              roles: ["admin"] },
    ],
  },
  {
    label: "account",
    items: [
      { href: "/profile",  label: "profile",  icon: "solar:user-id-linear",          activeIcon: "solar:user-id-bold",          roles: ["all"] },
      { href: "/support",  label: "support",  icon: "solar:chat-round-linear",       activeIcon: "solar:chat-round-bold",       roles: ["all"] },
      { href: "/help",     label: "help",     icon: "solar:question-circle-linear",  activeIcon: "solar:question-circle-bold",  roles: ["all"] },
    ],
  },
  // Roadmap = pages whose UI is scaffolded but the underlying flow is not
  // yet a real product feature. Kept visible so a demo viewer sees breadth,
  // but signposted with a "Скоро" badge so they don't click expecting prod.
  // Routes themselves still resolve — the existing pages render their own
  // honest "in development" banners.
  {
    label: "roadmap",
    items: [
      { href: "/compliance", label: "compliance", icon: "solar:shield-check-linear",        activeIcon: "solar:shield-check-bold",        roles: ["admin"],          roadmap: true },
      { href: "/users",      label: "users",      icon: "solar:users-group-rounded-linear", activeIcon: "solar:users-group-rounded-bold", roles: ["admin"],          roadmap: true },
      { href: "/documents",  label: "documents",  icon: "solar:document-linear",            activeIcon: "solar:document-bold",            roles: ["all"],            roadmap: true },
      { href: "/settings",   label: "settings",   icon: "solar:settings-linear",            activeIcon: "solar:settings-bold",            roles: ["all"],            roadmap: true },
    ],
  },
];

export function filterByRole(role: SidebarRole, groups = SIDEBAR_NAV): SidebarGroup[] {
  return groups
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => i.roles.includes("all") || i.roles.includes(role)),
    }))
    .filter((g) => g.items.length > 0);
}
