"use client";

import { useState } from "react";
import useSWR from "swr";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { PendingSignaturesTable } from "@/components/signatures/PendingSignaturesTable";
import { SignatureHistoryTable } from "@/components/signatures/SignatureHistoryTable";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { helpContent } from "@/lib/help-content";
import { pageLayout, buttonStyles } from "@/lib/page-layout";

export default function SignaturesPage() {
  const t = useTranslations('signatures');
  const [batchSigning, setBatchSigning] = useState(false);

  const handleBatchSign = async () => {
    if (!pending || pending.length === 0) return;
    if (!confirm(`Подписать все ${pending.length} транзакций?`)) return;
    setBatchSigning(true);
    try {
      await api.batchSign();
      setNotification({ type: "success", message: `Подписано ${pending.length} транзакций` });
      mutatePending();
      mutateHistory();
      mutateStats();
      setTimeout(() => setNotification(null), 5000);
    } catch (e: any) {
      setNotification({ type: "error", message: e.message || "Ошибка массовой подписи" });
      setTimeout(() => setNotification(null), 5000);
    } finally {
      setBatchSigning(false);
    }
  };

  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Fetch data with SWR (auto-refresh every 30 seconds)
  const {
    data: pending,
    error: pendingError,
    mutate: mutatePending,
  } = useSWR("/api/signatures/pending", api.getPendingSignaturesV2, {
    refreshInterval: 30000, // 30 seconds
  });

  const {
    data: history,
    error: historyError,
    mutate: mutateHistory,
  } = useSWR(
    "/api/signatures/history",
    () => api.getSignatureHistory(50),
    {
      refreshInterval: 60000, // 1 minute
    }
  );

  const {
    data: stats,
    error: statsError,
    mutate: mutateStats,
  } = useSWR("/api/signatures/stats", api.getSignatureStats, {
    refreshInterval: 60000, // 1 minute
  });

  const handleSign = async (txUnid: string) => {
    try {
      await api.signTransactionV2(txUnid);
      setNotification({
        type: "success",
        message: t('notifications.signed', { txId: txUnid.substring(0, 8) }),
      });
      // Refresh data
      mutatePending();
      mutateHistory();
      mutateStats();
      // Clear notification after 5 seconds
      setTimeout(() => setNotification(null), 5000);
    } catch (error) {
      setNotification({
        type: "error",
        message:
          error instanceof Error
            ? error.message
            : t('notifications.signFailed'),
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleReject = async (txUnid: string, reason: string) => {
    try {
      await api.rejectTransactionV2(txUnid, reason);
      setNotification({
        type: "success",
        message: t('notifications.rejected', { txId: txUnid.substring(0, 8) }),
      });
      // Refresh data
      mutatePending();
      mutateHistory();
      mutateStats();
      setTimeout(() => setNotification(null), 5000);
    } catch (error) {
      setNotification({
        type: "error",
        message:
          error instanceof Error
            ? error.message
            : t('notifications.rejectFailed'),
      });
      setTimeout(() => setNotification(null), 5000);
    }
  };

  const handleGetStatus = async (txUnid: string) => {
    try {
      return await api.getSignatureStatus(txUnid);
    } catch (error) {
      console.error("Failed to get signature status:", error);
      throw error;
    }
  };

  const isLoading = !pending && !pendingError;
  const hasError = pendingError || historyError || statsError;

  return (
    <>
      <Header title={t('title')} />
      <div className={pageLayout.container}>
        {/* Notification */}
        {notification && (
          <div className={notification.type === "success" ? pageLayout.success : pageLayout.error}>
            <div className="flex items-center justify-between">
              <span>{notification.message}</span>
              <button
                onClick={() => setNotification(null)}
                className="ml-4 hover:opacity-70"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Error State */}
        {hasError && (
          <div className={pageLayout.error}>
            {t('notifications.loadFailed')}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className={pageLayout.loading}>
            <LoadingSpinner />
          </div>
        )}

        {/* Statistics Cards */}
        {stats && (
          <div>
            <h2 className={`${pageLayout.header.title} text-lg mb-4 flex items-center gap-2`}>
              {t('stats.title')}
              <HelpTooltip 
                text={helpContent.signatures.statisticsPanel.text}
                example={helpContent.signatures.statisticsPanel.example}
                tips={helpContent.signatures.statisticsPanel.tips}
              />
            </h2>
            <div className={pageLayout.stats}>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('stats.pendingNow')}
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {pending?.length || 0}
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('stats.signed24h')}
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-green-600 dark:text-green-400">
                    {stats.signed_last_24h || 0}
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('stats.rejected24h')}
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-red-600 dark:text-red-400">
                    {stats.rejected_last_24h || 0}
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('stats.totalSigned')}
                  </div>
                  <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-gray-100">
                    {stats.total_signed || 0}
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}

        {/* Pending Signatures */}
        {pending && (
          <div>
            <h2 className={`${pageLayout.header.title} text-lg mb-4 flex items-center gap-2`}>
              {t('pending.title')} {t('pending.count', { count: pending.length })}
              {pending.length > 0 && (
                <button onClick={handleBatchSign} disabled={batchSigning} className={buttonStyles.primary + " ml-auto text-xs !py-1"}>
                  <Icon icon="solar:check-read-linear" />
                  {batchSigning ? "Подпись..." : "Подписать все"}
                </button>
              )}
              <HelpTooltip 
                text={helpContent.signatures.pendingList.text}
                example={helpContent.signatures.pendingList.example}
                tips={helpContent.signatures.pendingList.tips}
              />
            </h2>
            <PendingSignaturesTable
              signatures={pending}
              onSign={handleSign}
              onReject={handleReject}
              getStatus={handleGetStatus}
            />
          </div>
        )}

        {/* Signature History */}
        {history && (
          <div>
            <h2 className={`${pageLayout.header.title} text-lg mb-4 flex items-center gap-2`}>
              {t('history.title')}
              <HelpTooltip 
                text={helpContent.signatures.signatureHistory.text}
                example={helpContent.signatures.signatureHistory.example}
                tips={helpContent.signatures.signatureHistory.tips}
              />
            </h2>
            <SignatureHistoryTable history={history} />
          </div>
        )}
      </div>
    </>
  );
}
