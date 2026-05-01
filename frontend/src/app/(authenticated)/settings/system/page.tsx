"use client";

// Live system diagnostics — admin-only page, real data, no mocks.
// Polls /api/health/detailed and /api/dashboard/stats on a 30s interval.
// Designed as a self-check tool: glance at this page → know if Safina,
// Postgres and the Safina-sync cache are actually alive.

import useSWR from "swr";
import { useMemo } from "react";
import { Icon } from "@/lib/icons";
import { Eyebrow, Mono } from "@/components/ui/primitives";
import { Badge } from "@/components/ui/Badge";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ServiceState {
  status?: string;
  reachable?: boolean;
  configured?: boolean;
  last_sync?: string | null;
  stats?: {
    networks_age_seconds?: number;
    networks_fresh?: boolean;
    networks_count?: number;
    tokens_info_age_seconds?: number;
    tokens_info_fresh?: boolean;
    tokens_info_count?: number;
  };
}

interface DetailedHealth {
  status?: string;
  timestamp?: string;
  version?: string;
  services?: {
    database?: ServiceState;
    safina_api?: ServiceState;
    cache?: ServiceState;
    telegram?: ServiceState;
    asagent_bridge?: ServiceState;
  };
}

interface Stats {
  total_wallets?: number;
  transactions_24h?: number;
  pending_signatures?: number;
  networks_active?: number;
  last_sync?: string | null;
}

interface Wallet {
  my_unid?: string;
  name?: string;
  network?: number;
  info?: string | null;
}

interface Tx {
  safina_id?: number | null;
  unid?: string | null;
  status?: string;
  token_name?: string | null;
  value?: string | number;
  to_addr?: string;
}

const TONE: Record<string, "success" | "warning" | "destructive" | "muted"> = {
  healthy:        "success",
  ok:             "success",
  active:         "success",
  not_configured: "muted",
  warning:        "warning",
  error:          "destructive",
  failed:         "destructive",
  unknown:        "muted",
};

function StatusDot({ tone }: { tone: "success" | "warning" | "destructive" | "muted" }) {
  return (
    <span
      className={cn(
        "inline-block w-2 h-2 rounded-full",
        tone === "success" && "bg-success",
        tone === "warning" && "bg-warning",
        tone === "destructive" && "bg-destructive",
        tone === "muted" && "bg-muted-foreground",
      )}
      aria-hidden
    />
  );
}

function fmtAge(seconds?: number): string {
  if (typeof seconds !== "number") return "—";
  if (seconds < 60) return `${seconds}с`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}м`;
  return `${Math.floor(seconds / 3600)}ч ${Math.floor((seconds % 3600) / 60)}м`;
}

function fmtTime(iso?: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function explorerUrl(addr: string): string | null {
  if (!addr) return null;
  if (addr.startsWith("T") && addr.length >= 32) return `https://tronscan.org/#/address/${addr}`;
  if (addr.startsWith("0x") && addr.length === 42) return `https://etherscan.io/address/${addr}`;
  if (addr.startsWith("bc1") || (addr.length >= 26 && /^[13]/.test(addr))) return `https://www.blockchain.com/btc/address/${addr}`;
  return null;
}

