"use client";

import Link from "next/link";
import { Card, CardHeader } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { shortenAddress, formatValue, formatTimestamp } from "@/lib/utils";

type Transaction = {
  unid: string;
  to_addr: string;
  value: string;
  token_name?: string;
  status: string;
  init_ts: number;
};

export function RecentTransactions({ transactions }: { transactions: Transaction[] }) {
  return (
    <Card>
      <CardHeader
        title="Recent Transactions"
        action={
          <Link
            href="/transactions"
            className="text-xs text-slate-500 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            View all
          </Link>
        }
      />
      <div className="overflow-x-auto p-2">
        <div className="overflow-x-auto"><table className="min-w-full text-left text-xs">
          <thead className="text-slate-500">
            <tr>
              <th className="whitespace-nowrap px-2 py-2 font-medium">To</th>
              <th className="whitespace-nowrap px-2 py-2 font-medium">Amount</th>
              <th className="whitespace-nowrap px-2 py-2 font-medium">Status</th>
              <th className="whitespace-nowrap px-2 py-2 text-right font-medium">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800/50">
            {transactions.length === 0 && (
              <tr>
                <td colSpan={4} className="py-8 text-center text-slate-500">
                  No transactions yet
                </td>
              </tr>
            )}
            {transactions.map((tx) => (
              <tr key={tx.unid} className="group transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/30">
                <td className="whitespace-nowrap px-2 py-3">
                  <Link
                    href={`/transactions/${tx.unid}`}
                    className="font-mono text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition-colors"
                  >
                    {shortenAddress(tx.to_addr)}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-2 py-3 font-medium text-slate-900 dark:text-white">
                  {formatValue(tx.value)} {tx.token_name || ""}
                </td>
                <td className="whitespace-nowrap px-2 py-3">
                  <StatusBadge status={tx.status} />
                </td>
                <td className="whitespace-nowrap px-2 py-3 text-right text-slate-500 dark:text-slate-400">
                  {tx.init_ts ? formatTimestamp(new Date(tx.init_ts * 1000)) : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </div>
    </Card>
  );
}
