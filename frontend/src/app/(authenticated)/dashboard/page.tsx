"use client";

import useSWR from "swr";
import { useEffect } from "react";
import { useTranslations } from '@/hooks/useTranslations';
import { Header } from "@/components/layout/Header";
import { StatCards } from "@/components/dashboard/StatCards";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { TokenSummary } from "@/components/dashboard/TokenSummary";
import { CryptoRates } from "@/components/dashboard/CryptoRates";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { OnboardingTip } from "@/components/common/OnboardingTip";
import { api } from "@/lib/api";
import { useWebSocket } from "@/contexts/WebSocketContext";

export default function DashboardPage() {
  const t = useTranslations('dashboard');
  // WebSocket for real-time updates
  const { lastEvent } = useWebSocket();
  
  // Fetch Phase 2 endpoints with SWR
  const { data: stats, error: statsError, mutate: mutateStats } = useSWR(
    "/api/dashboard/stats",
    api.getDashboardStats,
    { refreshInterval: 30000 } // 30 seconds
  );

  const { data: recent, error: recentError, mutate: mutateRecent } = useSWR(
    "/api/dashboard/recent",
    () => api.getDashboardRecent(20),
    { refreshInterval: 30000 }
  );

  const { data: alerts, error: alertsError, mutate: mutateAlerts } = useSWR(
    "/api/dashboard/alerts",
    api.getDashboardAlerts,
    { refreshInterval: 60000 } // 1 minute
  );

  // Fallback to legacy endpoint for token summary
  const { data: overview } = useSWR(
    "/api/dashboard/overview",
    api.getDashboardOverview
  );

  // Auto-refresh on real-time events
  useEffect(() => {
    if (!lastEvent) return;
    
    const { type } = lastEvent;
    
    // Refresh dashboard on relevant events
    if (
      type === "transaction.created" ||
      type === "transaction.confirmed" ||
      type === "transaction.failed" ||
      type === "balance.updated" ||
      type === "wallet.created" ||
      type === "sync.completed"
    ) {
      mutateStats();
      mutateRecent();
      mutateAlerts();
    }
  }, [lastEvent, mutateStats, mutateRecent, mutateAlerts]);

  const isLoading = !stats && !statsError;
  const hasError = statsError || recentError || alertsError;

  return (
    <>
      <Header title={t('title')} />
        <OnboardingTip id="dashboard-welcome" text="Welcome to ORGON! This is your dashboard — view wallet balances, recent transactions and alerts. Start by creating a wallet in the Wallets section." icon="solar:home-smile-bold" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8">
        {hasError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400">
            Failed to load dashboard data. Please try again.
          </div>
        )}

        {isLoading && (
          <div className="flex justify-center py-12">
            <LoadingSpinner />
          </div>
        )}

        {stats && (
          <>
            {/* Statistics Cards */}
            <StatCards data={stats} />

            {/* Alerts Panel */}
            {alerts && <AlertsPanel alerts={alerts} />}

            {/* Recent Activity & Token Summary */}
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                {recent && <RecentActivity activities={recent} limit={10} />}
              </div>
              <div className="space-y-6">
                <CryptoRates />
                {overview?.token_summary && (
                  <TokenSummary
                    tokens={
                      overview.token_summary as Parameters<
                        typeof TokenSummary
                      >[0]["tokens"]
                    }
                  />
                )}
              </div>
            </div>

          </>
        )}
      </div>
    </>
  );
}
