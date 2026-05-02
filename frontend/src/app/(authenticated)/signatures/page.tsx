"use client";

import { useState } from "react";
import useSWR from "swr";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, BigNum, Mono, StatusPill } from "@/components/ui/primitives";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import toast from "react-hot-toast";

interface PendingSig {
  tx_unid?: string;
  wallet_name?: string;
  to_address?: string;
  to_addr?: string;
  amount?: string | number;
  amount_decimal?: string | number;
  value?: string | number;
  token?: string;
  network?: number;
  signed_count?: number;
  required_count?: number;
  threshold?: string;
  created_at?: string;
}

interface HistoryItem {
  tx_unid?: string;
  signer_address?: string;
  action?: "signed" | "rejected" | string;
  reason?: string | null;
  signed_at?: string;
}

interface SigStats {
  pending_count?: number;
  signed_last_24h?: number;
  rejected_last_24h?: number;
  total_signers?: number;
}

function formatTime(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function SignaturesPage() {
  const t = useTranslations("signatures");
  const [busy, setBusy] = useState<string | null>(null);

  const { data: pending, mutate: mutatePending } = useSWR<PendingSig[]>(
    "/api/signatures/pending",
    api.getPendingSignaturesV2,
    { refreshInterval: 30000 },
  );
  const { data: history, mutate: mutateHistory } = useSWR<HistoryItem[]>(
    "/api/signatures/history",
    () => api.getSignatureHistory(30),
    { refreshInterval: 60000 },
  );
  const { data: stats, mutate: mutateStats } = useSWR<SigStats>(
    "/api/signatures/stats",
    api.getSignatureStats,
    { refreshInterval: 60000 },
  );

  const pendingList: PendingSig[] = Array.isArray(pending) ? pending : [];
  const historyList: HistoryItem[] = Array.isArray(history) ? history : [];

  async function handleSign(txUnid: string) {
    setBusy(txUnid);
    try {
      await api.signTransactionV2(txUnid);
      toast.success(`Подписано: ${txUnid.slice(0, 8)}…`);
      mutatePending(); mutateHistory(); mutateStats();
    } catch (e: any) {
      toast.error(e?.message ?? "Ошибка подписи");
    } finally {
      setBusy(null);
    }
  }

  async function handleReject(txUnid: string) {
    const reason = window.prompt("Причина отклонения (опционально):", "") ?? "";
    setBusy(txUnid);
    try {
      await api.rejectTransactionV2(txUnid, reason);
      toast.success(`Отклонено: ${txUnid.slice(0, 8)}…`);
      mutatePending(); mutateHistory(); mutateStats();
    } catch (e: any) {
      toast.error(e?.message ?? "Ошибка отклонения");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-8">
        <div>
          <span className="inline-flex items-center gap-1.5">
            <Eyebrow dash>Подписи</Eyebrow>
            <HelpTooltip
              text="Multi-sig подписания транзакций."
              tips={[
                "Каждая исходящая транзакция требует N подписей из M участников (настройка кошелька в Safina).",
                "Подпись делается через KMS (если ORGON_SIGNER_BACKEND=kms) — приватный ключ не покидает HSM.",
                "ORGON локально верифицирует Safina-возвращённые подписи (Wave 22), несовпадение → tx rejected.",
                "История подписей immutable — одобренное действие в audit-log не редактируется.",
              ]}
            />
          </span>
          <h2 className="mt-2 text-[24px] sm:text-[28px] font-medium tracking-[-0.02em] text-foreground">
            Очередь подписей и история
          </h2>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
          <StatTile label="Ожидают" value={String(stats?.pending_count ?? pendingList.length)} accent />
          <StatTile label="Подписано · 24ч" value={String(stats?.signed_last_24h ?? "—")} />
          <StatTile label="Отклонено · 24ч" value={String(stats?.rejected_last_24h ?? "—")} />
          <StatTile label="Подписантов" value={String(stats?.total_signers ?? "—")} />
        </div>

        {/* Pending queue */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <Eyebrow>Ожидают подписи</Eyebrow>
            <Mono size="xs" className="text-faint">{pendingList.length} в очереди</Mono>
          </div>

          {pendingList.length === 0 ? (
            <div className="border border-border bg-card p-12">
              <div className="flex flex-col items-center text-center">
                <div className="w-14 h-14 rounded-full bg-success/10 flex items-center justify-center mb-3">
                  <Icon icon="solar:check-circle-bold" className="text-2xl text-success" />
                </div>
                <p className="text-[14px] font-medium text-foreground mb-1">Очередь пуста</p>
                <p className="text-[12px] text-muted-foreground max-w-md">
                  Когда появится транзакция, требующая M-of-N подписи, она будет здесь — с таймером политики и кнопками «Подписать» / «Отклонить». Проверить логику можно в{" "}
                  <a href="/demo/architecture" className="text-primary hover:underline">демо-симуляторе</a>.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingList.map((p) => {
                const dest = p.to_address || p.to_addr || "—";
                const amount = p.amount_decimal ?? p.amount ?? p.value ?? "—";
                const signed = p.signed_count ?? 0;
                const required = p.required_count ?? 0;
                const pct = required > 0 ? Math.min(100, Math.round((signed / required) * 100)) : 0;
                const isBusy = busy === p.tx_unid;

                return (
                  <article key={p.tx_unid} className="border border-border bg-card p-5">
                    <div className="grid lg:grid-cols-[1.4fr_0.7fr_auto] gap-5 items-start">
                      <div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <Mono size="md" className="text-foreground">{p.tx_unid?.slice(0, 12) ?? "—"}…</Mono>
                          <Badge variant="warning">Ожидает</Badge>
                          {p.token && <Badge variant="outline">{p.token}</Badge>}
                        </div>
                        <div className="mt-3 flex items-center gap-6 flex-wrap text-[12px]">
                          <span className="text-muted-foreground">
                            <span className="text-faint mr-1">из</span>
                            <Mono>{p.wallet_name?.slice(0, 12) ?? "—"}…</Mono>
                          </span>
                          <span className="text-muted-foreground">
                            <span className="text-faint mr-1">к</span>
                            <Mono>{dest}</Mono>
                          </span>
                          <Mono size="xs" className="text-faint">{formatTime(p.created_at)}</Mono>
                        </div>
                      </div>

                      <div>
                        <div className="flex items-baseline justify-between">
                          <Eyebrow>Сумма</Eyebrow>
                          <Mono size="xs" className="text-faint">{required > 0 ? `${signed}/${required}` : ""}</Mono>
                        </div>
                        <BigNum size="lg" className="mt-1">{String(amount)}</BigNum>
                        <div className="mt-2 h-1 bg-muted relative">
                          <div className="absolute left-0 top-0 h-full bg-primary" style={{ width: `${pct}%` }} />
                        </div>
                      </div>

                      <div className="flex flex-col gap-2 lg:items-end">
                        <Button variant="primary" size="sm" onClick={() => handleSign(p.tx_unid!)} disabled={isBusy} loading={isBusy}>
                          <Icon icon="solar:pen-bold" className="text-[14px]" />
                          Подписать
                        </Button>
                        <Button variant="secondary" size="sm" onClick={() => handleReject(p.tx_unid!)} disabled={isBusy}>
                          <Icon icon="solar:close-circle-linear" className="text-[14px]" />
                          Отклонить
                        </Button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        {/* History */}
        <section>
          <Eyebrow className="mb-3">История подписей</Eyebrow>
          <div className="border border-border bg-card overflow-x-auto">
            <table className="w-full text-[12px] border-collapse">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="pl-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Действие</th>
                  <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Транзакция</th>
                  <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Подписант</th>
                  <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Причина</th>
                  <th className="pr-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal text-right">Время</th>
                </tr>
              </thead>
              <tbody>
                {historyList.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-14">
                      <div className="flex flex-col items-center text-center">
                        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                          <Icon icon="solar:history-linear" className="text-xl text-muted-foreground" />
                        </div>
                        <p className="text-[14px] font-medium text-foreground mb-1">Истории подписей пока нет</p>
                        <p className="text-[12px] text-muted-foreground max-w-md">
                          Каждое действие подписанта (одобрение, отклонение, истечение таймаута) останется здесь навсегда — таблица append-only, гарантировано на уровне БД-триггера.
                        </p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  historyList.map((h, i) => (
                    <tr key={i} className="border-b border-border last:border-b-0">
                      <td className="pl-5 py-3">
                        {h.action === "rejected" ? (
                          <StatusPill kind="rejected" label="Отклонил" />
                        ) : (
                          <StatusPill kind="confirmed" label="Подписал" />
                        )}
                      </td>
                      <td className="px-3 py-3"><Mono>{h.tx_unid?.slice(0, 16) ?? "—"}…</Mono></td>
                      <td className="px-3 py-3"><Mono truncate>{h.signer_address ?? "—"}</Mono></td>
                      <td className="px-3 py-3 text-muted-foreground">{h.reason ?? "—"}</td>
                      <td className="pr-5 py-3 text-right"><Mono size="xs" className="text-faint">{formatTime(h.signed_at)}</Mono></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}

function StatTile({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="bg-card p-5">
      <Eyebrow>{label}</Eyebrow>
      <BigNum size="lg" className={cn("mt-2", accent && "text-primary")}>{value}</BigNum>
    </div>
  );
}
