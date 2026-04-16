"use client";

import Link from "next/link";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CopyButton } from "@/components/common/CopyButton";
import { shortenAddress, formatValue, formatTimestamp } from "@/lib/utils";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";

type Transaction = {
  unid: string;
  to_addr: string;
  value: string;
  token_name?: string;
  token?: string;
  status: string;
  init_ts: number;
  tx_hash?: string;
  wallet_name?: string;
};

export function TransactionTable({ transactions }: { transactions: Transaction[] }) {
  const t = useTranslations('transactions.table');
  
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/40 dark:shadow-none">
      <div className="overflow-x-auto"><table className="min-w-full text-left text-xs">
        <thead className="text-slate-500 dark:text-slate-400">
          <tr className="border-b border-slate-100 dark:border-slate-800">
            <th className="whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('unid')} 
                <HelpTooltip 
                  text={helpContent.transactionTable.unid.text}
                  example={helpContent.transactionTable.unid.example}
                  tips={helpContent.transactionTable.unid.tips}
                />
              </span>
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('to')} 
                <HelpTooltip 
                  text={helpContent.transactionTable.recipient.text}
                  example={helpContent.transactionTable.recipient.example}
                  tips={helpContent.transactionTable.recipient.tips}
                />
              </span>
            </th>
            <th className="hidden md:table-cell whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('amount')} 
                <HelpTooltip 
                  text={helpContent.transactionTable.amount.text}
                  example={helpContent.transactionTable.amount.example}
                  tips={helpContent.transactionTable.amount.tips}
                />
              </span>
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('status')} 
                <HelpTooltip 
                  text={helpContent.transactionTable.status.text}
                  example={helpContent.transactionTable.status.example}
                  tips={helpContent.transactionTable.status.tips}
                  diagram={helpContent.transactionTable.status.diagram}
                />
              </span>
            </th>
            <th className="hidden md:table-cell whitespace-nowrap px-4 py-3 font-medium">
              <span className="inline-flex items-center gap-1">
                {t('txHash')} 
                <HelpTooltip 
                  text={helpContent.transactionTable.txHash.text}
                  example={helpContent.transactionTable.txHash.example}
                  tips={helpContent.transactionTable.txHash.tips}
                />
              </span>
            </th>
            <th className="whitespace-nowrap px-4 py-3 text-right font-medium">
              <span className="inline-flex items-center gap-1">
                {t('date')} 
                <HelpTooltip 
                  text={helpContent.transactionTable.date.text}
                  example={helpContent.transactionTable.date.example}
                  tips={helpContent.transactionTable.date.tips}
                />
              </span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
          {transactions.length === 0 && (
            <tr>
              <td colSpan={6} className="hidden md:table-cell px-4 py-12 text-center text-slate-500">
                {t('noTransactions')}
              </td>
            </tr>
          )}
          {transactions.map((tx) => (
            <tr key={tx.unid} className="transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30">
              <td className="whitespace-nowrap px-4 py-3">
                <Link
                  href={`/transactions/${tx.unid}`}
                  className="font-mono text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition-colors"
                >
                  {shortenAddress(tx.unid, 8)}
                </Link>
              </td>
              <td className="whitespace-nowrap px-4 py-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-slate-700 dark:text-slate-300">
                    {shortenAddress(tx.to_addr)}
                  </span>
                  <CopyButton text={tx.to_addr} />
                </div>
              </td>
              <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-900 dark:text-white">
                {formatValue(tx.value)} {tx.token_name || ""}
              </td>
              <td className="whitespace-nowrap px-4 py-3">
                <StatusBadge status={tx.status} />
              </td>
              <td className="whitespace-nowrap px-4 py-3 font-mono text-slate-500 dark:text-slate-400">
                {tx.tx_hash ? shortenAddress(tx.tx_hash) : "-"}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-right text-slate-500 dark:text-slate-400">
                {tx.init_ts ? formatTimestamp(new Date(tx.init_ts * 1000)) : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table></div>
    </div>
  );
}
