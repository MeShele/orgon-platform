"use client";

import { useState, useEffect } from "react";
import { useTranslations } from '@/hooks/useTranslations';
import { Header } from "@/components/layout/Header";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { Tooltip, HelpText } from "@/components/ui/Tooltip";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { helpContent } from "@/lib/help-content";
import { pageLayout } from "@/lib/page-layout";
import BalanceChart from "@/components/analytics/BalanceChart";
import TokenDistribution from "@/components/analytics/TokenDistribution";
import VolumeChart from "@/components/analytics/VolumeChart";
import SignatureStats from "@/components/analytics/SignatureStats";
import { HoverBorderGradient } from "@/components/aceternity/hover-border-card";
import { SkeletonCard, SkeletonTable } from "@/components/aceternity/loading-skeleton";
import { ButtonHover } from "@/components/aceternity/button-hover";

interface AnalyticsData {
  balance_history: Array<{
    date: string;
    tx_count: number;
    total_value: number;
  }>;
  token_distribution: Array<{
    token: string;
    value: number;
    percentage: number;
    tx_count: number;
  }>;
  transaction_volume: Array<{
    network_id: number;
    network_name: string;
    tx_count: number;
    total_value: number;
  }>;
  signature_stats: {
    signed: number;
    total: number;
    pending: number;
    completion_rate: number;
  };
  wallet_summary: {
    total: number;
    active: number;
    inactive: number;
  };
}

