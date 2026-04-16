"use client";

import Link from "next/link";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";

// Phase 2 stats format
type DashboardStats = {
  total_wallets: number;
  total_balance_usd: string;
  transactions_24h: number;
  pending_signatures: number;
  networks_active: number;
  cache_stats?: {
    networks_cache_hit?: number;
    stale?: boolean;
  };
  last_sync?: string;
};

export function StatCards({ data }: { data: DashboardStats }) {
  const t = useTranslations('dashboard');
  
  const stats = [
    {
      label: t('stats.wallets'),
      value: data.total_wallets,
      icon: "solar:wallet-linear",
      help: helpContent.dashboard.wallets,
      link: "/wallets",
    },
    {
      label: t('stats.transactions24h'),
      value: data.transactions_24h,
      icon: "solar:hourglass-linear",
      help: helpContent.dashboard.pendingTx,
      link: "/transactions",
    },
    {
      label: t('stats.pendingSignatures'),
      value: data.pending_signatures,
      icon: "solar:pen-linear",
      help: helpContent.dashboard.pendingSignatures,
      link: "/signatures",
      highlight: data.pending_signatures > 0,
    },
    {
      label: t('stats.networks'),
      value: data.networks_active,
      icon: "solar:layers-linear",
      help: helpContent.dashboard.tokenTypes,
      link: "/networks",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => {
        const CardWrapper = stat.link
          ? ({ children }: { children: React.ReactNode }) => (
              <Link href={stat.link!}>{children}</Link>
            )
          : ({ children }: { children: React.ReactNode }) => <>{children}</>;

        return (
          <CardWrapper key={stat.label}>
            <div
              className={`rounded-2xl border p-4 shadow-sm ${
                stat.highlight
                  ? "border-yellow-300 bg-yellow-50 dark:border-yellow-500/30 dark:bg-yellow-900/10"
                  : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900/40 dark:shadow-none"
              } ${stat.link ? "cursor-pointer" : ""}`}
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1 text-xs font-medium text-slate-500">
                  {stat.label}
                  <HelpTooltip
                    text={stat.help.text}
                    example={"example" in stat.help ? stat.help.example : undefined}
                    tips={"tips" in stat.help ? stat.help.tips : undefined}
                    diagram={"diagram" in stat.help ? stat.help.diagram : undefined}
                  />
                </span>
                <Icon
                  icon={stat.icon}
                  className={
                    stat.highlight
                      ? "text-yellow-400 dark:text-yellow-500"
                      : "text-slate-300 dark:text-slate-600"
                  }
                />
              </div>
              <div
                className={`mt-3 text-2xl font-semibold tracking-tight ${
                  stat.highlight
                    ? "text-yellow-900 dark:text-yellow-100"
                    : "text-slate-900 dark:text-white"
                }`}
              >
                {stat.value}
              </div>
            </div>
          </CardWrapper>
        );
      })}
    </div>
  );
}
