"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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
import { explorerTxUrl, getNetworkConfig } from "@/lib/networkConfig";

/** Extract Safina network id (e.g. "5010") from a token string of the
 *  form "<network>:::<SYMBOL>###<wallet_name>". Returns null when the
 *  token field is missing or shaped differently. */
function networkFromToken(token: unknown): number | null {
  if (typeof token !== "string") return null;
  const head = token.split(":::")[0];
  if (!head) return null;
  const n = Number(head);
  return Number.isFinite(n) ? n : null;
}

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

  // Auto-refresh while the tx is in-flight (pending / signed without
  // tx_hash). Sync is the same primitive the dashboard + send-page
  // poll on; we just close the loop here so a user landing via
  // drill-down doesn't have to manually reload. Polling halts on
  // terminal status — both branches handled by `shouldPoll`.
  useEffect(() => {
    if (!tx) return;
    const status = String(tx.status ?? "").toLowerCase();
    const hashStr = (tx.tx_hash ? String(tx.tx_hash) : "").trim();
    const isSentinel =
      hashStr.toLowerCase().includes("canceled") ||
      hashStr.toLowerCase().includes("limit");
    const shouldPoll =
      !hashStr || isSentinel
        ? !(
            status === "rejected" ||
            status === "failed" ||
            status === "rejected_signer_mismatch" ||
            isSentinel
          )
        : false;
    if (!shouldPoll) return;
    const id = setInterval(loadTx, 6000);
    return () => clearInterval(id);
  }, [tx, unid]);

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
        <Header title="Транзакция" />
        <div className="p-4 sm:p-6 lg:p-8">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-xs text-destructive">
            {error}
          </div>
        </div>
      </>
    );
  }

  if (!tx) {
    return (
      <>
        <Header title="Транзакция" />
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
            title={`Транзакция ${unid.slice(0, 16)}…`}
            action={<StatusBadge status={String(tx.status)} />}
          />
          <div className="space-y-4 p-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">UNID</p>
                <div className="flex items-center gap-2">
                  <p className="font-mono text-xs text-foreground break-all">{String(tx.unid)}</p>
                  <CopyButton text={String(tx.unid)} />
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">Адрес получателя</p>
                <div className="flex items-center gap-2">
                  <p className="font-mono text-xs text-foreground break-all">{String(tx.to_addr)}</p>
                  <CopyButton text={String(tx.to_addr)} />
                </div>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">Сумма</p>
                <p className="text-sm font-semibold text-foreground">
                  {formatValue(String(tx.value))} {String(tx.token_name || "")}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5">Дата</p>
                <p className="text-xs text-foreground">
                  {tx.init_ts ? formatTimestamp(new Date(Number(tx.init_ts) * 1000)) : "-"}
                </p>
              </div>
              {tx.tx_hash ? (
                <div className="col-span-full">
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">Хэш транзакции</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-mono text-xs text-foreground break-all">{String(tx.tx_hash)}</p>
                    <CopyButton text={String(tx.tx_hash)} />
                    {(() => {
                      const net = networkFromToken(tx.token);
                      const url = explorerTxUrl(net, String(tx.tx_hash));
                      const name = getNetworkConfig(net)?.explorerName ?? "explorer";
                      return url ? (
                        <a
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                        >
                          Открыть в {name}
                          <Icon icon="solar:arrow-right-up-linear" className="text-sm" />
                        </a>
                      ) : null;
                    })()}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </Card>

        {/* In-flight progress widget — same 3-step ladder as on
            /wallets/[name]/send?tx=<unid>, mirrored here so a user
            who drills in from /dashboard sees current status without
            jumping back to the send form. Renders only when the tx is
            actually in motion (signed, awaiting broadcast, or pending
            without on-chain confirmation yet). Auto-refreshes every
            6s via the parent `loadTx` interval — see useEffect below. */}
        {(() => {
          const status = String(tx.status ?? "").toLowerCase();
          const hashStr = (tx.tx_hash ? String(tx.tx_hash) : "").trim();
          const isSentinel =
            hashStr.toLowerCase().includes("canceled") ||
            hashStr.toLowerCase().includes("limit");
          const hasRealHash = !!hashStr && !isSentinel;
          // Step cursor:
          //   pending / signed / sent without hash → broadcasting (cursor=2)
          //   real tx_hash present → done (cursor=4, all 3 ticked)
          //   rejected/failed/sentinel → error (cursor=-1, list hidden)
          const isErrorTerm =
            status === "rejected" ||
            status === "failed" ||
            status === "rejected_signer_mismatch" ||
            isSentinel;
          const isInFlight = !hasRealHash && !isErrorTerm && status !== "on_hold";
          if (!isInFlight && !hasRealHash) return null;
          const steps = [
            { label: "Подписание", sublabel: "Подписали нашим EC ключом" },
            { label: "Отправка в сеть", sublabel: "Safina передаёт транзакцию в блокчейн" },
            { label: "Подтверждение", sublabel: "Транзакция принята сетью" },
          ];
          // For drilled-in view we always know sign happened (the row
          // wouldn't exist otherwise). With hash → all done. Without
          // → step 2 active.
          const cursor = hasRealHash ? 4 : 2;
          return (
            <Card>
              <CardHeader
                title="Прогресс"
                subtitle={
                  hasRealHash
                    ? "Транзакция в сети"
                    : "Ждём, пока Safina передаст транзакцию в блокчейн. Автообновление каждые 6 секунд."
                }
              />
              <ol className="space-y-2 p-4">
                {steps.map((s, i) => {
                  const idx = i + 1;
                  const done = cursor > idx;
                  const active = cursor === idx;
                  return (
                    <li
                      key={s.label}
                      className={
                        done
                          ? "rounded-lg border border-success/30 bg-success/5 px-3 py-2"
                          : active
                          ? "rounded-lg border border-primary/30 bg-primary/5 px-3 py-2"
                          : "rounded-lg border border-border bg-muted/30 px-3 py-2"
                      }
                    >
                      <div className="flex items-center gap-3">
                        {done ? (
                          <Icon icon="solar:check-circle-bold" className="text-success text-lg" />
                        ) : active ? (
                          <Icon icon="solar:refresh-bold" className="text-primary text-lg animate-spin" />
                        ) : (
                          <Icon icon="solar:clock-circle-linear" className="text-muted-foreground text-lg" />
                        )}
                        <div>
                          <p className={done || active ? "text-xs font-medium text-foreground" : "text-xs font-medium text-muted-foreground"}>
                            {s.label}
                          </p>
                          <p className="text-[10px] text-muted-foreground">{s.sublabel}</p>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ol>
            </Card>
          );
        })()}

        {/* Wave 23 / Story 2.8 — if an in-house AML rule held this tx,
            surface it prominently with a deep-link to the AML triage queue. */}
        {tx.status === "on_hold" && (
          <Card>
            <div className="flex items-start gap-3 p-4">
              <Icon icon="solar:shield-warning-bold" className="text-2xl text-warning shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  Транзакция на удержании AML-правилом
                </p>
                <p className="text-xs text-muted-foreground">
                  Сработавшее правило мониторинга поставило транзакцию на ручную проверку.
                  Подписание заблокировано до разрешения compliance-офицером.
                </p>
                <Link href="/compliance?tab=aml" className="text-xs text-primary underline-offset-4 hover:underline inline-flex items-center gap-1 mt-1">
                  Открыть очередь AML
                  <Icon icon="solar:alt-arrow-right-linear" className="text-xs" />
                </Link>
              </div>
            </div>
          </Card>
        )}

        {tx.status === "pending" && (
          <Card>
            <CardHeader title="Действия" subtitle="Подписать или отклонить транзакцию" />
            <div className="flex gap-3 p-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSign}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-success px-4 py-2 text-xs font-medium text-primary-foreground hover:bg-success disabled:opacity-50 transition-colors"
                >
                  <Icon icon="solar:pen-new-square-linear" className="text-sm" />
                  {actionLoading ? "Обработка…" : "Подписать"}
                </button>
                <HelpTooltip text={helpContent.transactionDetail.sign.text} diagram={helpContent.transactionDetail.sign.diagram} />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReject}
                  disabled={actionLoading}
                  className="inline-flex items-center gap-2 rounded-lg border border-destructive/30 px-4 py-2 text-xs font-medium text-destructive hover:bg-destructive/10 disabled:opacity-50 transition-colors"
                >
                  <Icon icon="solar:close-circle-linear" className="text-sm" />
                  Отклонить
                </button>
                <HelpTooltip text={helpContent.transactionDetail.reject.text} />
              </div>
            </div>
          </Card>
        )}

        {tx.signatures && Array.isArray(tx.signatures) && (tx.signatures as Record<string, unknown>[]).length > 0 ? (
          <Card>
            <CardHeader title="Подписи" action={<HelpTooltip text={helpContent.transactionDetail.signatures.text} />} />
            <div className="space-y-2 p-4">
              {(tx.signatures as Record<string, unknown>[]).map((sig, i) => (
                <div key={i} className="flex items-center justify-between rounded-lg border border-border px-4 py-3">
                  <p className="font-mono text-xs text-muted-foreground">{String(sig.ec_address)}</p>
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