export default function AnalyticsPage() {
  const t = useTranslations('analytics');
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      
      // Load overview data
      const overview = await api.getAnalyticsOverview();
      
      // Load balance history with selected days
      const balanceHistory = await api.getBalanceHistory(days);
      
      setData({
        balance_history: balanceHistory,
        token_distribution: overview.token_distribution || [],
        transaction_volume: overview.transaction_volume || [],
        signature_stats: overview.signature_stats || {
          signed: 0,
          total: 0,
          pending: 0,
          completion_rate: 0
        },
        wallet_summary: overview.wallet_summary || {
          total: 0,
          active: 0,
          inactive: 0
        }
      });
    } catch (error) {
      console.error("Failed to load analytics:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [days]);

  if (loading) {
    return (
      <>
        <Header title={t('title')} />
        <div className={pageLayout.container}>
          {/* Days Filter Skeleton */}
          <div className="flex gap-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-10 w-16 bg-slate-700/50 rounded-lg animate-pulse" />
            ))}
          </div>

          {/* Summary Cards Skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {[1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>

          {/* Charts Skeleton */}
          <div className="space-y-6">
            <div className="h-64 bg-muted/50 rounded-2xl border border-border animate-pulse" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="h-64 bg-muted/50 rounded-2xl border border-border animate-pulse" />
              <div className="h-64 bg-muted/50 rounded-2xl border border-border animate-pulse" />
            </div>
            <div className="h-48 bg-muted/50 rounded-2xl border border-border animate-pulse" />
          </div>
        </div>
      </>
    );
  }

  if (!data) {
    return (
      <>
        <Header title={t('title')} />
        <div className={pageLayout.container}>
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-2xl border border-border">
            <div className="mb-4">
              <Icon icon="solar:danger-circle-linear" className="text-5xl text-destructive mx-auto" />
            </div>
            <p className="text-muted-foreground mb-4">{t('error')}</p>
            <ButtonHover
              onClick={loadAnalytics}
              variant="primary"
              size="md"
              icon={<Icon icon="solar:restart-linear" />}
              iconPosition="left"
            >
              {t('retry')}
            </ButtonHover>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Header title={t('title')} />
      <div className={pageLayout.container}>
        
        {/* Days Filter */}
        <div>
          <h2 className={`${pageLayout.header.title} text-lg mb-4 flex items-center gap-2`}>
            {t('filters.title')}
            <HelpTooltip 
              text={helpContent.analytics.periodFilter.text}
              example={helpContent.analytics.periodFilter.example}
              tips={helpContent.analytics.periodFilter.tips}
            />
          </h2>
          <div className="flex flex-wrap gap-2">
            {[7, 14, 30, 90].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 sm:px-4 py-2 rounded-lg font-medium transition-colors text-sm sm:text-base ${
                  days === d
                    ? "bg-blue-600 text-white dark:bg-blue-500"
                    : "bg-gray-100 text-foreground hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="bg-card rounded-2xl p-4 sm:p-6 border border-border shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                  {t('stats.totalWallets')}
                  <HelpTooltip 
                    text={helpContent.analytics.walletsCard.text}
                    example={helpContent.analytics.walletsCard.example}
                    tips={helpContent.analytics.walletsCard.tips}
                  />
                </p>
                <p className="text-2xl sm:text-3xl font-bold text-foreground">
                  {data.wallet_summary.total}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                <Icon icon="solar:wallet-linear" className="text-2xl text-primary" />
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 sm:gap-4 text-xs sm:text-sm">
              <span className="text-success">
                {t('stats.active')}: {data.wallet_summary.active}
              </span>
              <span className="text-muted-foreground">
                {t('stats.inactive')}: {data.wallet_summary.inactive}
              </span>
            </div>
          </div>

          <div className="bg-card rounded-2xl p-4 sm:p-6 border border-border shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                  {t('stats.totalSignatures')}
                  <HelpTooltip 
                    text={helpContent.analytics.signaturesCard.text}
                    example={helpContent.analytics.signaturesCard.example}
                    tips={helpContent.analytics.signaturesCard.tips}
                  />
                </p>
                <p className="text-2xl sm:text-3xl font-bold text-foreground">
                  {data.signature_stats.total}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                <Icon icon="solar:pen-linear" className="text-2xl text-success" />
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 sm:gap-4 text-xs sm:text-sm">
              <span className="text-success">
                {t('stats.signed')}: {data.signature_stats.signed}
              </span>
              <span className="text-yellow-600 dark:text-yellow-400">
                {t('stats.pending')}: {data.signature_stats.pending}
              </span>
            </div>
          </div>

          <div className="bg-card rounded-2xl p-4 sm:p-6 border border-border sm:col-span-2 lg:col-span-1 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                  {t('stats.tokenTypes')}
                  <HelpTooltip 
                    text={helpContent.analytics.tokensCard.text}
                    example={helpContent.analytics.tokensCard.example}
                    tips={helpContent.analytics.tokensCard.tips}
                  />
                </p>
                <p className="text-2xl sm:text-3xl font-bold text-foreground">
                  {data.token_distribution.length}
                </p>
              </div>
              <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center flex-shrink-0">
                <Icon icon="solar:dollar-minimalistic-linear" className="text-2xl text-purple-600 dark:text-purple-400" />
              </div>
            </div>
            <div className="mt-4 text-xs sm:text-sm text-muted-foreground">
              {t('stats.activeTokens')}
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="space-y-6">
          {/* Balance History - Full Width */}
          <HoverBorderGradient
            containerClassName="w-full"
            className="w-full p-0"
            duration={2}
            as="div"
          >
            <div className="w-full overflow-x-auto">
              <BalanceChart data={data.balance_history} days={days} />
            </div>
          </HoverBorderGradient>

          {/* Token Distribution & Volume - Side by Side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            <HoverBorderGradient
              containerClassName="w-full"
              className="w-full p-0"
              duration={2.5}
              as="div"
            >
              <div className="w-full overflow-x-auto">
                <TokenDistribution data={data.token_distribution} />
              </div>
            </HoverBorderGradient>
            <HoverBorderGradient
              containerClassName="w-full"
              className="w-full p-0"
              duration={2.5}
              clockwise={false}
              as="div"
            >
              <div className="w-full overflow-x-auto">
                <VolumeChart data={data.transaction_volume} />
              </div>
            </HoverBorderGradient>
          </div>

          {/* Signature Stats - Full Width */}
          <HoverBorderGradient
            containerClassName="w-full"
            className="w-full p-0"
            duration={2}
            as="div"
          >
            <div className="w-full overflow-x-auto">
              <SignatureStats data={data.signature_stats} />
            </div>
          </HoverBorderGradient>
        </div>

        {/* Refresh Button */}
        <div className="flex justify-center">
          <Tooltip
            content={
              <HelpText
                title={helpContent.analytics.refreshButton.text.split('.')[0]}
                description={helpContent.analytics.refreshButton.text}
                example={helpContent.analytics.refreshButton.example}
                tips={helpContent.analytics.refreshButton.tips}
              />
            }
            position="top"
            maxWidth="320px"
          >
            <ButtonHover
              onClick={loadAnalytics}
              variant="secondary"
              size="lg"
              icon={<Icon icon="solar:refresh-linear" />}
              iconPosition="left"
              className="w-full sm:w-auto"
            >
              {t('refreshButton')}
            </ButtonHover>
          </Tooltip>
        </div>
    </div>
    </>
  );
}