export default function SystemSettingsPage() {
  const { data: health, isLoading: healthLoading, mutate: refetchHealth } = useSWR<DetailedHealth>(
    "/api/health/detailed",
    () => fetch("/api/health/detailed", { credentials: "include" }).then((r) => r.json()),
    { refreshInterval: 30_000 },
  );

  const { data: stats } = useSWR<Stats>(
    "/api/dashboard/stats",
    api.getDashboardStats,
    { refreshInterval: 30_000 },
  );

  // Pull a sample wallet + recent tx so the page can SHOW concrete
  // Safina-side identifiers (UNID, safina_id) — the strongest "this is
  // really live" signal.
  const { data: sampleWallets } = useSWR<Wallet[]>(
    "/api/wallets?limit=1",
    () => fetch("/api/wallets?limit=1", { credentials: "include" }).then((r) => r.json()),
  );
  const { data: sampleTxs } = useSWR<Tx[]>(
    "/api/transactions?limit=1",
    () => fetch("/api/transactions?limit=1", { credentials: "include" }).then((r) => r.json()),
  );

  const services = health?.services;
  const overallTone: "success" | "warning" | "destructive" = useMemo(() => {
    if (!services) return "warning";
    const isDown = (s?: ServiceState) =>
      s?.status && !["healthy", "ok", "active", "not_configured"].includes(s.status);
    if (isDown(services.database) || isDown(services.safina_api)) return "destructive";
    if (services.safina_api?.reachable === false) return "destructive";
    return "success";
  }, [services]);

  const sampleWallet = sampleWallets?.[0];
  const sampleTx = sampleTxs?.[0];

  return (
    <div className="space-y-8 p-4 sm:p-6 lg:p-10">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <Eyebrow dash tone="primary">Состояние системы</Eyebrow>
          <h1 className="mt-3 text-[28px] font-medium tracking-[-0.02em] text-foreground flex items-center gap-3">
            <StatusDot tone={overallTone} />
            {overallTone === "success" && "Все сервисы работают"}
            {overallTone === "warning" && "Загрузка…"}
            {overallTone === "destructive" && "Один или больше сервисов не отвечают"}
          </h1>
          <p className="mt-2 text-[13px] text-muted-foreground">
            Опрос каждые 30 секунд · последняя проверка <Mono size="xs">{fmtTime(health?.timestamp)}</Mono>
          </p>
        </div>
        <button
          onClick={() => refetchHealth()}
          disabled={healthLoading}
          className="inline-flex items-center gap-2 px-3 h-9 border border-border text-[13px] hover:bg-muted transition-colors disabled:opacity-50"
        >
          <Icon icon="solar:refresh-linear" className={cn("text-[14px]", healthLoading && "animate-spin")} />
          Обновить
        </button>
      </div>

      {/* Services grid */}
      <section>
        <Eyebrow className="mb-4">Сервисы</Eyebrow>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border border border-border">
          <ServiceCard
            title="Postgres (БД ORGON)"
            icon="solar:database-bold"
            state={services?.database}
            description="Канонический schema, RLS активен, audit-триггеры"
          />
          <ServiceCard
            title="Safina Pay API"
            icon="solar:link-circle-bold"
            state={services?.safina_api}
            description="my.safina.pro/ece/ — multi-sig custody backend"
            extraBadge={
              services?.safina_api?.reachable
                ? <Badge variant="green">reachable</Badge>
                : services?.safina_api ? <Badge variant="red">unreachable</Badge> : null
            }
          />
          <ServiceCard
            title="Cache (networks + tokens)"
            icon="solar:layers-bold"
            state={services?.cache}
            description={`networks: ${services?.cache?.stats?.networks_count ?? "—"} · tokens: ${services?.cache?.stats?.tokens_info_count ?? "—"} · возраст ${fmtAge(services?.cache?.stats?.networks_age_seconds)}`}
          />
          <ServiceCard
            title="Telegram уведомления"
            icon="solar:plain-bold"
            state={services?.telegram}
            description="Опционально — настраивается через TELEGRAM_BOT_TOKEN"
          />
          <ServiceCard
            title="ASagent bridge"
            icon="solar:server-square-bold"
            state={services?.asagent_bridge}
            description="Опционально — outbound webhook bridge"
          />
          <div className="bg-card p-5 flex flex-col justify-center">
            <Eyebrow tone="muted">Версия</Eyebrow>
            <Mono size="sm" className="mt-1 text-foreground">v{health?.version ?? "—"}</Mono>
          </div>
        </div>
      </section>

      {/* Live KPI */}
      <section>
        <Eyebrow className="mb-4">Что синкается прямо сейчас</Eyebrow>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-border border border-border">
          <KpiCard label="Кошельков" value={stats?.total_wallets ?? "—"} icon="solar:wallet-bold" hint="из Safina" />
          <KpiCard label="Активных сетей" value={stats?.networks_active ?? "—"} icon="solar:global-bold" hint="из Safina" />
          <KpiCard label="Транзакций 24ч" value={stats?.transactions_24h ?? "—"} icon="solar:transfer-horizontal-bold" />
          <KpiCard label="Ожидают подписи" value={stats?.pending_signatures ?? "—"} icon="solar:pen-bold" />
        </div>
      </section>

      {/* Safina proof card */}
      <section>
        <Eyebrow className="mb-4">Маркеры Safina (доказательство что это не stub)</Eyebrow>
        <div className="border border-border bg-card p-6 space-y-5">
          <p className="text-[13px] text-muted-foreground">
            Stub-режим вернул бы либо UUID4 в идентификаторах, либо вообще не отвечал на /api/health/safina. Ниже — реальные маркеры из Safina test-аккаунта:
          </p>

          {/* Sample wallet */}
          {sampleWallet ? (
            <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 pt-4 border-t border-border">
              <div className="text-[12px] text-muted-foreground sm:w-44 shrink-0">UNID кошелька (16-байт hex Safina-формата)</div>
              <Mono size="sm" className="text-foreground break-all">
                {sampleWallet.my_unid ?? sampleWallet.name}
              </Mono>
              {sampleWallet.info && (
                <span className="text-[12px] text-muted-foreground">«{sampleWallet.info}»</span>
              )}
            </div>
          ) : (
            <div className="text-[12px] text-muted-foreground italic pt-4 border-t border-border">Загружаем кошельки…</div>
          )}

          {/* Sample tx */}
          {sampleTx ? (
            <>
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6 pt-4 border-t border-border">
                <div className="text-[12px] text-muted-foreground sm:w-44 shrink-0">FK на запись в БД Safina</div>
                <Mono size="sm" className="text-foreground">safina_id = {sampleTx.safina_id ?? "—"}</Mono>
                <Badge variant="outline">{sampleTx.status ?? "—"}</Badge>
                {sampleTx.token_name && (
                  <span className="text-[12px] text-muted-foreground">
                    {sampleTx.value} {sampleTx.token_name}
                  </span>
                )}
              </div>

              {sampleTx.to_addr && (
                <div className="flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-6 pt-4 border-t border-border">
                  <div className="text-[12px] text-muted-foreground sm:w-44 shrink-0">Получатель на блокчейне</div>
                  <div className="min-w-0 flex-1 space-y-1">
                    <Mono size="sm" className="text-foreground break-all block">{sampleTx.to_addr}</Mono>
                    {explorerUrl(sampleTx.to_addr) && (
                      <a
                        href={explorerUrl(sampleTx.to_addr)!}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-[12px] text-primary hover:underline"
                      >
                        Открыть в block explorer
                        <Icon icon="solar:arrow-right-up-linear" className="text-[12px]" />
                      </a>
                    )}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-[12px] text-muted-foreground italic pt-4 border-t border-border">
              Транзакций пока нет — Safina test-аккаунт пуст. Создайте первую через /transactions/new чтобы увидеть safina_id.
            </div>
          )}
        </div>
      </section>

      {/* Quick links */}
      <section className="text-[12px] text-muted-foreground">
        <p>
          Документация API:{" "}
          <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">/api/docs (Swagger UI)</a>
          {" · "}
          <a href="/api/redoc" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">/api/redoc</a>
          {" · "}
          скрипт для CTO-аудитории: <Mono size="xs">scripts/safina-proof.sh</Mono>
        </p>
      </section>
    </div>
  );
}

function ServiceCard({
  title,
  icon,
  state,
  description,
  extraBadge,
}: {
  title: string;
  icon: string;
  state?: ServiceState;
  description?: string;
  extraBadge?: React.ReactNode;
}) {
  const status = state?.status ?? "unknown";
  const tone = TONE[status] ?? "muted";
  return (
    <div className="bg-card p-5 flex flex-col">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <Icon icon={icon} className="text-[18px] text-muted-foreground shrink-0" />
          <h3 className="text-[14px] font-medium text-foreground truncate">{title}</h3>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <StatusDot tone={tone} />
          <Mono size="xs" className="text-muted-foreground uppercase">{status}</Mono>
        </div>
      </div>
      {description && <p className="mt-2 text-[12px] text-muted-foreground">{description}</p>}
      {extraBadge && <div className="mt-3">{extraBadge}</div>}
    </div>
  );
}

function KpiCard({
  label,
  value,
  icon,
  hint,
}: {
  label: string;
  value: number | string;
  icon: string;
  hint?: string;
}) {
  return (
    <div className="bg-card p-5">
      <div className="flex items-center gap-2">
        <Icon icon={icon} className="text-[16px] text-primary" />
        <Eyebrow tone="muted">{label}</Eyebrow>
      </div>
      <div className="mt-3 text-[28px] font-medium tabular text-foreground">{String(value)}</div>
      {hint && <Mono size="xs" className="mt-1 block text-muted-foreground">{hint}</Mono>}
    </div>
  );
}
