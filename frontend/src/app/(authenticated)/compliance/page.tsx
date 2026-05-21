"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR from "swr";
import { AmlAlertList } from "@/components/compliance/AmlAlertList";
import { HelpTooltip } from "@/components/common/HelpTooltip";

interface ComplianceData {
  total_verified: number;
  pending_review: number;
  rejected: number;
  records: Record<string, unknown>[];
}

type Tab = "overview" | "aml" | "kyc" | "reports";

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const { data: kyc } = useSWR<ComplianceData>(
    "/api/v1/compliance/kyc",
    () => api.get("/api/v1/compliance/kyc")
  );

  const { data: kyb } = useSWR<ComplianceData>(
    "/api/v1/compliance/kyb",
    () => api.get("/api/v1/compliance/kyb")
  );

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: "overview", label: "Лицензирование", icon: "solar:document-text-linear" },
    { id: "aml", label: "AML/KYT", icon: "solar:shield-warning-linear" },
    { id: "kyc", label: "KYC/KYB", icon: "solar:user-check-linear" },
    { id: "reports", label: "Отчётность", icon: "solar:chart-square-linear" },
  ];

  return (
    <>
      <Header title="Комплаенс" />
      <div className={pageLayout.container}>
        {/* Roadmap-status banner. The /compliance index is sidebar-marked
            `roadmap: true` (see `sidebar-nav.ts`); production-ready
            sub-pages live at `/compliance/rules` and
            `/compliance/reviews` (Waves 23+25+26). This index page
            stays as a navigation hub + light overview until a real
            dashboard ships. Banner sets expectations so the user
            doesn't mistake the mock reports table for live data. */}
        <div className="flex items-start gap-3 rounded-lg border border-warning/30 bg-warning/5 p-4 text-[13px]">
          <Icon icon="solar:info-circle-bold" className="text-warning mt-0.5 shrink-0 text-base" />
          <div className="text-foreground">
            <div className="font-medium">Comply Core — обзорная страница</div>
            <div className="mt-1 text-muted-foreground">
              Этот dashboard объединяет ссылки на рабочие compliance-инструменты.
              Боевые потоки: <span className="text-primary">/compliance/reviews</span> (AML-очередь, SAR),
              <span className="text-primary"> /compliance/rules</span> (rule engine).
              Цифры и календарь отчётности на вкладке «Отчётность» — справочно, реальные SLA — в AML drawer'е.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 -mt-2">
          <HelpTooltip
            text="Compliance dashboard объединяет KYC, KYB, AML triage и регуляторную отчётность в одном месте."
            tips={[
              "AML-вкладка — реальная очередь алертов из Sumsub-bridge + in-house rule engine.",
              "KYC/KYB — Sumsub WebSDK, документы загружаются прямо к ним (FedRAMP-compliant).",
              "Лицензирование — справочно, регуляторные требования КР для VA-операторов.",
              "Отчётность — заглушка, реальный SAR-flow живёт в AML-вкладке (drawer → «Сформировать SAR»).",
              "Кнопка «Правила» (вверху справа) — конфигурация AML rule engine (только для admin).",
            ]}
          />
          <span className="text-xs text-muted-foreground">Что такое эта страница</span>
        </div>
        {/* Статистика */}
        <div className={pageLayout.grid.cols4}>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-warning/10 p-2.5">
                <Icon icon="solar:shield-warning-bold" className="text-xl text-warning" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">0</p>
                <p className="text-xs text-muted-foreground">AML-оповещения</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-success/10 p-2.5">
                <Icon icon="solar:user-check-bold" className="text-xl text-success" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">{kyc?.total_verified || 0}</p>
                <p className="text-xs text-muted-foreground">KYC верифицировано</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <Icon icon="solar:document-text-bold" className="text-xl text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">0</p>
                <p className="text-xs text-muted-foreground">Отчёты к сдаче</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-primary/10 p-2.5">
                <Icon icon="solar:graph-up-bold" className="text-xl text-primary dark:text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold text-foreground">Низкий</p>
                <p className="text-xs text-muted-foreground">Уровень риска</p>
              </div>
            </div>
          </Card>
        </div>

        {/* SAR backend status */}
        <SarBackendIndicator />

        {/* Табы */}
        <div className="flex gap-1 overflow-x-auto border-b border-border items-end">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-primary text-primary dark:text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground dark:hover:text-faint"
              }`}
            >
              <Icon icon={tab.icon} />
              {tab.label}
            </button>
          ))}
          <a
            href="/compliance/rules"
            className="ml-auto px-3 py-2 text-xs text-muted-foreground hover:text-primary inline-flex items-center gap-1"
            title="Настройка правил мониторинга"
          >
            <Icon icon="solar:shield-keyhole-linear" />
            Правила
          </a>
        </div>

        {/* Контент табов */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-foreground mb-3">Лицензирование в Кыргызской Республике</h3>
                {/* Мобильные карточки */}
                <div className="space-y-3 md:hidden">
                  {[
                    { type: "Оператор обмена ВА", desc: "Фиат ↔ крипто обмен", capital: "400 000 ед.", tier: "Tier A", color: "bg-primary/10 text-primary" },
                    { type: "Оператор торговли ВА", desc: "Крипто-биржа", capital: "Повышенный", tier: "Tier B", color: "bg-muted text-foreground" },
                    { type: "Кастодиан", desc: "Хранение ВА третьих лиц", capital: "По требованию", tier: "ASYSTEM", color: "bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300" },
                    { type: "Эмитент ВА", desc: "Выпуск токенов/стейблкоинов", capital: "По требованию", tier: "Tier C", color: "bg-warning/10 text-warning" },
                  ].map((l) => (
                    <div key={l.type} className="rounded-lg border border-border p-3">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium text-foreground">{l.type}</p>
                        <span className={`rounded px-2 py-0.5 text-xs ${l.color}`}>{l.tier}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">{l.desc} • Капитал: {l.capital}</p>
                    </div>
                  ))}
                </div>
                {/* Десктопная таблица */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 text-xs font-medium text-muted-foreground">Тип лицензии</th>
                        <th className="text-left py-2 text-xs font-medium text-muted-foreground">Описание</th>
                        <th className="text-left py-2 text-xs font-medium text-muted-foreground">Требования к капиталу</th>
                        <th className="text-left py-2 text-xs font-medium text-muted-foreground">Уровень ORGON</th>
                      </tr>
                    </thead>
                    <tbody className="text-foreground">
                      <tr className="border-b border-border">
                        <td className="py-2 font-medium">Оператор обмена ВА</td>
                        <td className="py-2">Фиат ↔ крипто обмен</td>
                        <td className="py-2">400 000 единиц</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">Tier A</span></td>
                      </tr>
                      <tr className="border-b border-border">
                        <td className="py-2 font-medium">Оператор торговли ВА</td>
                        <td className="py-2">Крипто-биржа, листинг/делистинг</td>
                        <td className="py-2">Повышенный</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-muted text-foreground rounded text-xs">Tier B</span></td>
                      </tr>
                      <tr className="border-b border-border">
                        <td className="py-2 font-medium">Кастодиан</td>
                        <td className="py-2">Хранение ВА третьих лиц</td>
                        <td className="py-2">По требованию</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300 rounded text-xs">ASYSTEM</span></td>
                      </tr>
                      <tr>
                        <td className="py-2 font-medium">Эмитент ВА</td>
                        <td className="py-2">Выпуск токенов/стейблкоинов</td>
                        <td className="py-2">По требованию</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-warning/10 text-warning rounded text-xs">Tier C</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-foreground mb-3">Ключевые требования</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-success mt-0.5 flex-shrink-0" /> Раздельное хранение средств клиентов (Ст. 5, Постановление 625)</li>
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-success mt-0.5 flex-shrink-0" /> Запрет анонимных кошельков — все кошельки привязаны к идентифицированным пользователям</li>
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-success mt-0.5 flex-shrink-0" /> Обязательная оценка рисков транзакций (Ст. 24, Постановление 625)</li>
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-success mt-0.5 flex-shrink-0" /> Ежеквартальная отчётность в Финнадзор</li>
                </ul>
              </div>
            </Card>
          </div>
        )}

        {activeTab === "aml" && <AmlAlertList />}

        {activeTab === "kyc" && (
          <div className="space-y-4">
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-foreground mb-3">Требования KYC/KYB</h3>
                <div className={pageLayout.grid.cols2}>
                  <div className="rounded-lg border border-border p-4">
                    <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                      <Icon icon="solar:user-bold" className="text-primary" /> KYC — Физические лица
                    </h4>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs text-muted-foreground">Верифицировано: {kyc?.total_verified || 0}</span>
                      <span className="text-xs text-muted-foreground">• На рассмотрении: {kyc?.pending_review || 0}</span>
                      <span className="text-xs text-muted-foreground">• Отклонено: {kyc?.rejected || 0}</span>
                    </div>
                    <ul className="space-y-1.5 text-sm text-muted-foreground">
                      <li>• ФИО и дата рождения</li>
                      <li>• Удостоверение личности (паспорт)</li>
                      <li>• Селфи-верификация</li>
                      <li>• Подтверждение адреса</li>
                      <li>• Декларация об источнике средств</li>
                    </ul>
                  </div>
                  <div className="rounded-lg border border-border p-4">
                    <h4 className="text-sm font-medium text-foreground mb-2 flex items-center gap-2">
                      <Icon icon="solar:buildings-bold" className="text-primary" /> KYB — Юридические лица
                    </h4>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs text-muted-foreground">Верифицировано: {kyb?.total_verified || 0}</span>
                      <span className="text-xs text-muted-foreground">• На рассмотрении: {kyb?.pending_review || 0}</span>
                      <span className="text-xs text-muted-foreground">• Отклонено: {kyb?.rejected || 0}</span>
                    </div>
                    <ul className="space-y-1.5 text-sm text-muted-foreground">
                      <li>• Свидетельство о регистрации</li>
                      <li>• Лицензия на деятельность с ВА от Финнадзора</li>
                      <li>• Учредительные документы</li>
                      <li>• Структура бенефициарного владения</li>
                      <li>• Политика AML/CFT</li>
                    </ul>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeTab === "reports" && (
          <Card>
            <div className="p-4 sm:p-6">
              <h3 className="font-semibold text-foreground mb-3">Отчётность для Финнадзора</h3>
              {/* Mock data — таблица ниже жёстко закодирована (это
                  пример календаря отчётности). Реальные дедлайны и
                  статусы — в AML-drawer'е → «Сформировать SAR»
                  (Wave 24). Эта вкладка остаётся справочной до тех
                  пор пока полноценный reporting dashboard не выйдет в
                  отдельном sprint'е. */}
              <div className="mb-4 flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-[12px] text-muted-foreground">
                <Icon icon="solar:info-circle-bold" className="mt-0.5 shrink-0 text-warning" />
                <span>
                  Таблица ниже — пример календаря отчётности (мок).
                  Боевые SAR-submission'ы и статусы — на вкладке AML, кнопка «Сформировать SAR» в drawer'е алерта.
                </span>
              </div>
              {/* Мобильные карточки */}
              <div className="space-y-3 md:hidden">
                {[
                  { report: "Отчёт об объёмах транзакций", freq: "Квартальный", status: "Актуален", next: "Q2 2026", color: "bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300" },
                  { report: "SAR (Подозрительная активность)", freq: "По необходимости", status: "Нет ожидающих", next: "—", color: "bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300" },
                  { report: "Сегрегация активов клиентов", freq: "Квартальный", status: "Актуален", next: "Q2 2026", color: "bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300" },
                  { report: "Годовой аудит комплаенса", freq: "Годовой", status: "Запланирован", next: "Дек 2026", color: "bg-primary/10 text-primary" },
                ].map((r) => (
                  <div key={r.report} className="rounded-lg border border-border p-3">
                    <p className="text-sm font-medium text-foreground">{r.report}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-muted-foreground">{r.freq} • Следующий: {r.next}</span>
                      <span className={`rounded px-2 py-0.5 text-xs ${r.color}`}>{r.status}</span>
                    </div>
                  </div>
                ))}
              </div>
              {/* Десктопная таблица */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 text-xs font-medium text-muted-foreground">Отчёт</th>
                      <th className="text-left py-2 text-xs font-medium text-muted-foreground">Периодичность</th>
                      <th className="text-left py-2 text-xs font-medium text-muted-foreground">Статус</th>
                      <th className="text-left py-2 text-xs font-medium text-muted-foreground">Следующая сдача</th>
                    </tr>
                  </thead>
                  <tbody className="text-foreground">
                    <tr className="border-b border-border">
                      <td className="py-2">Отчёт об объёмах транзакций</td>
                      <td className="py-2">Квартальный</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300 rounded text-xs">Актуален</span></td>
                      <td className="py-2">Q2 2026</td>
                    </tr>
                    <tr className="border-b border-border">
                      <td className="py-2">SAR (Подозрительная активность)</td>
                      <td className="py-2">По необходимости</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300 rounded text-xs">Нет ожидающих</span></td>
                      <td className="py-2">—</td>
                    </tr>
                    <tr className="border-b border-border">
                      <td className="py-2">Сегрегация активов клиентов</td>
                      <td className="py-2">Квартальный</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-success dark:text-emerald-300 rounded text-xs">Актуален</span></td>
                      <td className="py-2">Q2 2026</td>
                    </tr>
                    <tr>
                      <td className="py-2">Годовой аудит комплаенса</td>
                      <td className="py-2">Годовой</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-primary/10 text-primary rounded text-xs">Запланирован</span></td>
                      <td className="py-2">Дек 2026</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}

// ────────────────────────────────────────────────────────────────────
// SAR backend indicator — shows compliance officer at a glance which
// channel SAR submissions are flowing through (manual_export / email /
// api_v1 / dryrun) and whether it's correctly configured.
// ────────────────────────────────────────────────────────────────────

type SarConfig = {
  backend: "manual_export" | "email" | "api_v1" | "dryrun" | string;
  ready: boolean;
  missing_env: string[];
  target_email: string | null;
  cc_email: string | null;
  smtp_configured: boolean;
  known_backends: string[];
};

const BACKEND_LABEL: Record<string, { label: string; description: string }> = {
  manual_export: {
    label: "Ручная выгрузка",
    description:
      "SAR файлы (JSON + Markdown) сохраняются в sar_submissions. Сотрудник скачивает их и подаёт через портал Финнадзора руками.",
  },
  email: {
    label: "Email",
    description:
      "SAR автоматически уходит на FINSUPERVISORY_SAR_EMAIL с прикреплёнными CSV (для копипасты в форму) + JSON + Markdown.",
  },
  api_v1: {
    label: "API v1",
    description:
      "Резерв на будущее: прямая подача через Финнадзор API. Сейчас не реализовано — Финнадзор не опубликовал спецификацию.",
  },
  dryrun: {
    label: "Тестовый (dryrun)",
    description: "Только логирует, ничего не отправляет. Для тестов и shadow-валидации.",
  },
};

function SarBackendIndicator() {
  const { data, error, isLoading } = useSWR<SarConfig>(
    "/api/v1/compliance/sar/config",
    () => api.get("/api/v1/compliance/sar/config"),
    { refreshInterval: 60_000 },
  );

  if (isLoading) {
    return (
      <Card>
        <div className="p-3 text-xs text-muted-foreground">Загрузка конфигурации SAR…</div>
      </Card>
    );
  }
  if (error || !data) {
    return (
      <Card>
        <div className="p-3 text-xs text-destructive">
          Не удалось загрузить конфигурацию SAR backend.
        </div>
      </Card>
    );
  }

  const info = BACKEND_LABEL[data.backend] ?? {
    label: data.backend,
    description: "Неизвестный backend",
  };

  return (
    <Card>
      <div className="p-3 sm:p-4 flex flex-wrap items-center gap-3 text-xs">
        <Icon icon="solar:letter-linear" className="text-base text-muted-foreground" />
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-muted-foreground">Режим подачи SAR:</span>
          <span
            className={
              data.ready
                ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                : "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
            }
            title={info.description}
          >
            {info.label}
          </span>
          {data.ready ? (
            <span className="text-success text-[10px]">готов</span>
          ) : (
            <span className="text-warning text-[10px]">требует настройки</span>
          )}
        </div>

        {data.backend === "email" && (
          <div className="flex items-center gap-2 text-muted-foreground ml-auto">
            {data.target_email ? (
              <span className="font-mono text-[11px]" title="Куда уходит SAR">
                → {data.target_email}
              </span>
            ) : null}
            {data.cc_email ? (
              <span className="font-mono text-[11px]" title="Кому копия (compliance officer)">
                cc: {data.cc_email}
              </span>
            ) : null}
            <span
              className={
                data.smtp_configured
                  ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                  : "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
              }
              title={
                data.smtp_configured
                  ? "SMTP_HOST env var задан"
                  : "SMTP_HOST не задан — настройте в Coolify env"
              }
            >
              SMTP {data.smtp_configured ? "OK" : "нет"}
            </span>
          </div>
        )}

        {!data.ready && data.missing_env.length > 0 && (
          <div className="w-full mt-1 text-warning text-[11px]">
            Не хватает:{" "}
            {data.missing_env.map((m, i) => (
              <span key={m}>
                {i > 0 ? ", " : ""}
                <code className="font-mono">{m}</code>
              </span>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
