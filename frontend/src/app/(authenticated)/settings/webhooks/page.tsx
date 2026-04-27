"use client";

import { useState } from "react";
import useSWR from "swr";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout, buttonStyles, badgeStyles, tableStyles } from "@/lib/page-layout";

interface Webhook {
  id: string;
  url: string;
  events: string[];
  status: string;
  created_at: string;
}

export default function WebhooksPage() {
  const [showModal, setShowModal] = useState(false);
  const [newUrl, setNewUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const { data: webhooks, error, isLoading, mutate } = useSWR<Webhook[]>(
    "/api/v1/partner/webhooks",
    api.getWebhooks
  );
  const { data: availableEvents } = useSWR<string[]>(
    "/api/v1/partner/webhooks/events",
    api.getWebhookEvents
  );

  const notify = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleCreate = async () => {
    if (!newUrl || selectedEvents.length === 0) return;
    setCreating(true);
    try {
      await api.createWebhook({ url: newUrl, events: selectedEvents });
      notify("success", "Вебхук создан");
      setShowModal(false);
      setNewUrl("");
      setSelectedEvents([]);
      mutate();
    } catch (e: any) {
      notify("error", e.message || "Ошибка создания");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить вебхук?")) return;
    try {
      await api.deleteWebhook(id);
      notify("success", "Вебхук удалён");
      mutate();
    } catch (e: any) {
      notify("error", e.message || "Ошибка удаления");
    }
  };

  const toggleEvent = (event: string) => {
    setSelectedEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  return (
    <>
      <Header title="Вебхуки" />
      <div className={pageLayout.container}>
        {notification && (
          <div className={notification.type === "success" ? pageLayout.success : pageLayout.error}>
            {notification.message}
          </div>
        )}

        <div className={pageLayout.actionBar}>
          <p className={pageLayout.header.subtitle}>
            Управление вебхуками для получения уведомлений о событиях
          </p>
          <button onClick={() => setShowModal(true)} className={buttonStyles.primary}>
            <Icon icon="solar:add-circle-linear" />
            Добавить вебхук
          </button>
        </div>

        {error && <div className={pageLayout.error}>Не удалось загрузить вебхуки</div>}
        {isLoading && <div className={pageLayout.loading}><LoadingSpinner /></div>}

        {webhooks && webhooks.length === 0 && (
          <div className={pageLayout.empty.wrapper}>
            <Icon icon="solar:link-broken-linear" className={pageLayout.empty.icon} />
            <p className={pageLayout.empty.title}>Нет вебхуков</p>
            <p className={pageLayout.empty.description}>Добавьте вебхук для получения уведомлений</p>
          </div>
        )}

        {webhooks && webhooks.length > 0 && (
          <div className={tableStyles.wrapper}>
            <table className={tableStyles.table}>
              <thead className={tableStyles.thead}>
                <tr>
                  <th className={tableStyles.th}>URL</th>
                  <th className={tableStyles.th}>События</th>
                  <th className={tableStyles.th}>Статус</th>
                  <th className={tableStyles.th}>Создан</th>
                  <th className={tableStyles.th}></th>
                </tr>
              </thead>
              <tbody className={tableStyles.tbody}>
                {webhooks.map((wh) => (
                  <tr key={wh.id}>
                    <td className={tableStyles.td}>
                      <code className="text-xs break-all">{wh.url}</code>
                    </td>
                    <td className={tableStyles.td}>
                      <div className="flex flex-wrap gap-1">
                        {wh.events.map((ev) => (
                          <span key={ev} className={`${badgeStyles.default} ${badgeStyles.variants.blue}`}>
                            {ev}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className={tableStyles.td}>
                      <span className={`${badgeStyles.default} ${wh.status === "active" ? badgeStyles.variants.green : badgeStyles.variants.slate}`}>
                        {wh.status === "active" ? "Активен" : "Отключён"}
                      </span>
                    </td>
                    <td className={tableStyles.tdMuted}>
                      {new Date(wh.created_at).toLocaleDateString("ru-RU")}
                    </td>
                    <td className={tableStyles.td}>
                      <button onClick={() => handleDelete(wh.id)} className={buttonStyles.danger + " !px-2 !py-1 text-xs"}>
                        <Icon icon="solar:trash-bin-trash-linear" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Modal */}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card">
              <h2 className="text-lg font-bold text-foreground mb-4">Новый вебхук</h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1">URL</label>
                  <input
                    type="url"
                    value={newUrl}
                    onChange={(e) => setNewUrl(e.target.value)}
                    placeholder="https://example.com/webhook"
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">События</label>
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                    {(availableEvents || []).map((event) => (
                      <label key={event} className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedEvents.includes(event)}
                          onChange={() => toggleEvent(event)}
                          className="rounded border-border"
                        />
                        {event}
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-6">
                <button onClick={() => setShowModal(false)} className={buttonStyles.secondary}>Отмена</button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !newUrl || selectedEvents.length === 0}
                  className={buttonStyles.primary}
                >
                  {creating ? "Создание..." : "Создать"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
