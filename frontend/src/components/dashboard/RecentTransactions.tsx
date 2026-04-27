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
            className="text-xs text-muted-foreground hover:text-foreground dark:hover:text-white transition-colors"
          >
            View all
          </Link>
        }
      />
      <div className="overflow-x-auto p-2">
        <div className="overflow-x-auto"><table className="min-w-full text-left text-xs">
          <thead className="text-muted-foreground">
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
                <td colSpan={4} className="py-8 text-center text-muted-foreground">
                  No transactions yet
                </td>
              </tr>
            )}
            {transactions.map((tx) => (
              <tr key={tx.unid} className="group transition-colors hover:bg-muted dark:hover:bg-muted/30">
                <td className="whitespace-nowrap px-2 py-3">
                  <Link
                    href={`/transactions/${tx.unid}`}
                    className="font-mono text-foreground hover:text-foreground dark:text-faint dark:hover:text-white transition-colors"
                  >
                    {shortenAddress(tx.to_addr)}
                  </Link>
                </td>
                <td className="whitespace-nowrap px-2 py-3 font-medium text-foreground">
                  {formatValue(tx.value)} {tx.token_name || ""}
                </td>
                <td className="whitespace-nowrap px-2 py-3">
                  <StatusBadge status={tx.status} />
                </td>
                <td className="whitespace-nowrap px-2 py-3 text-right text-muted-foreground">
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
