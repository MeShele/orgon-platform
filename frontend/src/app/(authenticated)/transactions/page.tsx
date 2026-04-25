"use client";
import { OnboardingTip } from "@/components/common/OnboardingTip";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { useTranslations } from '@/hooks/useTranslations';
import { Header } from "@/components/layout/Header";
import { TransactionTable } from "@/components/transactions/TransactionTable";
import { TransactionFilters } from "@/components/transactions/TransactionFilters";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Tooltip, HelpText } from "@/components/ui/Tooltip";
import { helpContent } from "@/lib/help-content";
import { Icon } from "@/lib/icons";
import { api, API_BASE } from "@/lib/api";
import { pageLayout, buttonStyles } from "@/lib/page-layout";

interface Filters {
  wallet?: string;
  status?: string;
  network?: string;
  from_date?: string;
  to_date?: string;
}

export default function TransactionsPage() {
  const t = useTranslations('transactions');
  const [filters, setFilters] = useState<Filters>({});
  const [appliedFilters, setAppliedFilters] = useState<Filters>({});
  const [exporting, setExporting] = useState(false);
  const [showBatch, setShowBatch] = useState(false);
  const [batchRows, setBatchRows] = useState([{ to_address: "", value: "", token: "" }]);
  const [batchSending, setBatchSending] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Fetch wallets and networks for filter dropdowns
  const { data: wallets } = useSWR("/api/wallets", api.getWallets);
  const { data: networks } = useSWR("/api/networks", api.getNetworks);

  // Fetch transactions with applied filters
  const {
    data: transactions,
    error,
    isLoading,
  } = useSWR(
    ["/api/transactions/filtered", appliedFilters],
    () =>
      api.getTransactionsFiltered({
        limit: 100,
        offset: 0,
        ...appliedFilters,
      }),
    {
      refreshInterval: 30000, // 30 seconds
    }
  );

  const handleFilterChange = (newFilters: Filters) => {
    setAppliedFilters(newFilters);
  };

  const addBatchRow = () => setBatchRows([...batchRows, { to_address: "", value: "", token: "" }]);
  const removeBatchRow = (i: number) => setBatchRows(batchRows.filter((_, idx) => idx !== i));
  const updateBatchRow = (i: number, field: string, val: string) => {
    const rows = [...batchRows];
    (rows[i] as any)[field] = val;
    setBatchRows(rows);
  };

  const handleBatchSend = async () => {
    const valid = batchRows.filter((r) => r.to_address && r.value && r.token);
    if (valid.length === 0) return;
    setBatchSending(true);
    try {
      await api.batchSend({ transactions: valid });
      setNotification({ type: "success", message: `Отправлено ${valid.length} транзакций` });
      setShowBatch(false);
      setBatchRows([{ to_address: "", value: "", token: "" }]);
      setTimeout(() => setNotification(null), 5000);
    } catch (e: any) {
      setNotification({ type: "error", message: e.message || "Ошибка пакетной отправки" });
      setTimeout(() => setNotification(null), 5000);
    } finally {
      setBatchSending(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      // Build query params
      const params = new URLSearchParams();
      if (appliedFilters.wallet) params.append("wallet", appliedFilters.wallet);
      if (appliedFilters.status) params.append("status", appliedFilters.status);
      if (appliedFilters.network) params.append("network", appliedFilters.network);
      if (appliedFilters.from_date) params.append("from_date", appliedFilters.from_date);
      if (appliedFilters.to_date) params.append("to_date", appliedFilters.to_date);

      // Download CSV
      const url = `${API_BASE}/export/transactions/csv?${params.toString()}`;
      window.open(url, "_blank");
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <Header title={t('title')} />
      <div className={pageLayout.container}>
        {/* Filters */}
        {wallets && networks && (
          <TransactionFilters
            onFilterChange={handleFilterChange}
            wallets={wallets}
            networks={networks}
          />
        )}

        {notification && (
          <div className={notification.type === "success" ? pageLayout.success : pageLayout.error}>
            {notification.message}
          </div>
        )}

        {/* Transaction Count & Export */}
        <div className={pageLayout.actionBar}>
          <p className={pageLayout.header.subtitle}>
            {t('count', { count: transactions?.length || 0 })}
            {Object.keys(appliedFilters).length > 0 && ` ${t('filtered')}`}
          </p>
          <button onClick={() => setShowBatch(true)} className={buttonStyles.primary}>
            <Icon icon="solar:layers-linear" />
            Пакетная отправка
          </button>
          <Tooltip
            content={
              <HelpText
                title={helpContent.transactionTable.exportButton.text.split('.')[0]}
                description={helpContent.transactionTable.exportButton.text}
                example={helpContent.transactionTable.exportButton.example}
                tips={helpContent.transactionTable.exportButton.tips}
              />
            }
            position="bottom"
            maxWidth="320px"
          >
            <button
              onClick={handleExport}
              disabled={exporting || !transactions || transactions.length === 0}
              className={buttonStyles.secondary}
            >
              <Icon 
                icon={exporting ? "solar:loader-linear" : "solar:download-linear"} 
                className={exporting ? "animate-spin" : ""} 
              />
              {exporting ? t('exporting') : t('exportButton')}
            </button>
          </Tooltip>
        </div>

        {/* Error State */}
        {error && (
          <div className={pageLayout.error}>
            {error.message || t('failedToLoad')}
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className={pageLayout.loading}>
            <LoadingSpinner />
          </div>
        )}

        {/* Transactions Table */}
        {transactions && (
          <TransactionTable
            transactions={transactions as Parameters<typeof TransactionTable>[0]["transactions"]}
          />
        )}
      </div>

      {/* Batch Modal */}
      {showBatch && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900 max-h-[80vh] overflow-y-auto">
            <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4">Пакетная отправка</h2>
            <div className="space-y-3">
              {batchRows.map((row, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <input
                    placeholder="Адрес"
                    value={row.to_address}
                    onChange={(e) => updateBatchRow(i, "to_address", e.target.value)}
                    className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                  />
                  <input
                    placeholder="Сумма"
                    value={row.value}
                    onChange={(e) => updateBatchRow(i, "value", e.target.value)}
                    className="w-28 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                  />
                  <input
                    placeholder="Токен"
                    value={row.token}
                    onChange={(e) => updateBatchRow(i, "token", e.target.value)}
                    className="w-24 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-white"
                  />
                  {batchRows.length > 1 && (
                    <button onClick={() => removeBatchRow(i)} className="text-red-500 hover:text-red-700">
                      <Icon icon="solar:close-circle-linear" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button onClick={addBatchRow} className={buttonStyles.ghost + " mt-3 text-xs"}>
              <Icon icon="solar:add-circle-linear" /> Добавить получателя
            </button>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowBatch(false)} className={buttonStyles.secondary}>Отмена</button>
              <button onClick={handleBatchSend} disabled={batchSending} className={buttonStyles.primary}>
                {batchSending ? "Отправка..." : `Отправить (${batchRows.filter(r => r.to_address && r.value && r.token).length})`}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
