"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import { useTranslations } from '@/hooks/useTranslations';
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { Tooltip, HelpText } from "@/components/ui/Tooltip";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { helpContent } from "@/lib/help-content";
import { pageLayout } from "@/lib/page-layout";

interface ScheduledTransaction {
  id: number;
  token: string;
  to_address: string;
  value: string;
  scheduled_at: string;
  recurrence_rule?: string;
  info?: string;
  status: "pending" | "sent" | "failed" | "cancelled";
  created_at: string;
  sent_at?: string;
  tx_unid?: string;
  error_message?: string;
  next_run_at?: string;
}

export default function ScheduledPage() {
  const t = useTranslations('scheduled');
  const [transactions, setTransactions] = useState<ScheduledTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("pending");

  const loadTransactions = async () => {
    try {
      setLoading(true);
      const data = await api.getScheduledTransactions({ status: filter });
      setTransactions(data.transactions || data || []);
    } catch (error) {
      console.error("Failed to load scheduled transactions:", error);
      setTransactions([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, [filter]);

  const handleCancel = async (id: number) => {
    if (!confirm(t('actions.cancelConfirm'))) return;

    try {
      await api.deleteScheduledTransaction(id);
      await loadTransactions();
    } catch (error) {
      console.error("Failed to cancel transaction:", error);
      alert(t('actions.cancelFailed'));
    }
  };

  const getStatusVariant = (status: string): "primary" | "success" | "danger" | "gray" => {
    switch (status) {
      case "pending": return "primary";
      case "sent": return "success";
      case "failed": return "danger";
      default: return "gray";
    }
  };

  return (
    <>
      <Header title={t('title')} />
      
      <div className={pageLayout.container}>
        {/* Filters */}
        <div>
          <h2 className={`${pageLayout.header.title} text-lg mb-4 flex items-center gap-2`}>
            {t('filters.title')}
            <HelpTooltip 
              text={helpContent.scheduled.statusFilters.text}
              example={helpContent.scheduled.statusFilters.example}
              tips={helpContent.scheduled.statusFilters.tips}
            />
          </h2>
          <div className="flex gap-3 flex-wrap">
            {["pending", "sent", "failed", "cancelled"].map((status) => (
              <Button
                key={status}
                variant={filter === status ? "primary" : "ghost"}
                onClick={() => setFilter(status)}
              >
                {t(`filters.${status}`)}
              </Button>
            ))}
          </div>
        </div>

        {/* Transactions List */}
        {loading ? (
          <div className={pageLayout.loading}>
            <LoadingSpinner />
          </div>
        ) : transactions.length === 0 ? (
          <Card padding className={pageLayout.empty.wrapper}>
            <Icon 
              icon="solar:calendar-linear" 
              className={pageLayout.empty.icon} 
            />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              {t('noTransactions')}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t(`filters.${filter}`)} {t('noTransactions').toLowerCase()}
            </p>
          </Card>
        ) : (
          <div className="grid gap-4">
            {transactions.map((tx) => (
              <Card key={tx.id} hover padding className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                        {tx.value} {tx.token}
                      </h3>
                      <Badge variant={getStatusVariant(tx.status)}>
                        {t(`status.${tx.status}`)}
                      </Badge>
                    </div>
                    
                    {tx.info && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {tx.info}
                      </p>
                    )}
                  </div>

                  {tx.status === "pending" && (
                    <Tooltip
                      content={
                        <HelpText
                          title={helpContent.scheduled.cancelButton.text.split('.')[0]}
                          description={helpContent.scheduled.cancelButton.text}
                          example={helpContent.scheduled.cancelButton.example}
                          tips={helpContent.scheduled.cancelButton.tips}
                        />
                      }
                      position="left"
                      maxWidth="320px"
                    >
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleCancel(tx.id)}
                      >
                        {t('actions.cancel')}
                      </Button>
                    </Tooltip>
                  )}
                </div>

                {/* Details Grid */}
                <div className="grid md:grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                  {/* To Address */}
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                      {t('fields.recipient')}
                    </p>
                    <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-2 py-1 rounded block truncate font-mono">
                      {tx.to_address}
                    </code>
                  </div>

                  {/* Scheduled Time */}
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
                      {t('fields.scheduledAt')}
                      <HelpTooltip 
                        text={helpContent.scheduled.scheduledAt.text}
                        example={helpContent.scheduled.scheduledAt.example}
                        tips={helpContent.scheduled.scheduledAt.tips}
                      />
                    </p>
                    <p className="text-sm text-gray-900 dark:text-gray-100">
                      {format(new Date(tx.scheduled_at), "PPpp")}
                    </p>
                  </div>

                  {/* Recurrence */}
                  {tx.recurrence_rule && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
                        {t('fields.recurrence')}
                        <HelpTooltip 
                          text={helpContent.scheduled.recurrence.text}
                          example={helpContent.scheduled.recurrence.example}
                          tips={helpContent.scheduled.recurrence.tips}
                        />
                      </p>
                      <Badge variant="warning">
                        {tx.recurrence_rule}
                      </Badge>
                    </div>
                  )}

                  {/* Next Run */}
                  {tx.next_run_at && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1 flex items-center gap-1">
                        {t('fields.nextRun')}
                        <HelpTooltip 
                          text={helpContent.scheduled.nextRun.text}
                          example={helpContent.scheduled.nextRun.example}
                          tips={helpContent.scheduled.nextRun.tips}
                        />
                      </p>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {format(new Date(tx.next_run_at), "PPpp")}
                      </p>
                    </div>
                  )}

                  {/* Sent At */}
                  {tx.sent_at && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                        {t('fields.sentAt')}
                      </p>
                      <p className="text-sm text-gray-900 dark:text-gray-100">
                        {format(new Date(tx.sent_at), "PPpp")}
                      </p>
                    </div>
                  )}

                  {/* Transaction ID */}
                  {tx.tx_unid && (
                    <div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                        {t('fields.transactionId')}
                      </p>
                      <code className="text-sm bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 px-2 py-1 rounded block truncate font-mono">
                        {tx.tx_unid}
                      </code>
                    </div>
                  )}

                  {/* Error Message */}
                  {tx.error_message && (
                    <div className="md:col-span-2">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                        {t('fields.error')}
                      </p>
                      <p className="text-sm text-red-600 dark:text-red-400">
                        {tx.error_message}
                      </p>
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
