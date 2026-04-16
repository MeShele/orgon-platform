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
  available: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-400" },
  pending: { bg: "bg-yellow-100 dark:bg-yellow-900/30", text: "text-yellow-700 dark:text-yellow-400" },
  generating: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-400" },
  error: { bg: "bg-red-100 dark:bg-red-900/30", text: "text-red-700 dark:text-red-400" },
};

const typeBadge: Record<string, { bg: string; text: string; icon: string }> = {
  financial: { bg: "bg-indigo-100 dark:bg-indigo-900/30", text: "text-indigo-700 dark:text-indigo-400", icon: "solar:chart-bold" },
  compliance: { bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-400", icon: "solar:shield-check-bold" },
  tax: { bg: "bg-emerald-100 dark:bg-emerald-900/30", text: "text-emerald-700 dark:text-emerald-400", icon: "solar:document-text-bold" },
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
                <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 p-2.5">
                  <Icon icon="solar:document-bold" className="text-xl text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{reports.length}</p>
                  <p className="text-xs text-slate-500">Всего отчётов</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-green-100 dark:bg-green-900/30 p-2.5">
                  <Icon icon="solar:check-circle-bold" className="text-xl text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{reports.filter(r => r.status === "available").length}</p>
                  <p className="text-xs text-slate-500">Готовы к скачиванию</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-amber-100 dark:bg-amber-900/30 p-2.5">
                  <Icon icon="solar:clock-circle-bold" className="text-xl text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">{reports.filter(r => r.status === "pending" || r.status === "generating").length}</p>
                  <p className="text-xs text-slate-500">В обработке</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {isLoading && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:refresh-linear" className="mx-auto text-3xl text-slate-400 animate-spin mb-3" />
              <p className="text-sm text-slate-500">Загрузка отчётов...</p>
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
                          <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 p-1.5">
                            <Icon icon={type.icon} className="text-sm text-indigo-600 dark:text-indigo-400" />
                          </div>
                          <p className="text-sm font-medium text-slate-900 dark:text-white">{r.title || r.id}</p>
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
                          <button className="inline-flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
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
                    <thead className="border-b border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-900/50">
                      <tr>
                        <th className="px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Название</th>
                        <th className="px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Тип</th>
                        <th className="px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Статус</th>
                        <th className="px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Дата</th>
                        <th className="px-4 py-3 text-xs font-medium text-slate-500 dark:text-slate-400">Действие</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {reports.map((r) => {
                        const type = typeBadge[r.type || ""] || typeBadge.financial;
                        const status = statusBadge[r.status || ""] || statusBadge.pending;
                        return (
                          <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-3">
                                <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 p-2">
                                  <Icon icon={type.icon} className="text-base text-indigo-600 dark:text-indigo-400" />
                                </div>
                                <p className="text-sm font-medium text-slate-900 dark:text-white">{r.title || r.id}</p>
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
                            <td className="px-4 py-3 text-xs text-slate-500 dark:text-slate-400">
                              {r.created_at ? new Date(r.created_at).toLocaleDateString('ru-RU') : "—"}
                            </td>
                            <td className="px-4 py-3">
                              {r.status === "available" && (
                                <button className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 px-3 py-1.5 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-colors">
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
              <Icon icon="solar:document-text-linear" className="mx-auto text-5xl text-slate-300 dark:text-slate-600 mb-4" />
              <h2 className="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">Нет отчётов</h2>
              <p className="text-sm text-slate-500">Отчёты ещё не были сгенерированы</p>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
