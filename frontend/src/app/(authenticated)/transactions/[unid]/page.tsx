"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CopyButton } from "@/components/common/CopyButton";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { formatValue, formatTimestamp } from "@/lib/utils";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";

export default function TransactionDetailPage() {
  const params = useParams();
  const unid = params.unid as string;
  const [tx, setTx] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const loadTx = () => {
    api.getTransaction(unid).then(setTx).catch((e) => setError(e.message));
  };

  useEffect(loadTx, [unid]);

  const handleSign = async () => {
    setActionLoading(true);
    try {
      await api.signTransaction(unid);
      loadTx();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign failed");
    }
    setActionLoading(false);
  };

  const handleReject = async () => {
    const reason = prompt("Rejection reason (optional):");
    if (reason === null) return;
    setActionLoading(true);
    try {
      await api.rejectTransaction(unid, reason);
      loadTx();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reject failed");
    }
    setActionLoading(false);
  };

  if (error) {
    return (
      <>
        <Header title="Transaction Detail" />
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        </div>
      </>
    );
  }

  if (!tx) {
    return (
      <>
        <Header title="Transaction Detail" />
        <div className="p-6"><LoadingSpinner /></div>
      </>
    );
  }

  return (
    <>
      <Header title="Transaction Detail" />
      <div className="space-y-4 p-2 sm:p-4 md:p-6 lg:p-8 max-w-3xl">
        <Card>
          <CardHeader
            title={`Transaction ${unid.slice(0, 16)}...`}
            action={<StatusBadge status={String(tx.status)} />}
          />
          <div className="space-y-4 p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">UNID</p>
                <div className="flex items-center gap-2">
                  <p className="font-mono text-xs text-slate-900 dark:text-white break-all">{String(tx.unid)}</p>
                  <CopyButton text={String(tx.unid)} />
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">To Address</p>
                <div className="flex items-center gap-2">
                  <p className="font-mono text-xs text-slate-900 dark:text-white break-all">{String(tx.to_addr)}</p>
                  <CopyButton text={String(tx.to_addr)} />
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Amount</p>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">
                  {formatValue(String(tx.value))} {String(tx.token_name || "")}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">Date</p>
                <p className="text-xs text-slate-900 dark:text-white">
                  {tx.init_ts ? formatTimestamp(new Date(Number(tx.init_ts) * 1000)) : "-"}
                </p>
              </div>
              {tx.tx_hash ? (
                <div className="col-span-full">
                  <p className="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1.5">TX Hash</p>
                  <div className="flex items-center gap-2">
                    <p className="font-mono text-xs text-slate-900 dark:text-white break-all">{String(tx.tx_hash)}</p>
                    <CopyButton text={String(tx.tx_hash)} />
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </Card>

        {tx.status === "pending" && (
          <Card>
            <CardHeader title="Actions" subtitle="Sign or reject this transaction" />
            <div className="flex gap-3 p-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSign}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                >
                  <Icon icon="solar:pen-new-square-linear" className="text-sm" />
                  {actionLoading ? "Processing..." : "Sign Transaction"}
                </button>
                <HelpTooltip text={helpContent.transactionDetail.sign.text} diagram={helpContent.transactionDetail.sign.diagram} />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-lg border border-red-200 px-4 py-2 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:border-red-500/30 dark:text-red-400 dark:hover:bg-red-500/10 transition-colors"
                >
                  <Icon icon="solar:close-circle-linear" className="text-sm" />
                  Reject
                </button>
                <HelpTooltip text={helpContent.transactionDetail.reject.text} />
              </div>
            </div>
          </Card>
        )}

        {tx.signatures && Array.isArray(tx.signatures) && (tx.signatures as Record<string, unknown>[]).length > 0 ? (
          <Card>
            <CardHeader title="Signatures" action={<HelpTooltip text={helpContent.transactionDetail.signatures.text} />} />
            <div className="space-y-2 p-4">
              {(tx.signatures as Record<string, unknown>[]).map((sig, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3 dark:border-slate-800">
                  <p className="font-mono text-xs text-slate-600 dark:text-slate-300">{String(sig.ec_address)}</p>
                  <StatusBadge status={String(sig.sig_type)} />
                </div>
              ))}
            </div>
          </Card>
        ) : null}
      </div>
    </>
  );
}
