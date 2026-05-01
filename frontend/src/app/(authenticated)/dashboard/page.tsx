"use client";

import useSWR from "swr";
import { useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, BigNum, Mono, StatusPill } from "@/components/ui/primitives";
import { Sparkline } from "@/components/ui/Sparkline";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useWebSocket } from "@/contexts/WebSocketContext";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import { formatWalletDisplayName } from "@/lib/walletDisplay";

interface Stats {
  total_wallets?: number;
  total_balance_usd?: string | number;
  transactions_24h?: number;
  pending_signatures?: number;
  networks_active?: number;
  last_sync?: string | null;
}

interface RecentItem {
  id?: number | string;
  tx_unid?: string;
  tx_hash?: string | null;
  wallet_name?: string;
  status?: string;
  amount_decimal?: string | number;
  value?: string | number;
  token?: string | null;
  to_address?: string;
  to_addr?: string;
  network?: number | string;
  created_at?: string;
  info?: string;
}

interface AlertItem {
  id?: number | string;
  severity?: "high" | "medium" | "low" | string;
  title?: string;
  message?: string;
  created_at?: string;
}

const STATUS_TO_KIND: Record<string, "confirmed" | "pending" | "sent" | "rejected"> = {
  confirmed: "confirmed",
  pending: "pending",
  sent: "sent",
  rejected: "rejected",
};

function formatTime(iso?: string): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
  } catch {
    return iso.slice(11, 16);
  }
}

