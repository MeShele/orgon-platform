"use client";

// AML triage list — table + filters + drawer for the /compliance AML tab.
// SWR with 30s polling per ADR-12 (low-velocity AML stream, no WS).

import { useState, useMemo, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import {
  fetchAmlAlerts,
  fetchAmlStats,
  type AmlAlertList as AmlAlertListType,
  type AmlSeverity,
  type AmlStats,
  type AmlStatus,
} from "@/lib/amlAlerts";
import { AmlSeverityBadge, AmlStatusBadge } from "./AmlBadges";
import { AmlAlertDrawer } from "./AmlAlertDrawer";

const STATUS_OPTIONS: { value: AmlStatus | ""; label: string }[] = [
  { value: "", label: "Все" },
  { value: "open", label: "Открытые" },
  { value: "investigating", label: "В работе" },
  { value: "resolved", label: "Решённые" },
  { value: "false_positive", label: "Ложные" },
  { value: "reported", label: "В регулятор" },
];

const SEVERITY_OPTIONS: { value: AmlSeverity | ""; label: string }[] = [
  { value: "", label: "Все" },
  { value: "critical", label: "Критический" },
  { value: "high", label: "Высокий" },
  { value: "medium", label: "Средний" },
  { value: "low", label: "Низкий" },
];

export function AmlAlertList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<AmlStatus | "">("open");
  const [severityFilter, setSeverityFilter] = useState<AmlSeverity | "">("");

  const listKey = useMemo(
    () => ["aml-alerts", statusFilter, severityFilter] as const,
    [statusFilter, severityFilter],
  );

  const { data, error, isLoading, mutate } = useSWR<AmlAlertListType>(
    listKey,
    () => fetchAmlAlerts({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
    }),
    { refreshInterval: 30000, revalidateOnFocus: true },
  );

  const { data: stats, mutate: mutateStats } = useSWR<AmlStats>(
    ["aml-stats"],
    fetchAmlStats,
    { refreshInterval: 30000 },
  );

  const selectedId = searchParams?.get("alert") ?? null;

  const openAlert = useCallback((id: string) => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.set("alert", id);
    router.replace(`?${params.toString()}`, { scroll: false });
  }, [router, searchParams]);

  const closeAlert = useCallback(() => {
    const params = new URLSearchParams(searchParams?.toString() ?? "");
    params.delete("alert");
    const qs = params.toString();
    router.replace(qs ? `?${qs}` : "?", { scroll: false });
  }, [router, searchParams]);

  const refreshAfterMutation = useCallback(() => {
    mutate();
    mutateStats();
  }, [mutate, mutateStats]);

  return (
    <div className="space-y-4">
      {/* KPI cards — render real numbers from /stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Открытых" value={stats.open} icon="solar:shield-warning-bold" tone="warning" />
          <KpiCard label="В работе" value={stats.investigating} icon="solar:clock-circle-bold" tone="primary" />
          <KpiCard label="Решено за 30д" value={stats.resolved_30d} icon="solar:check-circle-bold" tone="success" />
          <KpiCard label="Критических" value={stats.by_severity.critical} icon="solar:danger-triangle-bold" tone="danger" />
        </div>
      )}

      {/* Filter strip */}
      <div className="flex flex-wrap gap-3">
        <Filter
          label="Статус"
          value={statusFilter}
          options={STATUS_OPTIONS}
          onChange={(v) => setStatusFilter(v as AmlStatus | "")}
        />
        <Filter
          label="Severity"
          value={severityFilter}
          options={SEVERITY_OPTIONS}
          onChange={(v) => setSeverityFilter(v as AmlSeverity | "")}
        />
      </div>

      {/* List */}
      <Card>
        <div className="p-0">
          {isLoading && (
            <div className="flex items-center justify-center py-16">
              <Icon icon="svg-spinners:ring-resize" className="text-2xl text-primary" />
            </div>
          )}

          {error && (
            <div className="m-4 rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
              Не удалось загрузить алерты: {error instanceof Error ? error.message : String(error)}
            </div>
          )}

          {!isLoading && !error && data && data.items.length === 0 && (
            <div className="py-16 text-center">
              <Icon icon="solar:shield-check-bold" className="text-4xl text-success mx-auto mb-2" />
              <p className="text-sm text-foreground">Открытых алертов нет — система в чистом режиме</p>
              <p className="text-xs text-muted-foreground mt-1">
                Подозрительная активность не обнаружена.
              </p>
            </div>
          )}

          {!isLoading && !error && data && data.items.length > 0 && (
            <div className="divide-y divide-border">
              {data.items.map((alert) => (
                <button
                  key={alert.id}
                  onClick={() => openAlert(alert.id)}
                  className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors flex items-center gap-3"
                >
                  <div className="flex-shrink-0">
                    <AmlSeverityBadge severity={alert.severity} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground truncate">{alert.description}</p>
                    <p className="text-xs text-muted-foreground">
                      {alert.alert_type} · {new Date(alert.created_at).toLocaleString("ru-RU")}
                      {alert.assigned_to && (
                        <>
                          {" · "}
                          <span title={alert.assigned_to_email ?? undefined}>
                            {alert.assigned_to_name ?? alert.assigned_to_email ?? `user#${alert.assigned_to}`}
                          </span>
                        </>
                      )}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <AmlStatusBadge status={alert.status} />
                  </div>
                  <Icon icon="solar:alt-arrow-right-linear" className="text-muted-foreground" />
                </button>
              ))}
            </div>
          )}
        </div>
      </Card>

      <AmlAlertDrawer
        alertId={selectedId}
        onClose={closeAlert}
        onMutated={refreshAfterMutation}
      />
    </div>
  );
}

function KpiCard({
  label, value, icon, tone,
}: {
  label: string;
  value: number;
  icon: string;
  tone: "warning" | "primary" | "success" | "danger";
}) {
  const TONE: Record<typeof tone, string> = {
    warning: "bg-warning/10 text-warning",
    primary: "bg-primary/10 text-primary",
    success: "bg-success/10 text-success",
    danger: "bg-destructive/10 text-destructive",
  };
  return (
    <Card>
      <div className="p-4 flex items-center gap-3">
        <div className={`rounded-lg p-2.5 ${TONE[tone]}`}>
          <Icon icon={icon} className="text-xl" />
        </div>
        <div>
          <p className="text-2xl font-bold text-foreground">{value}</p>
          <p className="text-xs text-muted-foreground">{label}</p>
        </div>
      </div>
    </Card>
  );
}

function Filter<T extends string>({
  label, value, options, onChange,
}: {
  label: string;
  value: T | "";
  options: { value: T | ""; label: string }[];
  onChange: (v: T | "") => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{label}:</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T | "")}
        className="rounded-lg border border-border bg-card px-3 py-1.5 text-sm text-foreground"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </label>
  );
}
