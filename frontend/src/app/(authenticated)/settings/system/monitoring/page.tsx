"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout, badgeStyles } from "@/lib/page-layout";

export default function MonitoringPage() {
  const { data: health, error: healthErr, isLoading: healthLoading } = useSWR(
    "/api/monitoring/health", api.getMonitoringHealth, { refreshInterval: 30000 }
  );
  const { data: metrics, error: metricsErr, isLoading: metricsLoading } = useSWR(
    "/api/monitoring/metrics", api.getMonitoringMetrics, { refreshInterval: 30000 }
  );

  const [lastRefresh, setLastRefresh] = useState(new Date());
  useEffect(() => {
    const interval = setInterval(() => setLastRefresh(new Date()), 30000);
    return () => clearInterval(interval);
  }, []);

  const isLoading = healthLoading || metricsLoading;
  const hasError = healthErr || metricsErr;

  const statusColor = (ok: boolean) =>
    ok ? badgeStyles.variants.green : badgeStyles.variants.red;
  const statusText = (ok: boolean) => (ok ? "Работает" : "Ошибка");

  const services = health
    ? [
        { name: "База данных", key: "database", icon: "solar:database-bold" },
        { name: "Redis", key: "redis", icon: "solar:server-square-bold" },
        { name: "Safina API", key: "safina", icon: "solar:shield-check-bold" },
      ].map((s) => ({
        ...s,
        ok: health[s.key]?.status === "ok" || health[s.key]?.status === "healthy" || health[s.key] === true,
      }))
    : [];

  return (
    <>
      <Header title="Мониторинг системы" />
      <div className={pageLayout.container}>
        {hasError && <div className={pageLayout.error}>Не удалось загрузить данные мониторинга</div>}
        {isLoading && <div className={pageLayout.loading}><LoadingSpinner /></div>}

        <p className={pageLayout.header.subtitle}>
          Последнее обновление: {lastRefresh.toLocaleTimeString("ru-RU")} · Авто-обновление каждые 30 сек
        </p>

        {/* Overall Status */}
        {health && (
          <div className="rounded-xl border border-border bg-card p-5 dark:border-border dark:bg-card">
            <div className="flex items-center gap-3 mb-4">
              <Icon icon="solar:heart-pulse-bold" className="text-2xl text-primary" />
              <h2 className="text-lg font-bold text-foreground">Статус сервисов</h2>
              <span className={`${badgeStyles.default} ${statusColor(health.status === "ok" || health.status === "healthy")}`}>
                {health.status === "ok" || health.status === "healthy" ? "Всё работает" : "Есть проблемы"}
              </span>
            </div>
            <div className={pageLayout.grid.cols3}>
              {services.map((s) => (
                <Card key={s.key}>
                  <div className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon icon={s.icon} className="text-xl text-muted-foreground" />
                      <span className="font-medium text-foreground">{s.name}</span>
                    </div>
                    <span className={`${badgeStyles.default} ${statusColor(s.ok)}`}>
                      {statusText(s.ok)}
                    </span>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Metrics */}
        {metrics && (
          <div className="rounded-xl border border-border bg-card p-5 dark:border-border dark:bg-card">
            <div className="flex items-center gap-3 mb-4">
              <Icon icon="solar:chart-bold" className="text-2xl text-primary" />
              <h2 className="text-lg font-bold text-foreground">Метрики</h2>
            </div>
            <div className={pageLayout.stats}>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-muted-foreground">Uptime</div>
                  <div className="mt-1 text-2xl font-semibold text-foreground">
                    {metrics.uptime ? `${Math.floor(metrics.uptime / 3600)}ч ${Math.floor((metrics.uptime % 3600) / 60)}м` : "—"}
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-muted-foreground">CPU</div>
                  <div className="mt-1 text-2xl font-semibold text-foreground">
                    {metrics.cpu_percent != null ? `${metrics.cpu_percent}%` : "—"}
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-muted-foreground">Память</div>
                  <div className="mt-1 text-2xl font-semibold text-foreground">
                    {metrics.memory_mb != null ? `${metrics.memory_mb} МБ` : metrics.memory_percent != null ? `${metrics.memory_percent}%` : "—"}
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="text-sm font-medium text-muted-foreground">Запросов</div>
                  <div className="mt-1 text-2xl font-semibold text-foreground">
                    {metrics.total_requests ?? metrics.requests_total ?? "—"}
                  </div>
                </div>
              </Card>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
