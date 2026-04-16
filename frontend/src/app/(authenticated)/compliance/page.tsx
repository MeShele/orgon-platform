"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR from "swr";

interface ComplianceData {
  total_verified: number;
  pending_review: number;
  rejected: number;
  records: any[];
}

type Tab = "overview" | "aml" | "kyc" | "reports";

export default function CompliancePage() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  const { data: kyc } = useSWR<ComplianceData>(
    "/api/compliance/kyc",
    () => api.get("/api/compliance/kyc")
  );

  const { data: kyb } = useSWR<ComplianceData>(
    "/api/compliance/kyb",
    () => api.get("/api/compliance/kyb")
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
        {/* Статистика */}
        <div className={pageLayout.grid.cols4}>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-amber-100 dark:bg-amber-900/30 p-2.5">
                <Icon icon="solar:shield-warning-bold" className="text-xl text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">0</p>
                <p className="text-xs text-slate-500">AML-оповещения</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-green-100 dark:bg-green-900/30 p-2.5">
                <Icon icon="solar:user-check-bold" className="text-xl text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{kyc?.total_verified || 0}</p>
                <p className="text-xs text-slate-500">KYC верифицировано</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-blue-100 dark:bg-blue-900/30 p-2.5">
                <Icon icon="solar:document-text-bold" className="text-xl text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">0</p>
                <p className="text-xs text-slate-500">Отчёты к сдаче</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="p-4 flex items-center gap-3">
              <div className="rounded-lg bg-indigo-100 dark:bg-indigo-900/30 p-2.5">
                <Icon icon="solar:graph-up-bold" className="text-xl text-indigo-600 dark:text-indigo-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">Низкий</p>
                <p className="text-xs text-slate-500">Уровень риска</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Табы */}
        <div className="flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-slate-800">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                  : "border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              }`}
            >
              <Icon icon={tab.icon} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Контент табов */}
        {activeTab === "overview" && (
          <div className="space-y-4">
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Лицензирование в Кыргызской Республике</h3>
                {/* Мобильные карточки */}
                <div className="space-y-3 md:hidden">
                  {[
                    { type: "Оператор обмена ВА", desc: "Фиат ↔ крипто обмен", capital: "400 000 ед.", tier: "Tier A", color: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300" },
                    { type: "Оператор торговли ВА", desc: "Крипто-биржа", capital: "Повышенный", tier: "Tier B", color: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300" },
                    { type: "Кастодиан", desc: "Хранение ВА третьих лиц", capital: "По требованию", tier: "ASYSTEM", color: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300" },
                    { type: "Эмитент ВА", desc: "Выпуск токенов/стейблкоинов", capital: "По требованию", tier: "Tier C", color: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300" },
                  ].map((l) => (
                    <div key={l.type} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium text-slate-900 dark:text-white">{l.type}</p>
                        <span className={`rounded px-2 py-0.5 text-xs ${l.color}`}>{l.tier}</span>
                      </div>
                      <p className="text-xs text-slate-500">{l.desc} • Капитал: {l.capital}</p>
                    </div>
                  ))}
                </div>
                {/* Десктопная таблица */}
                <div className="hidden md:block overflow-x-auto">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-700">
                        <th className="text-left py-2 text-xs font-medium text-slate-500">Тип лицензии</th>
                        <th className="text-left py-2 text-xs font-medium text-slate-500">Описание</th>
                        <th className="text-left py-2 text-xs font-medium text-slate-500">Требования к капиталу</th>
                        <th className="text-left py-2 text-xs font-medium text-slate-500">Уровень ORGON</th>
                      </tr>
                    </thead>
                    <tbody className="text-slate-700 dark:text-slate-300">
                      <tr className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 font-medium">Оператор обмена ВА</td>
                        <td className="py-2">Фиат ↔ крипто обмен</td>
                        <td className="py-2">400 000 единиц</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs">Tier A</span></td>
                      </tr>
                      <tr className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 font-medium">Оператор торговли ВА</td>
                        <td className="py-2">Крипто-биржа, листинг/делистинг</td>
                        <td className="py-2">Повышенный</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded text-xs">Tier B</span></td>
                      </tr>
                      <tr className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-2 font-medium">Кастодиан</td>
                        <td className="py-2">Хранение ВА третьих лиц</td>
                        <td className="py-2">По требованию</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded text-xs">ASYSTEM</span></td>
                      </tr>
                      <tr>
                        <td className="py-2 font-medium">Эмитент ВА</td>
                        <td className="py-2">Выпуск токенов/стейблкоинов</td>
                        <td className="py-2">По требованию</td>
                        <td className="py-2"><span className="px-2 py-0.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded text-xs">Tier C</span></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Ключевые требования</h3>
                <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-emerald-500 mt-0.5 flex-shrink-0" /> Раздельное хранение средств клиентов (Ст. 5, Постановление 625)</li>
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-emerald-500 mt-0.5 flex-shrink-0" /> Запрет анонимных кошельков — все кошельки привязаны к идентифицированным пользователям</li>
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-emerald-500 mt-0.5 flex-shrink-0" /> Обязательная оценка рисков транзакций (Ст. 24, Постановление 625)</li>
                  <li className="flex items-start gap-2"><Icon icon="solar:check-circle-bold" className="text-emerald-500 mt-0.5 flex-shrink-0" /> Ежеквартальная отчётность в Финнадзор</li>
                </ul>
              </div>
            </Card>
          </div>
        )}

        {activeTab === "aml" && (
          <div className="space-y-4">
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Мониторинг AML/KYT</h3>
                <div className={pageLayout.success + " mb-4"}>
                  <p className="flex items-center gap-2">
                    <Icon icon="solar:check-circle-bold" /> Все транзакции проверены — подозрительная активность не обнаружена
                  </p>
                </div>
                <h4 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Правила мониторинга</h4>
                <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
                  <li>• Транзакции свыше $10 000 — автоматическая генерация SAR</li>
                  <li>• Множественные мелкие транзакции (обнаружение дробления)</li>
                  <li>• Транзакции с адресами высокого риска (чёрные списки)</li>
                  <li>• Мониторинг трансграничных операций</li>
                  <li>• Обнаружение необычных паттернов (на основе ML)</li>
                </ul>
              </div>
            </Card>
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Оценка рисков</h3>
                <div className={pageLayout.grid.cols3}>
                  {[
                    { level: "Низкий риск", color: "bg-emerald-500", range: "0-30%", desc: "Автоматическое одобрение" },
                    { level: "Средний риск", color: "bg-amber-500", range: "31-70%", desc: "Ручная проверка" },
                    { level: "Высокий риск", color: "bg-red-500", range: "71-100%", desc: "Блокировка, подача SAR" },
                  ].map((r) => (
                    <div key={r.level} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className={`w-3 h-3 rounded-full ${r.color}`} />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{r.level}</span>
                      </div>
                      <p className="text-xs text-slate-500">{r.range} — {r.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}

        {activeTab === "kyc" && (
          <div className="space-y-4">
            <Card>
              <div className="p-4 sm:p-6">
                <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Требования KYC/KYB</h3>
                <div className={pageLayout.grid.cols2}>
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4">
                    <h4 className="text-sm font-medium text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                      <Icon icon="solar:user-bold" className="text-indigo-500" /> KYC — Физические лица
                    </h4>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs text-slate-500">Верифицировано: {kyc?.total_verified || 0}</span>
                      <span className="text-xs text-slate-500">• На рассмотрении: {kyc?.pending_review || 0}</span>
                      <span className="text-xs text-slate-500">• Отклонено: {kyc?.rejected || 0}</span>
                    </div>
                    <ul className="space-y-1.5 text-sm text-slate-600 dark:text-slate-400">
                      <li>• ФИО и дата рождения</li>
                      <li>• Удостоверение личности (паспорт)</li>
                      <li>• Селфи-верификация</li>
                      <li>• Подтверждение адреса</li>
                      <li>• Декларация об источнике средств</li>
                    </ul>
                  </div>
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 p-4">
                    <h4 className="text-sm font-medium text-slate-900 dark:text-white mb-2 flex items-center gap-2">
                      <Icon icon="solar:buildings-bold" className="text-indigo-500" /> KYB — Юридические лица
                    </h4>
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-xs text-slate-500">Верифицировано: {kyb?.total_verified || 0}</span>
                      <span className="text-xs text-slate-500">• На рассмотрении: {kyb?.pending_review || 0}</span>
                      <span className="text-xs text-slate-500">• Отклонено: {kyb?.rejected || 0}</span>
                    </div>
                    <ul className="space-y-1.5 text-sm text-slate-600 dark:text-slate-400">
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
              <h3 className="font-semibold text-slate-900 dark:text-white mb-3">Отчётность для Финнадзора</h3>
              {/* Мобильные карточки */}
              <div className="space-y-3 md:hidden">
                {[
                  { report: "Отчёт об объёмах транзакций", freq: "Квартальный", status: "Актуален", next: "Q2 2026", color: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300" },
                  { report: "SAR (Подозрительная активность)", freq: "По необходимости", status: "Нет ожидающих", next: "—", color: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300" },
                  { report: "Сегрегация активов клиентов", freq: "Квартальный", status: "Актуален", next: "Q2 2026", color: "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300" },
                  { report: "Годовой аудит комплаенса", freq: "Годовой", status: "Запланирован", next: "Дек 2026", color: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300" },
                ].map((r) => (
                  <div key={r.report} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                    <p className="text-sm font-medium text-slate-900 dark:text-white">{r.report}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs text-slate-500">{r.freq} • Следующий: {r.next}</span>
                      <span className={`rounded px-2 py-0.5 text-xs ${r.color}`}>{r.status}</span>
                    </div>
                  </div>
                ))}
              </div>
              {/* Десктопная таблица */}
              <div className="hidden md:block overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="text-left py-2 text-xs font-medium text-slate-500">Отчёт</th>
                      <th className="text-left py-2 text-xs font-medium text-slate-500">Периодичность</th>
                      <th className="text-left py-2 text-xs font-medium text-slate-500">Статус</th>
                      <th className="text-left py-2 text-xs font-medium text-slate-500">Следующая сдача</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-700 dark:text-slate-300">
                    <tr className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2">Отчёт об объёмах транзакций</td>
                      <td className="py-2">Квартальный</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded text-xs">Актуален</span></td>
                      <td className="py-2">Q2 2026</td>
                    </tr>
                    <tr className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2">SAR (Подозрительная активность)</td>
                      <td className="py-2">По необходимости</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded text-xs">Нет ожидающих</span></td>
                      <td className="py-2">—</td>
                    </tr>
                    <tr className="border-b border-slate-100 dark:border-slate-800">
                      <td className="py-2">Сегрегация активов клиентов</td>
                      <td className="py-2">Квартальный</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded text-xs">Актуален</span></td>
                      <td className="py-2">Q2 2026</td>
                    </tr>
                    <tr>
                      <td className="py-2">Годовой аудит комплаенса</td>
                      <td className="py-2">Годовой</td>
                      <td className="py-2"><span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs">Запланирован</span></td>
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
