"use client";

import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CopyButton } from "@/components/common/CopyButton";
import { Icon } from "@/lib/icons";
import { useTranslations } from "@/hooks/useTranslations";

interface SignatureHistoryItem {
  tx_unid: string;
  signer_address: string;
  action: "signed" | "rejected";
  reason?: string;
  signed_at: string;
}

interface Props {
  history: SignatureHistoryItem[];
  loading?: boolean;
}

export function SignatureHistoryTable({ history, loading = false }: Props) {
  const t = useTranslations('signatures.history.table');
  const tActivity = useTranslations('dashboard.activity');
  
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);

    if (diffHours < 1) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60));
      return tActivity('minutesAgo', { count: diffMinutes });
    } else if (diffHours < 24) {
      return tActivity('hoursAgo', { count: Math.floor(diffHours) });
    } else {
      const diffDays = Math.floor(diffHours / 24);
      return tActivity('daysAgo', { count: diffDays });
    }
  };

  const truncateAddress = (addr: string) => {
    if (addr.length <= 16) return addr;
    return `${addr.substring(0, 8)}...${addr.substring(addr.length - 8)}`;
  };

  if (loading) {
    return (
      <Card>
        <div className="p-6">
          <div className="flex animate-pulse space-x-4">
            <div className="flex-1 space-y-4 py-1">
              <div className="h-4 w-3/4 rounded bg-slate-200 dark:bg-slate-700"></div>
              <div className="space-y-2">
                <div className="h-4 rounded bg-slate-200 dark:bg-slate-700"></div>
                <div className="h-4 w-5/6 rounded bg-slate-200 dark:bg-slate-700"></div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  if (history.length === 0) {
    return (
      <Card>
        <div className="p-6 text-center">
          <Icon 
            icon="solar:clipboard-list-linear" 
            className="mx-auto mb-4 text-6xl text-slate-400 dark:text-slate-600"
          />
          <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100">
            {t('noHistory')}
          </h3>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
            <tr>
              <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                {t('transaction')}
              </th>
              <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                {t('signer')}
              </th>
              <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                {t('action')}
              </th>
              <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                {t('reason')}
              </th>
              <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                {t('timestamp')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {history.map((item, index) => (
              <tr
                key={`${item.tx_unid}-${index}`}
                className="hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <code className="font-mono text-xs text-slate-600 dark:text-slate-400">
                      {truncateAddress(item.tx_unid)}
                    </code>
                    <CopyButton text={item.tx_unid} />
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <code className="font-mono text-xs text-slate-600 dark:text-slate-400">
                      {truncateAddress(item.signer_address)}
                    </code>
                    <CopyButton text={item.signer_address} />
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={item.action}
                  />
                </td>
                <td className="px-4 py-3">
                  {item.reason ? (
                    <span className="text-xs text-slate-600 dark:text-slate-400">
                      {item.reason.length > 40
                        ? `${item.reason.substring(0, 40)}...`
                        : item.reason}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-400 dark:text-slate-500">
                      —
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {formatTimestamp(item.signed_at)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
