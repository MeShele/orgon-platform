"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR from "swr";

interface UserProfile {
  id: number;
  email: string;
  full_name?: string;
  role: string;
  is_active: boolean;
  created_at: string;
  last_login_at?: string;
}

interface Session {
  id: number;
  user_id: number;
  ip_address: string;
  user_agent: string;
  created_at: string;
  last_active: string;
  is_current?: boolean;
}

const roleBadge: Record<string, { bg: string; text: string; label: string }> = {
  admin: { bg: "bg-red-100 dark:bg-red-900/30", text: "text-red-700 dark:text-red-400", label: "Администратор" },
  signer: { bg: "bg-amber-100 dark:bg-amber-900/30", text: "text-amber-700 dark:text-amber-400", label: "Подписант" },
  viewer: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-400", label: "Наблюдатель" },
  super_admin: { bg: "bg-purple-100 dark:bg-purple-900/30", text: "text-purple-700 dark:text-purple-400", label: "Суперадмин" },
};

export default function ProfilePage() {
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState<{ type: "error" | "success"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const { data: profile, isLoading } = useSWR<UserProfile>(
    "/api/auth/me",
    () => api.get("/api/auth/me")
  );

  const { data: sessions } = useSWR<Session[]>(
    "/api/users/me/sessions",
    () => api.getUserSessions().catch(() => [])
  );

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);

    if (newPassword !== confirmPassword) {
      setPasswordMsg({ type: "error", text: "Пароли не совпадают" });
      return;
    }
    if (newPassword.length < 8) {
      setPasswordMsg({ type: "error", text: "Пароль должен быть не менее 8 символов" });
      return;
    }

    setSaving(true);
    try {
      await api.changePassword(currentPassword, newPassword);
      setPasswordMsg({ type: "success", text: "Пароль успешно изменён" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowPasswordForm(false);
    } catch (err: any) {
      setPasswordMsg({ type: "error", text: err.message || "Не удалось сменить пароль" });
    } finally {
      setSaving(false);
    }
  };

  const handleRevokeSession = async (sessionId: number) => {
    if (!confirm("Завершить эту сессию?")) return;
    try {
      await api.revokeSession(sessionId);
    } catch (err) {
      console.error("Failed to revoke session:", err);
    }
  };

  const badge = roleBadge[profile?.role || "viewer"] || roleBadge.viewer;

  return (
    <>
      <Header title="Профиль" />
      <div className={pageLayout.container}>
        {isLoading && (
          <Card>
            <div className="p-8 text-center">
              <Icon icon="solar:refresh-linear" className="mx-auto text-3xl text-slate-400 animate-spin mb-3" />
              <p className="text-sm text-slate-500">Загрузка профиля...</p>
            </div>
          </Card>
        )}

        {profile && (
          <>
            {/* Информация о пользователе */}
            <Card>
              <div className="p-4 sm:p-6">
                <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                  <div className="flex-shrink-0 w-16 h-16 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                    <span className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                      {(profile.full_name || profile.email)[0].toUpperCase()}
                    </span>
                  </div>
                  <div className="flex-1">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
                      {profile.full_name || "—"}
                    </h2>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{profile.email}</p>
                    <div className="mt-2">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.bg} ${badge.text}`}>
                        {badge.label}
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-slate-500 dark:text-slate-400 sm:text-right">
                    <p>Аккаунт создан</p>
                    <p className="font-medium text-slate-900 dark:text-white">
                      {new Date(profile.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </p>
                  </div>
                </div>
              </div>
            </Card>

            {/* Детали — мобильные карточки + десктопная таблица */}
            <div className={pageLayout.grid.cols2}>
              <Card>
                <div className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 p-2">
                      <Icon icon="solar:letter-bold" className="text-base text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Email</p>
                      <p className="text-sm font-medium text-slate-900 dark:text-white">{profile.email}</p>
                    </div>
                  </div>
                </div>
              </Card>
              <Card>
                <div className="p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="rounded-lg bg-green-100 dark:bg-green-900/30 p-2">
                      <Icon icon="solar:login-bold" className="text-base text-green-600 dark:text-green-400" />
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Последний вход</p>
                      <p className="text-sm font-medium text-slate-900 dark:text-white">
                        {profile.last_login_at
                          ? new Date(profile.last_login_at).toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                          : "—"}
                      </p>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Смена пароля */}
            <Card>
              <div className="p-4 sm:p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-slate-900 dark:text-white">Безопасность</h3>
                    <p className="text-sm text-slate-500 mt-1">Управление паролем и настройками безопасности</p>
                  </div>
                  <button
                    onClick={() => setShowPasswordForm(!showPasswordForm)}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                  >
                    <Icon icon="solar:key-linear" />
                    {showPasswordForm ? "Отмена" : "Сменить пароль"}
                  </button>
                </div>

                {passwordMsg && (
                  <div className={`mt-4 ${passwordMsg.type === "error" ? pageLayout.error : pageLayout.success}`}>
                    {passwordMsg.text}
                  </div>
                )}

                {showPasswordForm && (
                  <form onSubmit={handlePasswordChange} className="mt-4 space-y-4 max-w-md">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Текущий пароль</label>
                      <input
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        required
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Новый пароль</label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        required
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Подтверждение пароля</label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-900 dark:text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none"
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={saving}
                      className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                    >
                      {saving && <Icon icon="solar:refresh-linear" className="animate-spin" />}
                      Сохранить
                    </button>
                  </form>
                )}
              </div>
            </Card>

            {/* Активные сессии */}
            {sessions && sessions.length > 0 && (
              <Card>
                <div className="p-4 sm:p-6">
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white mb-4">Активные сессии</h3>
                  <div className="space-y-3">
                    {sessions.map((s) => (
                      <div key={s.id} className="flex items-start justify-between rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 p-3">
                        <div className="flex items-center gap-3">
                          <Icon icon="solar:monitor-linear" className="text-xl text-slate-400" />
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-slate-900 dark:text-white">
                                {s.user_agent?.includes("Mobile") ? "Мобильное устройство" : "Десктоп"}
                              </span>
                              {s.is_current && (
                                <span className="rounded-full bg-green-100 dark:bg-green-900/30 px-2 py-0.5 text-[10px] font-medium text-green-700 dark:text-green-400">
                                  Текущая
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-500">{s.ip_address} • Последняя активность: {new Date(s.last_active).toLocaleString('ru-RU')}</p>
                          </div>
                        </div>
                        {!s.is_current && (
                          <button
                            onClick={() => handleRevokeSession(s.id)}
                            className="text-xs text-red-600 dark:text-red-400 hover:underline"
                          >
                            Завершить
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </>
  );
}