function formatNumber(n?: string | number, fractionDigits = 0): string {
  const v = typeof n === "string" ? Number(n) : n ?? 0;
  if (Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits }).format(v);
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { lastEvent } = useWebSocket();

  const { data: stats, error: statsError, mutate: mutateStats } = useSWR<Stats>(
    "/api/dashboard/stats",
    api.getDashboardStats,
    { refreshInterval: 30000 },
  );
  const { data: recent, mutate: mutateRecent } = useSWR<RecentItem[]>(
    "/api/dashboard/recent",
    () => api.getDashboardRecent(20),
    { refreshInterval: 30000 },
  );
  const { data: alerts, mutate: mutateAlerts } = useSWR<AlertItem[]>(
    "/api/dashboard/alerts",
    api.getDashboardAlerts,
    { refreshInterval: 60000 },
  );

  useEffect(() => {
    if (!lastEvent) return;
    const t = lastEvent.type as string;
    if (
      t === "transaction.created" ||
      t === "transaction.confirmed" ||
      t === "transaction.failed" ||
      t === "balance.updated" ||
      t === "wallet.created" ||
      t === "sync.completed"
    ) {
      mutateStats();
      mutateRecent();
      mutateAlerts();
    }
  }, [lastEvent, mutateStats, mutateRecent, mutateAlerts]);

  const recentList: RecentItem[] = Array.isArray(recent) ? recent : [];
  const alertList: AlertItem[] = Array.isArray(alerts) ? alerts : [];
  const balanceUsd = stats?.total_balance_usd ?? "0.00";

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-8">
        {statsError && (
          <div className="border border-destructive/40 bg-destructive/5 p-4 text-[13px] text-destructive">
            Не удалось загрузить данные. Повторите позже.
          </div>
        )}

        {/* KPI grid */}
        <section>
          <Eyebrow dash>Сводка</Eyebrow>
          <div className="mt-4 grid grid-cols-2 lg:grid-cols-5 gap-px bg-border border border-border">
            <KpiTile label="Общий баланс" value={`$ ${formatNumber(balanceUsd, 2)}`} sub="USD эквивалент" big />
            <KpiTile label="Кошельки" value={String(stats?.total_wallets ?? "—")} sub="всего" />
            <KpiTile label="Транзакции, 24ч" value={String(stats?.transactions_24h ?? "—")} sub="за последние 24 часа" />
            <KpiTile label="Ожидают подписи" value={String(stats?.pending_signatures ?? "—")} sub="требуют действия" accent />
            <KpiTile label="Сети" value={String(stats?.networks_active ?? "—")} sub="активные" />
          </div>
        </section>

        {/* Two-column: recent activity (wide) + sparkline & alerts (narrow) */}
        <section className="grid lg:grid-cols-[1.6fr_1fr] gap-6">
          {/* Recent transactions */}
          <div className="border border-border bg-card">
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <div>
                <Eyebrow>Последние транзакции</Eyebrow>
                <h3 className="mt-1 text-[14px] font-medium tracking-tight text-foreground">
                  {recentList.length > 0 ? `${recentList.length} записей` : "—"}
                </h3>
              </div>
              <Link href="/transactions">
                <Button variant="ghost" size="sm">
                  Все транзакции
                  <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
                </Button>
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-[12px] border-collapse">
                <thead>
                  <tr className="text-left">
                    <th className="px-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Статус</th>
                    <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Кошелёк</th>
                    <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal text-right">Сумма</th>
                    <th className="px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal">Получатель</th>
                    <th className="px-5 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal text-right">Время</th>
                  </tr>
                </thead>
                <tbody>
                  {recentList.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-14">
                        <div className="flex flex-col items-center text-center">
                          <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mb-3">
                            <Icon icon="solar:transfer-horizontal-linear" className="text-2xl text-muted-foreground" />
                          </div>
                          <p className="text-[14px] font-medium text-foreground mb-1">Транзакций пока нет</p>
                          <p className="text-[12px] text-muted-foreground mb-4 max-w-sm">
                            Когда вы создадите первую транзакцию или подпишете запрос — она появится здесь и в реальном времени отразится в аудит-логе.
                          </p>
                          <Link href="/transactions/new">
                            <Button variant="secondary" size="sm">
                              <Icon icon="solar:add-circle-linear" className="text-[14px]" />
                              Создать транзакцию
                            </Button>
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    recentList.slice(0, 8).map((tx, i) => {
                      const kind = STATUS_TO_KIND[(tx.status ?? "").toLowerCase()] ?? "neutral";
                      const amount = tx.amount_decimal ?? tx.value ?? "—";
                      const dest = tx.to_address || tx.to_addr || "—";
                      return (
                        <tr key={tx.tx_unid ?? tx.id ?? i} className="border-t border-border hover:bg-muted/40">
                          <td className="px-5 py-3"><StatusPill kind={kind as any} label={tx.status ?? "—"} /></td>
                          <td className="px-3 py-3 text-foreground">
                            <span
                              className="text-[12px] font-mono"
                              title={tx.wallet_name ?? undefined}
                            >
                              {formatWalletDisplayName({
                                name: tx.wallet_name ?? null,
                                wallet_name: tx.wallet_name ?? null,
                                network: tx.network ?? null,
                              })}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-right tabular text-foreground">
                            {String(amount)}{" "}
                            <span className="text-muted-foreground">{tx.token ?? ""}</span>
                          </td>
                          <td className="px-3 py-3"><Mono truncate>{dest}</Mono></td>
                          <td className="px-5 py-3 text-right"><Mono size="xs" className="text-faint">{formatTime(tx.created_at)}</Mono></td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right column */}
          <div className="space-y-6">
            <div className="border border-border bg-card p-5">
              <Eyebrow>Баланс · 30Д</Eyebrow>
              <BigNum size="xl" className="mt-2">$ {formatNumber(balanceUsd, 0)}</BigNum>
              <Mono size="xs" className="mt-1 text-muted-foreground block">Авто-обновление каждые 30с</Mono>
              <div className="mt-4 text-primary">
                <Sparkline points={[6, 7, 5, 8, 7, 9, 8, 10, 9, 11, 10, 12, 11, 13, 12, 14, 13, 15]} width={300} height={64} />
              </div>
            </div>

            <div className="border border-border bg-card">
              <div className="px-5 py-4 border-b border-border flex items-center justify-between">
                <Eyebrow>Уведомления</Eyebrow>
                <Mono size="xs" className="text-faint">{alertList.length}</Mono>
              </div>
              <ul>
                {alertList.length === 0 ? (
                  <li className="px-5 py-10">
                    <div className="flex flex-col items-center text-center">
                      <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-2">
                        <Icon icon="solar:bell-off-linear" className="text-xl text-muted-foreground" />
                      </div>
                      <p className="text-[13px] font-medium text-foreground">Тишина</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5 max-w-[18rem]">
                        Алерты по AML, превышениям лимитов и аномалиям будут появляться здесь.
                      </p>
                    </div>
                  </li>
                ) : (
                  alertList.slice(0, 4).map((a, i) => (
                    <li key={a.id ?? i} className={cn("flex items-start gap-3 px-5 py-3", i > 0 && "border-t border-border")}>
                      <span
                        className={cn(
                          "inline-block w-1.5 h-1.5 rounded-full mt-1.5 shrink-0",
                          a.severity === "high" ? "bg-destructive" : a.severity === "medium" ? "bg-warning" : "bg-faint",
                        )}
                      />
                      <div className="min-w-0">
                        <div className="text-[13px] text-foreground">{a.title ?? a.message ?? "—"}</div>
                        {a.message && a.title && (
                          <div className="text-[12px] text-muted-foreground mt-0.5">{a.message}</div>
                        )}
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        </section>

        {/* Sync status footer */}
        {stats?.last_sync && (
          <div className="flex justify-end">
            <Mono size="xs" className="text-faint">
              Последняя синхронизация · {new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(stats.last_sync))}
            </Mono>
          </div>
        )}
      </div>
    </>
  );
}

function KpiTile({
  label,
  value,
  sub,
  big = false,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  big?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="bg-card p-5 lg:p-6">
      <Eyebrow>{label}</Eyebrow>
      <BigNum size={big ? "xl" : "lg"} className={cn("mt-2", accent && "text-primary")}>{value}</BigNum>
      {sub && <Mono size="xs" className="mt-2 text-muted-foreground block">{sub}</Mono>}
    </div>
  );
}
