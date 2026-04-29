"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "@/hooks/useTranslations";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { StatusDot } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { HelpTooltip } from "@/components/common/HelpTooltip";
import { helpContent } from "@/lib/help-content";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";
import clsx from "clsx";

type SettingsSection = 
  | "profile" 
  | "security" 
  | "api-keys" 
  | "notifications" 
  | "theme" 
  | "language" 
  | "limits" 
  | "backup" 
  | "about";

export default function SettingsPage() {
  const t = useTranslations('settings');
  const [activeSection, setActiveSection] = useState<SettingsSection>("profile");
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [safinaHealth, setSafinaHealth] = useState<Record<string, unknown> | null>(null);

  // Profile state
  const [profile, setProfile] = useState({
    fullName: "",
    email: "",
    role: "",
    avatar: "",
  });

  // Security state
  const [security, setSecurity] = useState({
    twoFactorEnabled: false,
    activeSessions: 0,
    lastPasswordChange: "",
  });

  // Notifications state
  const [notifications, setNotifications] = useState({
    emailNotifications: true,
    pushNotifications: false,
    telegramNotifications: false,
    transactionAlerts: true,
    securityAlerts: true,
    weeklyReport: false,
  });

  // Theme state
  const [theme, setTheme] = useState<"light" | "dark" | "auto">("auto");

  // Language state
  const [language, setLanguage] = useState<"en" | "ru" | "ky">("en");

  // Limits state
  const [limits, setLimits] = useState({
    maxWallets: 0,
    maxMonthlyVolume: 0,
    maxTransactionSize: 0,
    usedWallets: 0,
    usedVolume: 0,
  });

  useEffect(() => {
    api.getHealth().then(setHealth).catch(() => {});
    api.getSafinaHealth().then(setSafinaHealth).catch(() => {});
    // Load real profile data
    api.getCurrentUser().then((user: any) => {
      if (user) {
        setProfile({
          fullName: user.full_name || user.username || "",
          email: user.email || "",
          role: user.role || "",
          avatar: user.avatar || "",
        });
        setSecurity(prev => ({
          ...prev,
          twoFactorEnabled: user.twofa_enabled || false,
        }));
      }
    }).catch(() => {});
  }, []);

  const sections = [
    { id: "profile" as SettingsSection, icon: "solar:user-linear", label: t('sections.profile') },
    { id: "security" as SettingsSection, icon: "solar:shield-check-linear", label: t('sections.security') },
    { id: "api-keys" as SettingsSection, icon: "solar:key-linear", label: t('sections.apiKeys') },
    { id: "notifications" as SettingsSection, icon: "solar:bell-linear", label: t('sections.notifications') },
    { id: "theme" as SettingsSection, icon: "solar:palette-linear", label: t('sections.theme') },
    { id: "language" as SettingsSection, icon: "solar:translation-linear", label: t('sections.language') },
    { id: "limits" as SettingsSection, icon: "solar:chart-square-linear", label: t('sections.limits') },
    { id: "backup" as SettingsSection, icon: "solar:download-square-linear", label: t('sections.backup') },
    { id: "about" as SettingsSection, icon: "solar:info-circle-linear", label: t('sections.about') },
  ];

  return (
    <>
      <Header title={t('title')} />

      <div className="p-2 sm:p-4 md:p-6 lg:p-8 space-y-6">
        <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/5 p-4 text-[13px]">
          <Icon icon="solar:info-circle-bold" className="text-warning mt-0.5 shrink-0 text-base" />
          <div className="text-foreground">
            <div className="font-medium">Часть настроек — превью</div>
            <div className="mt-1 text-muted-foreground">
              Рабочие действия живут на профильных страницах:{" "}
              <a className="text-primary underline-offset-4 hover:underline" href="/profile">/profile</a> — смена пароля и сессии,{" "}
              <a className="text-primary underline-offset-4 hover:underline" href="/settings/keys">/settings/keys</a> — EC-ключ подписи Safina,{" "}
              <a className="text-primary underline-offset-4 hover:underline" href="/settings/system/monitoring">/settings/system/monitoring</a> — мониторинг,{" "}
              <a className="text-primary underline-offset-4 hover:underline" href="/settings/webhooks">/settings/webhooks</a> — webhooks.
              Партнёрские API-ключи — раздел ниже, выпуск через админский API.
            </div>
          </div>
        </div>

        {/* Quick navigation grid */}
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
          {[
            { href: "/profile", label: "Профиль", icon: "solar:user-bold", color: "bg-primary/10 text-primary" },
            { href: "/settings", label: "Безопасность (2FA)", icon: "solar:shield-keyhole-bold", color: "bg-success/10 text-success", active: true },
            { href: "/settings/keys", label: "API ключи", icon: "solar:key-bold", color: "bg-muted text-foreground" },
            { href: "/settings/organization", label: "Организация", icon: "solar:buildings-bold", color: "bg-warning/10 text-warning" },
            { href: "/settings/platform", label: "Платформа", icon: "solar:server-bold", color: "bg-primary/10 text-primary dark:text-primary", admin: true },
            { href: "/settings/webhooks", label: "Webhooks", icon: "solar:link-bold", color: "bg-muted text-foreground", admin: true },
            { href: "/settings/system/monitoring", label: "Мониторинг", icon: "solar:monitor-bold", color: "bg-destructive/10 text-destructive", admin: true },
          ].map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 rounded-xl border border-border bg-card p-4 transition-all hover:shadow-md dark:border-border dark:bg-card",
                item.active && "ring-2 ring-primary"
              )}
            >
              <div className={clsx("rounded-lg p-2", item.color)}>
                <Icon icon={item.icon} className="text-lg" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{item.label}</p>
                {item.admin && <span className="text-[10px] text-muted-foreground">admin</span>}
              </div>
            </a>
          ))}
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4 px-2 sm:px-4 md:px-6 lg:px-8 pb-8">
        {/* Left sidebar - Settings menu */}
        <aside className="w-full md:w-64 flex-shrink-0">
          <Card>
            <div className="p-4 space-y-1">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={clsx(
                    "w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                    activeSection === section.id
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:bg-muted dark:text-muted-foreground dark:hover:bg-muted"
                  )}
                >
                  <Icon icon={section.icon} className="text-base" />
                  <span>{section.label}</span>
                </button>
              ))}
            </div>
          </Card>
        </aside>

        {/* Right content - Active section */}
        <main className="flex-1 space-y-4">
          {/* Profile Section */}
          {activeSection === "profile" && (
            <Card>
              <CardHeader
                title={t('profile.title')}
                helpText={helpContent.settings.profile.text}
                helpTips={helpContent.settings.profile.tips}
              />
              <div className="p-4 space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-2xl font-bold">
                    {profile.fullName.charAt(0)}
                  </div>
                  <button
                    type="button"
                    disabled
                    title="В разработке"
                    className="px-4 py-2 text-sm rounded-lg border border-border opacity-50 cursor-not-allowed"
                  >
                    {t('profile.changeAvatar')}
                  </button>
                </div>

                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t('profile.fullName')}
                    </label>
                    <input
                      type="text"
                      value={profile.fullName}
                      onChange={(e) => setProfile({ ...profile, fullName: e.target.value })}
                      className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t('profile.email')}
                    </label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t('profile.role')}
                    </label>
                    <Badge variant="primary">{profile.role}</Badge>
                  </div>
                </div>

                <button
                  type="button"
                  disabled
                  title="В разработке"
                  className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg opacity-50 cursor-not-allowed"
                >
                  {t('profile.saveChanges')} · в разработке
                </button>
              </div>
            </Card>
          )}

          {/* Security Section */}
          {activeSection === "security" && (
            <div className="space-y-4">
              <Card>
                <CardHeader
                  title={t('security.title')}
                  helpText={helpContent.settings.security.text}
                  helpTips={helpContent.settings.security.tips}
                />
                <div className="p-4 space-y-4">
                  <div className="flex items-start gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3 text-[12px] text-foreground">
                    <Icon icon="solar:info-circle-bold" className="text-primary mt-0.5 shrink-0" />
                    <div>
                      Полное управление паролями, 2FA и сессиями — на странице{" "}
                      <a className="text-primary underline-offset-4 hover:underline" href="/profile">/profile</a>.
                      Поля ниже — превью.
                    </div>
                  </div>

                  <div className="flex items-center justify-between opacity-60">
                    <div>
                      <p className="text-sm font-medium text-foreground">{t('security.twoFactor')}</p>
                      <p className="text-xs text-muted-foreground">{t('security.twoFactorDesc')}</p>
                    </div>
                    <button
                      type="button"
                      disabled
                      title="Управляется на /profile"
                      className={clsx(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-not-allowed",
                        security.twoFactorEnabled ? "bg-success" : "bg-muted"
                      )}
                    >
                      <span
                        className={clsx(
                          "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                          security.twoFactorEnabled ? "translate-x-6" : "translate-x-1"
                        )}
                      />
                    </button>
                  </div>

                  <div className="border-t border-border pt-4 opacity-60">
                    <p className="text-sm font-medium text-foreground mb-2">{t('security.changePassword')}</p>
                    <div className="space-y-2">
                      <input
                        type="password"
                        disabled
                        placeholder={t('security.currentPassword')}
                        className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none cursor-not-allowed"
                      />
                      <input
                        type="password"
                        disabled
                        placeholder={t('security.newPassword')}
                        className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none cursor-not-allowed"
                      />
                      <input
                        type="password"
                        disabled
                        placeholder={t('security.confirmPassword')}
                        className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none cursor-not-allowed"
                      />
                      <button
                        type="button"
                        disabled
                        title="Доступно на /profile"
                        className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg opacity-50 cursor-not-allowed"
                      >
                        {t('security.updatePassword')} · на /profile
                      </button>
                    </div>
                  </div>

                  <div className="border-t border-border pt-4 opacity-60">
                    <p className="text-sm font-medium text-foreground mb-2">{t('security.activeSessions')}</p>
                    <p className="text-xs text-muted-foreground">
                      {security.activeSessions} {t('security.activeSessionsCount')}
                    </p>
                    <button
                      type="button"
                      disabled
                      title="Доступно на /profile"
                      className="mt-2 text-xs text-destructive cursor-not-allowed opacity-70"
                    >
                      {t('security.logoutAllSessions')} · на /profile
                    </button>
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* API Keys Section */}
          {activeSection === "api-keys" && (
            <Card>
              <CardHeader
                title={t('apiKeys.title')}
                helpText={helpContent.settings.apiKeys.text}
                helpTips={helpContent.settings.apiKeys.tips}
              />
              <div className="p-4 space-y-4">
                <div className="flex items-start gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3 text-[12px] text-foreground">
                  <Icon icon="solar:info-circle-bold" className="text-primary mt-0.5 shrink-0" />
                  <div className="space-y-2">
                    <div>
                      Партнёрские API-ключи — действие администратора организации.
                      Выпуск, ротация и отзыв доступны через{" "}
                      <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">/api/v1/admin/partners</code>{" "}
                      (роли <span className="font-mono">super_admin</span> /{" "}
                      <span className="font-mono">company_admin</span>).
                    </div>
                    <div className="text-muted-foreground">
                      Если у вас нет админ-роли — напишите на{" "}
                      <a className="text-primary underline-offset-4 hover:underline" href="mailto:support@orgon.asystem.kg">
                        support@orgon.asystem.kg
                      </a>{" "}
                      или владельцу организации, чтобы выпустить ключ для интеграции.
                    </div>
                  </div>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-3 text-[12px] text-muted-foreground">
                  <div className="font-medium text-foreground">Что хранит ключ</div>
                  <ul className="mt-1 list-disc pl-5 space-y-0.5">
                    <li><span className="font-mono">api_key</span> — публичный идентификатор партнёра (виден в логах)</li>
                    <li><span className="font-mono">api_secret</span> — HMAC-секрет, отдаётся ОДИН РАЗ при выпуске/ротации</li>
                    <li>Все запросы партнёра подписываются HMAC + защищены X-Nonce от replay-атак</li>
                  </ul>
                </div>
              </div>
            </Card>
          )}

          {/* Notifications Section */}
          {activeSection === "notifications" && (
            <Card>
              <CardHeader
                title={t('notifications.title')}
                helpText={helpContent.settings.notifications.text}
                helpTips={helpContent.settings.notifications.tips}
              />
              <div className="p-4 space-y-4">
                <div className="flex items-start gap-2 rounded-lg border border-primary/30 bg-primary/5 p-3 text-[12px] text-foreground">
                  <Icon icon="solar:info-circle-bold" className="text-primary mt-0.5 shrink-0" />
                  <div>
                    Настройки уведомлений — превью. Изменения пока не сохраняются.
                    Email-/Telegram-каналы для transaction- и security-событий
                    подключаются командой поддержки по запросу.
                  </div>
                </div>
                {[
                  { key: "emailNotifications" as const, label: t('notifications.email'), desc: t('notifications.emailDesc') },
                  { key: "pushNotifications" as const, label: t('notifications.push'), desc: t('notifications.pushDesc') },
                  { key: "telegramNotifications" as const, label: t('notifications.telegram'), desc: t('notifications.telegramDesc') },
                  { key: "transactionAlerts" as const, label: t('notifications.transactions'), desc: t('notifications.transactionsDesc') },
                  { key: "securityAlerts" as const, label: t('notifications.security'), desc: t('notifications.securityDesc') },
                  { key: "weeklyReport" as const, label: t('notifications.weekly'), desc: t('notifications.weeklyDesc') },
                ].map((item) => (
                  <div key={item.key} className="flex items-center justify-between opacity-60">
                    <div>
                      <p className="text-sm font-medium text-foreground">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.desc}</p>
                    </div>
                    <button
                      type="button"
                      disabled
                      title="Изменения не сохраняются — превью"
                      className={clsx(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-not-allowed",
                        notifications[item.key] ? "bg-success" : "bg-muted"
                      )}
                    >
                      <span
                        className={clsx(
                          "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                          notifications[item.key] ? "translate-x-6" : "translate-x-1"
                        )}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Theme Section */}
          {activeSection === "theme" && (
            <Card>
              <CardHeader
                title={t('theme.title')}
                helpText={helpContent.settings.theme.text}
                helpTips={helpContent.settings.theme.tips}
              />
              <div className="p-4 space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  {(["light", "dark", "auto"] as const).map((themeOption) => (
                    <button
                      key={themeOption}
                      onClick={() => setTheme(themeOption)}
                      className={clsx(
                        "p-4 rounded-lg border-2 transition-all",
                        theme === themeOption
                          ? "border-foreground"
                          : "border-border hover:border-border dark:hover:border-border"
                      )}
                    >
                      <Icon
                        icon={
                          themeOption === "light"
                            ? "solar:sun-linear"
                            : themeOption === "dark"
                            ? "solar:moon-linear"
                            : "solar:settings-linear"
                        }
                        className="text-2xl mb-2"
                      />
                      <p className="text-xs font-medium capitalize">{t(`theme.${themeOption}`)}</p>
                    </button>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* Language Section */}
          {activeSection === "language" && (
            <Card>
              <CardHeader
                title={t('language.title')}
                helpText={helpContent.settings.language.text}
                helpTips={helpContent.settings.language.tips}
              />
              <div className="p-4 space-y-3">
                {[
                  { code: "en" as const, name: "English", native: "English" },
                  { code: "ru" as const, name: "Russian", native: "Русский" },
                  { code: "ky" as const, name: "Kyrgyz", native: "Кыргызча" },
                ].map((lang) => (
                  <button
                    key={lang.code}
                    onClick={() => setLanguage(lang.code)}
                    className={clsx(
                      "w-full flex items-center justify-between p-3 rounded-lg border transition-colors",
                      language === lang.code
                        ? "border-foreground bg-muted"
                        : "border-border hover:bg-muted dark:border-border dark:hover:bg-muted"
                    )}
                  >
                    <div className="text-left">
                      <p className="text-sm font-medium text-foreground">{lang.native}</p>
                      <p className="text-xs text-muted-foreground">{lang.name}</p>
                    </div>
                    {language === lang.code && (
                      <Icon icon="solar:check-circle-bold" className="text-success" />
                    )}
                  </button>
                ))}
              </div>
            </Card>
          )}

          {/* Limits Section */}
          {activeSection === "limits" && (
            <Card>
              <CardHeader
                title={t('limits.title')}
                helpText={helpContent.settings.limits.text}
                helpTips={helpContent.settings.limits.tips}
              />
              <div className="p-4 space-y-4">
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-foreground">{t('limits.wallets')}</p>
                      <p className="text-xs text-muted-foreground">
                        {limits.usedWallets} / {limits.maxWallets}
                      </p>
                    </div>
                    <div className="w-full bg-muted dark:bg-muted rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${(limits.usedWallets / limits.maxWallets) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-foreground">{t('limits.monthlyVolume')}</p>
                      <p className="text-xs text-muted-foreground">
                        ${limits.usedVolume.toLocaleString()} / ${limits.maxMonthlyVolume.toLocaleString()}
                      </p>
                    </div>
                    <div className="w-full bg-muted dark:bg-muted rounded-full h-2">
                      <div
                        className="bg-success h-2 rounded-full transition-all"
                        style={{ width: `${(limits.usedVolume / limits.maxMonthlyVolume) * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="pt-4 border-t border-border">
                    <p className="text-sm font-medium text-foreground mb-2">{t('limits.transaction')}</p>
                    <p className="text-xs text-muted-foreground">
                      {t('limits.maxTransactionSize')}: ${limits.maxTransactionSize.toLocaleString()}
                    </p>
                  </div>
                </div>

                <button className="w-full px-4 py-2 text-sm rounded-lg border border-border hover:bg-muted dark:border-border dark:hover:bg-muted transition-colors">
                  {t('limits.upgrade')}
                </button>
              </div>
            </Card>
          )}

          {/* Backup Section */}
          {activeSection === "backup" && (
            <Card>
              <CardHeader
                title={t('backup.title')}
                helpText={helpContent.settings.backup.text}
                helpTips={helpContent.settings.backup.tips}
              />
              <div className="p-4 space-y-4">
                <div className="p-4 rounded-lg bg-primary/5 border border-primary/30">
                  <p className="text-sm text-foreground">
                    <Icon icon="solar:info-circle-bold" className="inline mr-2" />
                    {t('backup.description')}
                  </p>
                </div>

                <div className="flex items-start gap-2 rounded-lg border border-warning/30 bg-warning/5 p-3 text-[12px] text-foreground">
                  <Icon icon="solar:info-circle-bold" className="text-warning mt-0.5 shrink-0" />
                  <div>
                    Кнопки экспорта — превью. CSV-выгрузка кошельков и транзакций
                    реально работает на страницах{" "}
                    <a className="text-primary underline-offset-4 hover:underline" href="/wallets">/wallets</a>
                    {" "}и{" "}
                    <a className="text-primary underline-offset-4 hover:underline" href="/transactions">/transactions</a>{" "}
                    — кнопка «Экспорт CSV» в шапке таблицы.
                  </div>
                </div>
                <div className="space-y-3">
                  {[
                    { icon: "solar:folder-linear",                label: t('backup.exportWallets'),       desc: t('backup.exportWalletsDesc') },
                    { icon: "solar:document-text-linear",         label: t('backup.exportTransactions'),  desc: t('backup.exportTransactionsDesc') },
                    { icon: "solar:users-group-rounded-linear",   label: t('backup.exportContacts'),       desc: t('backup.exportContactsDesc') },
                  ].map((row) => (
                    <button
                      key={row.label}
                      type="button"
                      disabled
                      title="В разработке"
                      className="w-full flex items-center justify-between p-3 rounded-lg border border-border opacity-60 cursor-not-allowed"
                    >
                      <div className="flex items-center gap-3">
                        <Icon icon={row.icon} className="text-xl" />
                        <div className="text-left">
                          <p className="text-sm font-medium text-foreground">{row.label}</p>
                          <p className="text-xs text-muted-foreground">{row.desc}</p>
                        </div>
                      </div>
                      <Icon icon="solar:download-linear" className="text-muted-foreground" />
                    </button>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* About Section */}
          {activeSection === "about" && (
            <Card>
              <CardHeader
                title={t('about.title')}
                helpText={helpContent.settings.about.text}
                helpTips={helpContent.settings.about.tips}
              />
              <div className="p-4 space-y-4">
                <div className="text-center py-6">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary mb-4">
                    <span className="text-2xl font-bold text-primary-foreground">O</span>
                  </div>
                  <h3 className="text-lg font-bold text-foreground">ORGON</h3>
                  <p className="text-sm text-muted-foreground">{t('about.version')}: 1.0.0-beta</p>
                </div>

                <div className="space-y-2 pt-4 border-t border-border">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{t('about.backend')}</span>
                    <StatusDot active={!!health} />
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{t('about.safinaApi')}</span>
                    <StatusDot active={!!safinaHealth?.safina_reachable} />
                  </div>
                  {health?.last_sync ? (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{t('about.lastSync')}</span>
                      <span className="text-xs font-mono text-muted-foreground">{String(health.last_sync)}</span>
                    </div>
                  ) : null}
                </div>

                <div className="space-y-2 pt-4 border-t border-border">
                  <a
                    href="https://orgon.asystem.ai/docs"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-muted dark:hover:bg-muted transition-colors"
                  >
                    <span className="text-sm text-foreground">{t('about.documentation')}</span>
                    <Icon icon="solar:arrow-right-linear" className="text-muted-foreground" />
                  </a>
                  <a
                    href="https://asystem.kg"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-muted dark:hover:bg-muted transition-colors"
                  >
                    <span className="text-sm text-foreground">{t('about.website')}</span>
                    <Icon icon="solar:arrow-right-linear" className="text-muted-foreground" />
                  </a>
                  <a
                    href="mailto:support@asystem.kg"
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-muted dark:hover:bg-muted transition-colors"
                  >
                    <span className="text-sm text-foreground">{t('about.support')}</span>
                    <Icon icon="solar:arrow-right-linear" className="text-muted-foreground" />
                  </a>
                </div>

                <div className="pt-4 border-t border-border">
                  <p className="text-xs text-center text-muted-foreground">
                    © 2026 ASYSTEM. {t('about.rights')}
                  </p>
                </div>
              </div>
            </Card>
          )}
        </main>
      </div>
    </>
  );
}
