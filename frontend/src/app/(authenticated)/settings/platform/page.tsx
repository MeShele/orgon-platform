"use client";

import { useState } from "react";
import useSWR from "swr";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout, buttonStyles, badgeStyles, tableStyles } from "@/lib/page-layout";
import { Card } from "@/components/ui/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";

export default function PlatformSettingsPage() {
  const [notification, setNotification] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [activeTab, setActiveTab] = useState<"general" | "branding" | "domains" | "emails">("general");

  const notify = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Icon icon="solar:settings-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">Настройки платформы</h1>
          <p className="text-sm text-muted-foreground">Глобальные настройки, брендинг, домены</p>
        </div>
      </div>

      {notification && (
        <div className={notification.type === "success" ? pageLayout.success : pageLayout.error}>
          {notification.message}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg border border-border bg-muted p-1 dark:border-border dark:bg-muted">
        {[
          { key: "general", label: "Общие", icon: "solar:settings-linear" },
          { key: "branding", label: "Брендинг", icon: "solar:palette-linear" },
          { key: "domains", label: "Домены", icon: "solar:globe-linear" },
          { key: "emails", label: "Email шаблоны", icon: "solar:letter-linear" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-white text-foreground shadow-sm dark:bg-muted"
                : "text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-primary-foreground"
            }`}
          >
            <Icon icon={tab.icon} />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "general" && <GeneralSection />}
      {activeTab === "branding" && <BrandingSection notify={notify} />}
      {activeTab === "domains" && <DomainsSection notify={notify} />}
      {activeTab === "emails" && <EmailsSection notify={notify} />}
    </div>
  );
}

function GeneralSection() {
  return (
    <div className="space-y-4">
      {[
        { title: "Safina API", desc: "API endpoint, ключи аутентификации, URL вебхуков", icon: "solar:server-bold" },
        { title: "Фиат шлюзы", desc: "Банковские интеграции, платёжные процессоры", icon: "solar:card-bold" },
        { title: "IP Whitelist", desc: "Ограничение доступа по IP", icon: "solar:shield-network-bold" },
      ].map((s) => (
        <div key={s.title} className="rounded-xl border border-border bg-card p-5 dark:border-border dark:bg-card flex items-center gap-4 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer">
          <Icon icon={s.icon} className="text-2xl text-muted-foreground" />
          <div>
            <h3 className="font-semibold text-foreground">{s.title}</h3>
            <p className="text-sm text-muted-foreground">{s.desc}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function BrandingSection({ notify }: { notify: (t: "success" | "error", m: string) => void }) {
  const { data: branding, isLoading, mutate } = useSWR("/api/v1/whitelabel/branding", api.getBranding);
  const [form, setForm] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  // Initialize form from data
  if (branding && !form) {
    setForm({
      company_name: branding.company_name || "",
      logo_url: branding.logo_url || "",
      primary_color: branding.primary_color || "#3B82F6",
      secondary_color: branding.secondary_color || "#6366F1",
    });
  }

  const handleSave = async () => {
    if (!form) return;
    setSaving(true);
    try {
      await api.updateBranding(form);
      notify("success", "Брендинг обновлён");
      mutate();
    } catch (e: any) {
      notify("error", e.message || "Ошибка сохранения");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className={pageLayout.loading}><LoadingSpinner /></div>;

  return (
    <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
      <h3 className="text-lg font-bold text-foreground">Брендинг</h3>
      {form && (
        <>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Название компании</label>
            <input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })}
              className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">URL логотипа</label>
            <input value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
              placeholder="https://..." className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Основной цвет</label>
              <div className="flex gap-2 items-center">
                <input type="color" value={form.primary_color} onChange={(e) => setForm({ ...form, primary_color: e.target.value })}
                  className="w-10 h-10 rounded cursor-pointer" />
                <input value={form.primary_color} onChange={(e) => setForm({ ...form, primary_color: e.target.value })}
                  className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Дополнительный цвет</label>
              <div className="flex gap-2 items-center">
                <input type="color" value={form.secondary_color} onChange={(e) => setForm({ ...form, secondary_color: e.target.value })}
                  className="w-10 h-10 rounded cursor-pointer" />
                <input value={form.secondary_color} onChange={(e) => setForm({ ...form, secondary_color: e.target.value })}
                  className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
              </div>
            </div>
          </div>
          <button onClick={handleSave} disabled={saving} className={buttonStyles.primary}>
            {saving ? "Сохранение..." : "Сохранить"}
          </button>
        </>
      )}
    </div>
  );
}

function DomainsSection({ notify }: { notify: (t: "success" | "error", m: string) => void }) {
  const { data: domains, isLoading, mutate } = useSWR("/api/v1/whitelabel/domains", api.getDomains);
  const [newDomain, setNewDomain] = useState("");
  const [adding, setAdding] = useState(false);

  const handleAdd = async () => {
    if (!newDomain) return;
    setAdding(true);
    try {
      await api.addDomain({ domain: newDomain });
      notify("success", "Домен добавлен");
      setNewDomain("");
      mutate();
    } catch (e: any) {
      notify("error", e.message || "Ошибка");
    } finally {
      setAdding(false);
    }
  };

  const handleVerify = async (id: string) => {
    try {
      await api.verifyDomain(id);
      notify("success", "Верификация запущена");
      mutate();
    } catch (e: any) {
      notify("error", e.message || "Ошибка верификации");
    }
  };

  if (isLoading) return <div className={pageLayout.loading}><LoadingSpinner /></div>;

  return (
    <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
      <h3 className="text-lg font-bold text-foreground">Кастомные домены</h3>
      <div className="flex gap-2">
        <input value={newDomain} onChange={(e) => setNewDomain(e.target.value)} placeholder="example.com"
          className="flex-1 rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
        <button onClick={handleAdd} disabled={adding || !newDomain} className={buttonStyles.primary}>
          {adding ? "..." : "Добавить"}
        </button>
      </div>
      {Array.isArray(domains) && domains.length > 0 && (
        <div className={tableStyles.wrapper}>
          <table className={tableStyles.table}>
            <thead className={tableStyles.thead}>
              <tr>
                <th className={tableStyles.th}>Домен</th>
                <th className={tableStyles.th}>Статус</th>
                <th className={tableStyles.th}></th>
              </tr>
            </thead>
            <tbody className={tableStyles.tbody}>
              {domains.map((d: any) => (
                <tr key={d.id}>
                  <td className={tableStyles.td}>{d.domain}</td>
                  <td className={tableStyles.td}>
                    <span className={`${badgeStyles.default} ${d.verified ? badgeStyles.variants.green : badgeStyles.variants.yellow}`}>
                      {d.verified ? "Верифицирован" : "Ожидает"}
                    </span>
                  </td>
                  <td className={tableStyles.td}>
                    {!d.verified && (
                      <button onClick={() => handleVerify(d.id)} className={buttonStyles.ghost + " text-xs"}>
                        Верифицировать
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function EmailsSection({ notify }: { notify: (t: "success" | "error", m: string) => void }) {
  const { data: templates, isLoading, mutate } = useSWR("/api/v1/whitelabel/email-templates", api.getEmailTemplates);
  const [editing, setEditing] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ subject: string; body: string }>({ subject: "", body: "" });
  const [saving, setSaving] = useState(false);

  const startEdit = (tpl: any) => {
    setEditing(tpl.type);
    setEditForm({ subject: tpl.subject || "", body: tpl.body || "" });
  };

  const handleSave = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      await api.updateEmailTemplate(editing, editForm);
      notify("success", "Шаблон обновлён");
      setEditing(null);
      mutate();
    } catch (e: any) {
      notify("error", e.message || "Ошибка");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) return <div className={pageLayout.loading}><LoadingSpinner /></div>;

  return (
    <div className="rounded-xl border border-border bg-card p-6 dark:border-border dark:bg-card space-y-4">
      <h3 className="text-lg font-bold text-foreground">Email шаблоны</h3>
      {Array.isArray(templates) && templates.map((tpl: any) => (
        <div key={tpl.type} className="rounded-lg border border-border p-4 dark:border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-foreground">{tpl.type}</span>
            <button onClick={() => startEdit(tpl)} className={buttonStyles.ghost + " text-xs"}>
              <Icon icon="solar:pen-linear" /> Редактировать
            </button>
          </div>
          {editing === tpl.type ? (
            <div className="space-y-3">
              <input value={editForm.subject} onChange={(e) => setEditForm({ ...editForm, subject: e.target.value })}
                placeholder="Тема" className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
              <textarea value={editForm.body} onChange={(e) => setEditForm({ ...editForm, body: e.target.value })}
                rows={6} placeholder="Тело письма" className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm dark:bg-muted" />
              <div className="flex gap-2">
                <button onClick={handleSave} disabled={saving} className={buttonStyles.primary + " text-xs"}>
                  {saving ? "..." : "Сохранить"}
                </button>
                <button onClick={() => setEditing(null)} className={buttonStyles.secondary + " text-xs"}>Отмена</button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{tpl.subject || "Не настроено"}</p>
          )}
        </div>
      ))}
    </div>
  );
}
