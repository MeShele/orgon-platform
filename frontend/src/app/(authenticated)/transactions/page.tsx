"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Eyebrow, Mono, StatusPill } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/lib/icons";
import { api, API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatWalletDisplayName } from "@/lib/walletDisplay";

interface Tx {
  id?: number;
  tx_unid?: string;
  unid?: string | null;
  tx_hash?: string | null;
  wallet_name?: string;
  status?: string;
  amount_decimal?: string | number;
  value?: string | number;
  /** Backend returns the compound encoded string (`5010:::TRX###<id>`)
   *  in `token` and the clean symbol in `token_name`. Prefer `token_name`
   *  for display; fall back to extracting from `token`. */
  token?: string | null;
  token_name?: string | null;
  to_address?: string;
  to_addr?: string;
  network?: number | null;
  fee?: string | number;
  created_at?: string;
  info?: string;
}

/**
 * Backend `tx.token` is a compound string of shape
 *   "<networkId>:::<SYMBOL>###<wallet-uid>"
 * For display we want only the SYMBOL between `:::` and `###`.
 * If `token_name` is provided, prefer it. Returns "—" when empty.
 */
function tokenSymbol(tx: Tx): string {
  const clean = (tx.token_name ?? "").trim();
  if (clean) return clean;
  const raw = (tx.token ?? "").trim();
  if (!raw) return "—";
  const m = raw.match(/^[^:]*:::([^#]+?)(?:###.*)?$/);
  return (m?.[1] ?? raw).trim() || "—";
}

const STATUS_OPTIONS = [
  { value: "", label: "Все" },
  { value: "confirmed", label: "Подтверждены" },
  { value: "pending", label: "В обработке" },
  { value: "sent", label: "Отправлены" },
  { value: "rejected", label: "Отклонены" },
];

function formatTime(iso?: string): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(d);
  } catch {
    return iso;
  }
}

export default function TransactionsPage() {
  const t = useTranslations("transactions");
  const router = useRouter();

  const [statusFilter, setStatusFilter] = useState<string>("");
  const [exporting, setExporting] = useState(false);

  const { data: transactions, error, isLoading } = useSWR<Tx[]>(
    ["/api/transactions/filtered", statusFilter],
    () =>
      api.getTransactionsFiltered({
        limit: 100,
        offset: 0,
        status: statusFilter || undefined,
      }),
    { refreshInterval: 30000 },
  );

  const txs: Tx[] = Array.isArray(transactions) ? transactions : [];

  const counts = useMemo(() => {
    const map: Record<string, number> = { "": txs.length, confirmed: 0, pending: 0, sent: 0, rejected: 0 };
    txs.forEach((tx) => {
      const s = (tx.status ?? "").toLowerCase();
      if (s in map) map[s]++;
    });
    return map;
  }, [txs]);

  function handleExport() {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      window.open(`${API_BASE}/export/transactions/csv?${params}`, "_blank");
    } finally {
      setTimeout(() => setExporting(false), 600);
    }
  }

  return (
    <>
      <Header title={t("title")} />

      <div className="px-4 sm:px-6 lg:px-10 py-8 space-y-6">
        {/* Top bar */}
        <div className="flex items-end justify-between gap-4 flex-wrap">
          <div>
            <Eyebrow dash>Транзакции</Eyebrow>
            <h2 className="mt-2 text-[24px] sm:text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {txs.length > 0 ? `${txs.length} записей` : "Нет записей"}
            </h2>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="secondary" size="md" onClick={handleExport} disabled={exporting || isLoading || txs.length === 0} loading={exporting}>
              <Icon icon="solar:download-linear" className="text-[15px]" />
              Экспорт CSV
            </Button>
            <Button variant="primary" size="md" onClick={() => router.push("/transactions/new")}>
              <Icon icon="solar:add-circle-linear" className="text-[15px]" />
              Новая транзакция
            </Button>
          </div>
        </div>

        {/* Filter chips */}
        <div className="flex gap-1.5 flex-wrap">
          {STATUS_OPTIONS.map((opt) => {
            const active = statusFilter === opt.value;
            const count = counts[opt.value] ?? 0;
            return (
              <button
                key={opt.value || "all"}
                type="button"
                onClick={() => setStatusFilter(opt.value)}
                className={cn(
                  "h-8 inline-flex items-center gap-2 px-3 border font-mono text-[11px] tracking-[0.04em] transition-colors",
                  active
                    ? "bg-foreground text-background border-foreground"
                    : "bg-card text-muted-foreground border-border hover:border-strong hover:text-foreground",
                )}
              >
                {opt.label}
                <span className={cn("text-[10px]", active ? "text-background/60" : "text-faint")}>
                  · {count}
                </span>
              </button>
            );
          })}
        </div>

        {error && (
          <div className="border border-destructive/40 bg-destructive/5 p-4 text-[13px] text-destructive">
            Не удалось загрузить транзакции.
          </div>
        )}

        {/* Table */}
        <div className="border border-border bg-card overflow-x-auto">
          <table className="w-full text-[12px] border-collapse">
            <thead>
              <tr className="border-b border-border text-left">
                <Th className="pl-5">Хэш</Th>
                <Th>Статус</Th>
                <Th>Кошелёк</Th>
                <Th>Получатель</Th>
                <Th>Токен</Th>
                <Th className="text-right">Сумма</Th>
                <Th className="text-right pr-5">Время</Th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} className="px-5 py-12 text-center text-muted-foreground">Загрузка…</td></tr>
              ) : txs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-16">
                    <div className="flex flex-col items-center text-center">
                      <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mb-3">
                        <Icon icon="solar:transfer-horizontal-linear" className="text-2xl text-muted-foreground" />
                      </div>
                      <p className="text-[14px] font-medium text-foreground mb-1">Транзакций не найдено</p>
                      <p className="text-[12px] text-muted-foreground mb-4 max-w-md">
                        Здесь появятся все исходящие, входящие и запланированные транзакции по вашим кошелькам — с историей подписей и статусом синхронизации с блокчейном.
                      </p>
                      <Button variant="secondary" size="sm" onClick={() => router.push("/transactions/new")}>
                        <Icon icon="solar:add-circle-linear" className="text-[14px]" />
                        Новая транзакция
                      </Button>
                    </div>
                  </td>
                </tr>
              ) : (
                txs.map((tx) => {
                  const kind = (tx.status ?? "").toLowerCase() as any;
                  const dest = tx.to_address || tx.to_addr || "—";
                  const amount = tx.amount_decimal ?? tx.value ?? "—";
                  const STATUS_RU: Record<string, string> = {
                    confirmed: "Подтверждена",
                    pending:   "Ожидает",
                    sent:      "Отправлена",
                    rejected:  "Отклонена",
                    failed:    "Ошибка",
                    completed: "Завершена",
                    cancelled: "Отменена",
                  };
                  const statusLabel = STATUS_RU[kind] ?? tx.status ?? "—";
                  return (
                    <tr key={tx.tx_unid ?? tx.unid ?? tx.id} className="border-b border-border last:border-b-0 hover:bg-muted/40">
                      <td className="pl-5 py-3">
                        <Link
                          href={`/transactions/${tx.tx_unid ?? tx.unid ?? ""}`}
                          className="text-foreground hover:text-primary"
                          title={tx.tx_hash ?? tx.tx_unid ?? tx.unid ?? undefined}
                        >
                          <Mono truncate startChars={8} endChars={4}>{tx.tx_hash ?? tx.tx_unid ?? tx.unid ?? "—"}</Mono>
                        </Link>
                      </td>
                      <td className="px-3 py-3"><StatusPill kind={kind} label={statusLabel} /></td>
                      <td className="px-3 py-3 text-foreground" title={tx.wallet_name ?? undefined}>
                        <span className="text-[12px] font-mono">
                          {formatWalletDisplayName({
                            name: tx.wallet_name ?? null,
                            wallet_name: tx.wallet_name ?? null,
                            network: tx.network ?? null,
                          })}
                        </span>
                      </td>
                      <td className="px-3 py-3"><Mono truncate>{dest}</Mono></td>
                      <td className="px-3 py-3"><Badge variant="outline">{tokenSymbol(tx)}</Badge></td>
                      <td className="px-3 py-3 text-right text-foreground tabular">{String(amount)}</td>
                      <td className="pr-5 py-3 text-right"><Mono size="xs" className="text-faint">{formatTime(tx.created_at)}</Mono></td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={`px-3 py-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint font-normal ${className}`}>
      {children}
    </th>
  );
}
