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

  // API Keys state
  const [apiKeys, setApiKeys] = useState<{ id: number; name: string; key: string; created: string; lastUsed: string }[]>([]);

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
    // Load API keys
    (api as any).getApiKeys?.()?.then?.((keys: any) => {
      if (Array.isArray(keys)) setApiKeys(keys);
    })?.catch?.(() => {});
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
        {/* Quick navigation grid */}
        <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
          {[
            { href: "/profile", label: "Профиль", icon: "solar:user-bold", color: "bg-blue-100 dark:bg-blue-900/30 text-primary" },
            { href: "/settings", label: "Безопасность (2FA)", icon: "solar:shield-keyhole-bold", color: "bg-green-100 dark:bg-green-900/30 text-success", active: true },
            { href: "/settings/keys", label: "API ключи", icon: "solar:key-bold", color: "bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400" },
            { href: "/settings/organization", label: "Организация", icon: "solar:buildings-bold", color: "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400" },
            { href: "/settings/platform", label: "Платформа", icon: "solar:server-bold", color: "bg-indigo-100 dark:bg-indigo-900/30 text-primary dark:text-primary", admin: true },
            { href: "/settings/webhooks", label: "Webhooks", icon: "solar:link-bold", color: "bg-pink-100 dark:bg-pink-900/30 text-pink-600 dark:text-pink-400", admin: true },
            { href: "/settings/system/monitoring", label: "Мониторинг", icon: "solar:monitor-bold", color: "bg-red-100 dark:bg-red-900/30 text-destructive", admin: true },
          ].map((item) => (
            <a
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 rounded-xl border border-border bg-white p-4 transition-all hover:shadow-md dark:border-border dark:bg-card",
                item.active && "ring-2 ring-blue-500"
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
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-2xl font-bold">
                    {profile.fullName.charAt(0)}
                  </div>
                  <button className="px-4 py-2 text-sm rounded-lg border border-slate-300 hover:bg-muted dark:border-border dark:hover:bg-muted transition-colors">
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
                      className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
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
                      className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      {t('profile.role')}
                    </label>
                    <Badge variant="primary">{profile.role}</Badge>
                  </div>
                </div>

                <button className="px-4 py-2 text-sm rounded-lg bg-foreground text-background hover:bg-muted dark:bg-white dark:text-slate-950 dark:hover:bg-muted transition-colors">
                  {t('profile.saveChanges')}
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
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-foreground">{t('security.twoFactor')}</p>
                      <p className="text-xs text-muted-foreground">{t('security.twoFactorDesc')}</p>
                    </div>
                    <button
                      onClick={() => setSecurity({ ...security, twoFactorEnabled: !security.twoFactorEnabled })}
                      className={clsx(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                        security.twoFactorEnabled ? "bg-green-500" : "bg-slate-300 dark:bg-slate-700"
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

                  <div className="border-t border-border pt-4">
                    <p className="text-sm font-medium text-foreground mb-2">{t('security.changePassword')}</p>
                    <div className="space-y-2">
                      <input
                        type="password"
                        placeholder={t('security.currentPassword')}
                        className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                      />
                      <input
                        type="password"
                        placeholder={t('security.newPassword')}
                        className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                      />
                      <input
                        type="password"
                        placeholder={t('security.confirmPassword')}
                        className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                      />
                      <button className="px-4 py-2 text-sm rounded-lg bg-foreground text-background hover:bg-muted dark:bg-white dark:text-slate-950 dark:hover:bg-muted">
                        {t('security.updatePassword')}
                      </button>
                    </div>
                  </div>

                  <div className="border-t border-border pt-4">
                    <p className="text-sm font-medium text-foreground mb-2">{t('security.activeSessions')}</p>
                    <p className="text-xs text-muted-foreground">
                      {security.activeSessions} {t('security.activeSessionsCount')}
                    </p>
                    <button className="mt-2 text-xs text-red-600 hover:text-destructive">
                      {t('security.logoutAllSessions')}
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
                <button className="px-4 py-2 text-sm rounded-lg bg-foreground text-background hover:bg-muted dark:bg-white dark:text-slate-950 dark:hover:bg-muted">
                  <Icon icon="solar:add-circle-linear" className="inline mr-2" />
                  {t('apiKeys.createNew')}
                </button>

                <div className="space-y-3">
                  {apiKeys.map((key) => (
                    <div
                      key={key.id}
                      className="p-4 rounded-lg border border-border space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-foreground">{key.name}</p>
                        <div className="flex gap-2">
                          <button className="text-xs text-muted-foreground hover:text-foreground dark:text-muted-foreground dark:hover:text-white">
                            {t('apiKeys.revoke')}
                          </button>
                        </div>
                      </div>
                      <p className="text-xs font-mono text-muted-foreground">{key.key}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{t('apiKeys.created')}: {key.created}</span>
                        <span>{t('apiKeys.lastUsed')}: {key.lastUsed}</span>
                      </div>
                    </div>
                  ))}
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
                {[
                  { key: "emailNotifications" as const, label: t('notifications.email'), desc: t('notifications.emailDesc') },
                  { key: "pushNotifications" as const, label: t('notifications.push'), desc: t('notifications.pushDesc') },
                  { key: "telegramNotifications" as const, label: t('notifications.telegram'), desc: t('notifications.telegramDesc') },
                  { key: "transactionAlerts" as const, label: t('notifications.transactions'), desc: t('notifications.transactionsDesc') },
                  { key: "securityAlerts" as const, label: t('notifications.security'), desc: t('notifications.securityDesc') },
                  { key: "weeklyReport" as const, label: t('notifications.weekly'), desc: t('notifications.weeklyDesc') },
                ].map((item) => (
                  <div key={item.key} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-foreground">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.desc}</p>
                    </div>
                    <button
                      onClick={() => setNotifications({ ...notifications, [item.key]: !notifications[item.key] })}
                      className={clsx(
                        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
                        notifications[item.key] ? "bg-green-500" : "bg-slate-300 dark:bg-slate-700"
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
                          ? "border-slate-900 dark:border-white"
                          : "border-border hover:border-slate-300 dark:hover:border-border"
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
                        ? "border-slate-900 bg-muted dark:border-white dark:bg-muted"
                        : "border-border hover:bg-muted dark:border-border dark:hover:bg-muted"
                    )}
                  >
                    <div className="text-left">
                      <p className="text-sm font-medium text-foreground">{lang.native}</p>
                      <p className="text-xs text-muted-foreground">{lang.name}</p>
                    </div>
                    {language === lang.code && (
                      <Icon icon="solar:check-circle-bold" className="text-green-500" />
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
                    <div className="w-full bg-slate-200 dark:bg-muted rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all"
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
                    <div className="w-full bg-slate-200 dark:bg-muted rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full transition-all"
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

                <button className="w-full px-4 py-2 text-sm rounded-lg border border-slate-300 hover:bg-muted dark:border-border dark:hover:bg-muted transition-colors">
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
                <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900">
                  <p className="text-sm text-blue-900 dark:text-blue-200">
                    <Icon icon="solar:info-circle-bold" className="inline mr-2" />
                    {t('backup.description')}
                  </p>
                </div>

                <div className="space-y-3">
                  <button className="w-full flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted dark:border-border dark:hover:bg-muted transition-colors">
                    <div className="flex items-center gap-3">
                      <Icon icon="solar:folder-linear" className="text-xl" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-foreground">{t('backup.exportWallets')}</p>
                        <p className="text-xs text-muted-foreground">{t('backup.exportWalletsDesc')}</p>
                      </div>
                    </div>
                    <Icon icon="solar:download-linear" className="text-muted-foreground" />
                  </button>

                  <button className="w-full flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted dark:border-border dark:hover:bg-muted transition-colors">
                    <div className="flex items-center gap-3">
                      <Icon icon="solar:document-text-linear" className="text-xl" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-foreground">{t('backup.exportTransactions')}</p>
                        <p className="text-xs text-muted-foreground">{t('backup.exportTransactionsDesc')}</p>
                      </div>
                    </div>
                    <Icon icon="solar:download-linear" className="text-muted-foreground" />
                  </button>

                  <button className="w-full flex items-center justify-between p-3 rounded-lg border border-border hover:bg-muted dark:border-border dark:hover:bg-muted transition-colors">
                    <div className="flex items-center gap-3">
                      <Icon icon="solar:users-group-rounded-linear" className="text-xl" />
                      <div className="text-left">
                        <p className="text-sm font-medium text-foreground">{t('backup.exportContacts')}</p>
                        <p className="text-xs text-muted-foreground">{t('backup.exportContactsDesc')}</p>
                      </div>
                    </div>
                    <Icon icon="solar:download-linear" className="text-muted-foreground" />
                  </button>
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
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 mb-4">
                    <span className="text-2xl font-bold text-white">O</span>
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
