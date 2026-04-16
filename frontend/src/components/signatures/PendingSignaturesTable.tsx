"use client";

import { useState } from "react";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "@/components/common/StatusBadge";
import { CopyButton } from "@/components/common/CopyButton";
import { SignatureProgressIndicator } from "./SignatureProgressIndicator";
import { RejectDialog } from "./RejectDialog";
import { Icon } from "@/lib/icons";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { Tooltip, HelpText } from "@/components/ui/Tooltip";
import { helpContent } from "@/lib/help-content";
import { useTranslations } from "@/hooks/useTranslations";
import { parseToken as parseTokenUtil, formatValueWithToken } from "@/lib/token-utils";

interface PendingSignature {
  token: string;
  to_addr: string;
  tx_value: string;
  init_ts: number;
  unid: string;
}

interface SignatureStatus {
  signed: string[];
  waiting: string[];
  progress: string;
  is_complete: boolean;
}

interface Props {
  signatures: PendingSignature[];
  onSign: (txUnid: string) => Promise<void>;
  onReject: (txUnid: string, reason: string) => Promise<void>;
  getStatus?: (txUnid: string) => Promise<SignatureStatus>;
  loading?: boolean;
}

export function PendingSignaturesTable({
  signatures,
  onSign,
  onReject,
  getStatus,
  loading = false,
}: Props) {
  const t = useTranslations('signatures.pending.table');
  const [signingTxUnid, setSigningTxUnid] = useState<string | null>(null);
  const [rejectingTxUnid, setRejectingTxUnid] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<Record<string, SignatureStatus>>({});

  const calculateAge = (timestamp: number) => {
    const now = Date.now();
    const ageMs = now - timestamp * 1000;
    const ageHours = ageMs / (1000 * 60 * 60);

    if (ageHours < 1) {
      return `${Math.round(ageMs / (1000 * 60))}m`;
    } else if (ageHours < 24) {
      return `${Math.round(ageHours)}h`;
    } else {
      return `${Math.round(ageHours / 24)}d`;
    }
  };

  // Use token-utils for parsing
  // formatValue and parseToken moved to token-utils

  const handleSign = async (txUnid: string) => {
    setSigningTxUnid(txUnid);
    try {
      await onSign(txUnid);
    } finally {
      setSigningTxUnid(null);
    }
  };

  const handleReject = async (txUnid: string, reason: string) => {
    setRejectingTxUnid(null);
    try {
      await onReject(txUnid, reason);
    } catch (error) {
      // Error handled by parent
    }
  };

  const loadStatus = async (txUnid: string) => {
    if (!getStatus) return;
    try {
      const status = await getStatus(txUnid);
      setStatuses((prev) => ({ ...prev, [txUnid]: status }));
    } catch (error) {
      console.error("Failed to load signature status:", error);
    }
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

  if (signatures.length === 0) {
    return (
      <Card>
        <div className="p-6 text-center">
          <Icon 
            icon="solar:check-circle-bold" 
            className="mx-auto mb-4 text-6xl text-green-500 dark:text-green-400"
          />
          <h3 className="text-lg font-medium text-slate-900 dark:text-slate-100">
            {t('noSignatures')}
          </h3>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <div className="overflow-x-auto">
          <div className="overflow-x-auto"><table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800">
              <tr>
                <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                  {t('token')}
                </th>
                <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                  {t('value')}
                </th>
                <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                  {t('to')}
                </th>
                <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                  <span className="inline-flex items-center gap-1">
                    {t('age')}
                    <HelpTooltip
                      text={helpContent.signatures.urgencyIndicator.text}
                      example={helpContent.signatures.urgencyIndicator.example}
                      tips={helpContent.signatures.urgencyIndicator.tips}
                    />
                  </span>
                </th>
                <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                  <span className="inline-flex items-center gap-1">
                    {t('progress')}
                    <HelpTooltip
                      text={helpContent.signatures.signatureCounter.text}
                      example={helpContent.signatures.signatureCounter.example}
                      tips={helpContent.signatures.signatureCounter.tips}
                    />
                  </span>
                </th>
                <th className="px-4 py-3 font-medium text-slate-700 dark:text-slate-300">
                  {t('actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {signatures.map((sig) => {
                const parsed = parseTokenUtil(sig.token);
                const tokenSymbol = parsed?.tokenSymbol || sig.token;
                const walletName = parsed?.walletName || '';
                const status = statuses[sig.unid];

                return (
                  <tr
                    key={sig.unid}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 dark:text-slate-100">
                          {tokenSymbol}
                        </span>
                        {walletName && (
                          <span className="text-xs text-slate-500 dark:text-slate-400">
                            {walletName}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-slate-900 dark:text-slate-100">
                        {sig.tx_value.replace(",", ".")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <span className="font-mono text-xs text-slate-600 dark:text-slate-400">
                          {sig.to_addr.substring(0, 10)}...
                          {sig.to_addr.substring(sig.to_addr.length - 8)}
                        </span>
                        <CopyButton text={sig.to_addr} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge
                        status={calculateAge(sig.init_ts)}
                      />
                    </td>
                    <td className="px-4 py-3">
                      {status ? (
                        <SignatureProgressIndicator
                          signed={status.signed}
                          waiting={status.waiting}
                          totalRequired={
                            status.signed.length + status.waiting.length
                          }
                          isComplete={status.is_complete}
                        />
                      ) : (
                        <button
                          onClick={() => loadStatus(sig.unid)}
                          className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          {t('loadStatusButton')}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <Tooltip
                          content={
                            <HelpText
                              title={helpContent.signatures.signButton.text.split('.')[0]}
                              description={helpContent.signatures.signButton.text}
                              example={helpContent.signatures.signButton.example}
                              tips={helpContent.signatures.signButton.tips}
                            />
                          }
                          position="top"
                          maxWidth="320px"
                        >
                          <button
                            onClick={() => handleSign(sig.unid)}
                            disabled={signingTxUnid === sig.unid}
                            className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {signingTxUnid === sig.unid ? t('signing') : t('signButton')}
                          </button>
                        </Tooltip>
                        <Tooltip
                          content={
                            <HelpText
                              title={helpContent.signatures.rejectButton.text.split('.')[0]}
                              description={helpContent.signatures.rejectButton.text}
                              example={helpContent.signatures.rejectButton.example}
                              tips={helpContent.signatures.rejectButton.tips}
                            />
                          }
                          position="top"
                          maxWidth="320px"
                        >
                          <button
                            onClick={() => setRejectingTxUnid(sig.unid)}
                            disabled={signingTxUnid === sig.unid}
                            className="rounded bg-red-600 px-3 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {t('rejectButton')}
                          </button>
                        </Tooltip>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table></div>
        </div>
      </Card>

      {rejectingTxUnid && (
        <RejectDialog
          txUnid={rejectingTxUnid}
          onConfirm={(reason) => handleReject(rejectingTxUnid, reason)}
          onCancel={() => setRejectingTxUnid(null)}
        />
      )}
    </>
  );
}
