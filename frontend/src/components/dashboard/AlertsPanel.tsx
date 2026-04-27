"use client";

import Link from "next/link";
import { Card } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";
import { usePluralize } from "@/hooks/usePluralize";
import { useLanguage } from "@/contexts/LanguageContext";

interface Alert {
  type: "pending_signature" | "failed_transaction" | "cache_warning" | "sync_issue";
  message: string;
  count?: number;
  link?: string;
  severity: "info" | "warning" | "error";
}

interface AlertsData {
  pending_signatures: number;
  pending_signatures_list: Array<{
    tx_unid: string;
    token: string;
    value: string;
    age_hours: number;
  }>;
  failed_transactions: number;
  failed_transactions_list: Array<{
    unid: string;
    status: string;
  }>;
  low_balances: unknown[];
  sync_issues: Array<{
    type: string;
    message: string;
  }>;
  cache_warnings: Array<{
    type: string;
    message: string;
    cache: string;
  }>;
}

interface Props {
  alerts: AlertsData;
}

export function AlertsPanel({ alerts }: Props) {
  const t = useTranslations('dashboard');
  const { pluralCount } = usePluralize();
  const allAlerts: Alert[] = [];

  // Pending signatures
  if (alerts.pending_signatures > 0) {
    const count = alerts.pending_signatures;
    allAlerts.push({
      type: "pending_signature",
      message: `${pluralCount(count, 'signatures')} ожидают вашей подписи`,
      count: count,
      link: "/signatures",
      severity: count >= 5 ? "error" : "warning",
    });
  }

  // Failed transactions
  if (alerts.failed_transactions > 0) {
    const count = alerts.failed_transactions;
    allAlerts.push({
      type: "failed_transaction",
      message: `${pluralCount(count, 'transactions')} неудачных за последние 7 дней`,
      count: count,
      link: "/transactions",
      severity: "error",
    });
  }

  // Cache warnings
  if (alerts.cache_warnings.length > 0) {
    alerts.cache_warnings.forEach((warning) => {
      allAlerts.push({
        type: "cache_warning",
        message: warning.message,
        severity: "warning",
      });
    });
  }

  // Sync issues
  if (alerts.sync_issues.length > 0) {
    alerts.sync_issues.forEach((issue) => {
      allAlerts.push({
        type: "sync_issue",
        message: issue.message,
        severity: "error",
      });
    });
  }

  // No alerts - show success state
  if (allAlerts.length === 0) {
    return (
      <Card>
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/20">
              <svg
                className="h-6 w-6 text-success"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-medium text-foreground">
                {t('alerts.allOperational')}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {t('alerts.noAlerts')}
              </p>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "error":
        return "solar:close-circle-bold";
      case "warning":
        return "solar:danger-triangle-bold";
      case "info":
        return "solar:info-circle-bold";
      default:
        return "solar:info-circle-bold";
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "error":
        return "text-destructive bg-destructive/10 border-destructive/40";
      case "warning":
        return "text-yellow-600 dark:text-yellow-400 bg-warning/10 border-warning/40";
      case "info":
        return "text-primary bg-primary/10 border-primary/40";
      default:
        return "text-muted-foreground bg-muted/20 border-border dark:border-gray-500/20";
    }
  };

  return (
    <Card>
      <div className="p-6">
        <h3 className="mb-4 text-lg font-semibold text-foreground flex items-center gap-2">
          {t('alerts.title')}
          <HelpTooltip
            text={helpContent.dashboard.alerts.text}
            example={helpContent.dashboard.alerts.example}
            tips={helpContent.dashboard.alerts.tips}
          />
        </h3>
        <div className="space-y-3">
          {allAlerts.map((alert, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 rounded-lg border p-3 ${getSeverityColor(
                alert.severity
              )}`}
            >
              <Icon 
                icon={getSeverityIcon(alert.severity)} 
                className="text-xl flex-shrink-0 mt-0.5"
              />
              <div className="flex-1">
                <p className="text-sm font-medium">{alert.message}</p>
                {alert.link && (
                  <Link
                    href={alert.link}
                    className="mt-1 inline-block text-xs font-medium hover:underline"
                  >
                    {t('alerts.viewDetails')}
                  </Link>
                )}
              </div>
              {alert.count !== undefined && (
                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white/50 dark:bg-black/20">
                  <span className="text-xs font-bold">{alert.count}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}
