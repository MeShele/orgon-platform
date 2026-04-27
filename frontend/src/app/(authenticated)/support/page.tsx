"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR, { mutate } from "swr";

interface Ticket {
  id: string;
  subject?: string;
  title?: string;
  status?: string;
  priority?: string;
  message?: string;
  created_at?: string;
  updated_at?: string;
}

const statusLabel: Record<string, string> = {
  open: "Открыт",
  in_progress: "В работе",
  closed: "Закрыт",
  resolved: "Решён",
};

const statusBadge: Record<string, string> = {
  open: "bg-success/10 text-success",
  in_progress: "bg-primary/10 text-primary",
  closed: "bg-muted text-muted-foreground",
  resolved: "bg-emerald-100 text-success dark:bg-emerald-900/30 dark:text-emerald-400",
};

const priorityLabel: Record<string, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  urgent: "Срочный",
};

const priorityBadge: Record<string, string> = {
  low: "bg-muted text-muted-foreground",
  medium: "bg-warning/10 text-warning",
  high: "bg-destructive/10 text-destructive",
  urgent: "bg-destructive/15 text-destructive",
};

export default function SupportPage() {
  const [showForm, setShowForm] = useState(false);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [priority, setPriority] = useState("medium");
  const [submitting, setSubmitting] = useState(false);

  const { data: tickets, error, isLoading } = useSWR<Ticket[]>(
    "/api/support/tickets",
    async () => {
      const data = await api.get("/api/support/tickets");
      return Array.isArray(data) ? data : data.tickets || data.items || [];
    }
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim()) return;
    setSubmitting(true);
    try {
      await api.post("/api/support/tickets", { subject, message, priority });
      setSubject("");
      setMessage("");
      setPriority("medium");
      setShowForm(false);
      mutate("/api/support/tickets");
    } catch (err) {
      console.error("Failed to create ticket:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Header title="Поддержка" />
      <div className={pageLayout.container}>
        {/* Статистика */}
        <div className={pageLayout.grid.cols3}>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <Icon icon="solar:chat-round-dots-bold" className="text-xl text-primary dark:text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{tickets?.length || 0}</p>
                <p className="text-xs text-muted-foreground">Всего тикетов</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-success/10 p-2.5">
                <Icon icon="solar:chat-round-check-bold" className="text-xl text-success" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{tickets?.filter(t => t.status === "open").length || 0}</p>
                <p className="text-xs text-muted-foreground">Открытых</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-warning/10 p-2.5">
                <Icon icon="solar:clock-circle-bold" className="text-xl text-warning" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{tickets?.filter(t => t.status === "in_progress").length || 0}</p>
                <p className="text-xs text-muted-foreground">В работе</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Кнопка создания + форма */}
        <div className={pageLayout.actionBar}>
          <div />
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-colors"
          >
            <Icon icon={showForm ? "solar:close-circle-bold" : "solar:add-circle-bold"} />
            {showForm ? "Отмена" : "Создать тикет"}
          </button>
        </div>

        {showForm && (
          <Card>
            <form onSubmit={handleSubmit} className="p-4 sm:p-6 space-y-4">
              <h3 className="text-base font-semibold text-foreground">Новый тикет</h3>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Тема</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Опишите проблему кратко"
                  required
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-faint focus:border-primary focus:ring-1 focus:ring-primary/30 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Приоритет</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:border-primary focus:ring-1 focus:ring-primary/30 outline-none"
                >
                  <option value="low">Низкий</option>
                  <option value="medium">Средний</option>
                  <option value="high">Высокий</option>
                  <option value="urgent">Срочный</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">Сообщение</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Подробно опишите вашу проблему..."
                  rows={4}
                  className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground placeholder:text-faint focus:border-primary focus:ring-1 focus:ring-primary/30 outline-none resize-none"
                />
              </div>
              <button
                type="submit"
                disabled={submitting || !subject.trim()}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? (
                  <Icon icon="solar:refresh-linear" className="animate-spin" />
                ) : (
                  <Icon icon="solar:send-bold" />
                )}
                Отправить
              </button>
            </form>
          </Card>
        )}

        {isLoading && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:refresh-linear" className="mx-auto text-3xl text-muted-foreground animate-spin mb-3" />
              <p className="text-sm text-muted-foreground">Загрузка тикетов...</p>
            </div>
          </Card>
        )}

        {error && (
          <div className={pageLayout.error}>Не удалось загрузить тикеты</div>
        )}

        {tickets && tickets.length > 0 && (
          <>
            {/* Мобильные карточки */}
            <div className="space-y-3 md:hidden">
              {tickets.map((t, i) => (
                <Card key={t.id || i}>
                  <div className="p-4">
                    <div className="flex items-start justify-between mb-2">
                      <p className="text-sm font-medium text-foreground">{t.subject || t.title || `Тикет #${t.id}`}</p>
                      <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${statusBadge[t.status || "open"]}`}>
                        {statusLabel[t.status || ""] || t.status || "Открыт"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      {t.priority && (
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${priorityBadge[t.priority] || priorityBadge.medium}`}>
                          {priorityLabel[t.priority] || t.priority}
                        </span>
                      )}
                      <span className="text-[10px] text-muted-foreground">
                        {t.created_at ? new Date(t.created_at).toLocaleDateString('ru-RU') : "—"}
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>

            {/* Десктопная таблица */}
            <div className="hidden md:block">
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border bg-muted/50 dark:border-border dark:bg-card/50">
                      <tr>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Тема</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Приоритет</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Статус</th>
                        <th className="px-4 py-3 text-xs font-medium text-muted-foreground">Создан</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {tickets.map((t, i) => (
                        <tr key={t.id || i} className="hover:bg-muted dark:hover:bg-muted/50 transition-colors">
                          <td className="px-4 py-3">
                            <p className="text-sm font-medium text-foreground">{t.subject || t.title || `Тикет #${t.id}`}</p>
                          </td>
                          <td className="px-4 py-3">
                            {t.priority && (
                              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${priorityBadge[t.priority] || priorityBadge.medium}`}>
                                {priorityLabel[t.priority] || t.priority}
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${statusBadge[t.status || "open"]}`}>
                              {statusLabel[t.status || ""] || t.status || "Открыт"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-muted-foreground">
                            {t.created_at ? new Date(t.created_at).toLocaleDateString('ru-RU') : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>
            </div>
          </>
        )}

        {tickets && tickets.length === 0 && !showForm && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:chat-round-dots-linear" className="mx-auto text-5xl text-faint dark:text-muted-foreground mb-4" />
              <h2 className="text-lg font-semibold text-foreground mb-2">Нет тикетов</h2>
              <p className="text-sm text-muted-foreground mb-4">Создайте тикет, если вам нужна помощь</p>
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-colors"
              >
                <Icon icon="solar:add-circle-bold" />
                Создать тикет
              </button>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}
