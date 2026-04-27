"use client";

import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR from "swr";

interface Report {
  id: string;
  title?: string;
  type?: string;
  status?: string;
  created_at?: string;
  file_url?: string;
}

const statusBadge: Record<string, { bg: string; text: string }> = {
  available: { bg: "bg-success/10", text: "text-success" },
  pending: { bg: "bg-warning/10", text: "text-warning" },
  generating: { bg: "bg-primary/10", text: "text-primary" },
  error: { bg: "bg-destructive/10", text: "text-destructive" },
};

const typeBadge: Record<string, { bg: string; text: string; icon: string }> = {
  financial: { bg: "bg-primary/10", text: "text-primary dark:text-primary", icon: "solar:chart-bold" },
  compliance: { bg: "bg-warning/10", text: "text-warning", icon: "solar:shield-check-bold" },
  tax: { bg: "bg-emerald-100 dark:bg-emerald-900/30", text: "text-success", icon: "solar:document-text-bold" },
};

const statusLabel: Record<string, string> = {
  available: "Готов",
  pending: "Ожидает",
  generating: "Генерируется",
  error: "Ошибка",
};

const typeLabel: Record<string, string> = {
  financial: "Финансовый",
  compliance: "Комплаенс",
  tax: "Налоговый",
};

export default function ReportsPage() {
  const { data: reports, error, isLoading } = useSWR<Report[]>(
    "/api/reports",
    async () => {
      const data = await api.get("/api/reports");
      return Array.isArray(data) ? data : data.reports || data.items || [];
    }
  );

  return (
    <>
      <Header title="Отчёты" />
      <div className={pageLayout.container}>
        {/* Статистика */}
        {reports && reports.length > 0 && (
          <div className={pageLayout.grid.cols3}>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2.5">
                  <Icon icon="solar:document-bold" className="text-xl text-primary dark:text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{reports.length}</p>
                  <p className="text-xs text-muted-foreground">Всего отчётов</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-success/10 p-2.5">
                  <Icon icon="solar:check-circle-bold" className="text-xl text-success" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{reports.filter(r => r.status === "available").length}</p>
                  <p className="text-xs text-muted-foreground">Готовы к скачиванию</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-warning/10 p-2.5">
                  <Icon icon="solar:clock-circle-bold" className="text-xl text-warning" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{reports.filter(r => r.status === "pending" || r.status === "generating").length}</p>
                  <p className="text-xs text-muted-foreground">В обработке</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {isLoading && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:refresh-linear" className="mx-auto text-3xl text-muted-foreground animate-spin mb-3" />
              <p className="text-sm text-muted-foreground">Загрузка отчётов...</p>
            </div>
          </Card>
        )}

        {error && (
          <div className={pageLayout.error}>Не удалось загрузить отчёты</div>
        )}

        {reports && reports.length > 0 && (
          <>
            {/* Мобильные карточки */}
            <div className="space-y-3 md:hidden">
              {reports.map((r) => {
                const type = typeBadge[r.type || ""] || typeBadge.financial;
                const status = statusBadge[r.status || ""] || statusBadge.pending;
                return (
                  <Card key={r.id}>
                    <div className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="rounded-lg bg-primary/10 p-1.5">
                            <Icon icon={type.icon} className="text-sm text-primary dark:text-primary" />
                          </div>
                          <p className="text-sm font-medium text-foreground">{r.title || r.id}</p>
                        </div>
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${status.bg} ${status.text}`}>
                          {statusLabel[r.status || ""] || r.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between mt-3">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${type.bg} ${type.text}`}>
                          {typeLabel[r.type || ""] || r.type}
                        </span>
                        {r.status === "available" && (
                          <button className="inline-flex items-center gap-1 text-xs text-primary dark:text-primary hover:underline">
                            <Icon icon="solar:download-minimalistic-bold" className="text-sm" />
                            Скачать
                          </button>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* Десктопная таблица */}
            <div className="hidden md:block">
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border bg-muted/50 dark:border-border dark:bg-card/50">
                      <tr>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Название</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Тип</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Статус</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Дата</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Действие</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {reports.map((r) => {
                        const type = typeBadge[r.type || ""] || typeBadge.financial;
                        const status = statusBadge[r.status || ""] || statusBadge.pending;
                        return (
                          <tr key={r.id} className="hover:bg-muted dark:hover:bg-muted/50 transition-colors">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <div className="rounded-lg bg-primary/10 p-2">
                                  <Icon icon={type.icon} className="text-base text-primary dark:text-primary" />
                                </div>
                                <p className="text-sm font-medium text-foreground">{r.title || r.id}</p>
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${type.bg} ${type.text}`}>
                                {typeLabel[r.type || ""] || r.type}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${status.bg} ${status.text}`}>
                                {statusLabel[r.status || ""] || r.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-xs text-muted-foreground">
                              {r.created_at ? new Date(r.created_at).toLocaleDateString('ru-RU') : "—"}
                            </td>
                            <td className="px-4 py-3">
                              {r.status === "available" && (
                                <button className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/15 transition-colors">
                                  <Icon icon="solar:download-minimalistic-bold" className="text-sm" />
                                  Скачать
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </>
        )}

        {reports && reports.length === 0 && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:document-text-linear" className="mx-auto text-5xl text-faint dark:text-muted-foreground mb-4" />
              <h2 className="text-lg font-semibold text-foreground mb-2">Нет отчётов</h2>
              <p className="text-sm text-muted-foreground">Отчёты ещё не были сгенерированы</p>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
