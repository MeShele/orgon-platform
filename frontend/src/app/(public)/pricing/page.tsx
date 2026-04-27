"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { SafeIcon as Icon } from "@/components/SafeIcon";
import { Button } from "@/components/ui/Button";
import { API_BASE } from "@/lib/api";

interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  monthly_price: string;
  yearly_price: string;
  currency: string;
  features: Record<string, unknown>;
  sort_order: number;
  is_active: boolean;
  margin_min?: string | null;
}

const PLAN_VISUALS: Record<string, { gradient: string; iconBg: string; icon: string; tagline: string }> = {
  start: {
    gradient: "from-blue-500 to-cyan-500",
    iconBg: "from-blue-500/10 to-cyan-500/10",
    icon: "solar:rocket-2-bold",
    tagline: "Для малых обменников и финтех",
  },
  business: {
    gradient: "from-emerald-500 to-teal-500",
    iconBg: "from-emerald-500/10 to-teal-500/10",
    icon: "solar:buildings-2-bold",
    tagline: "Для средних бирж и брокеров",
  },
  enterprise: {
    gradient: "from-amber-500 to-orange-500",
    iconBg: "from-amber-500/10 to-orange-500/10",
    icon: "solar:crown-star-bold",
    tagline: "Для банков и крупных бирж",
  },
};

const FEATURE_LABELS: Record<string, string> = {
  max_wallets: "Кошельков",
  max_transactions: "Транзакций / мес",
  tx_commission: "Комиссия за транзакцию",
  crypto_acquiring: "Крипто-эквайринг",
  kyc_price: "KYC за пользователя ($)",
  basic_support: "Базовая поддержка",
  priority_support: "Приоритетная поддержка",
  dedicated_support: "Выделенная поддержка",
  dedicated_manager: "Персональный менеджер",
  api_access: "API доступ",
  white_label: "White-label",
  sla_24_7: "SLA 24/7",
  unlimited_wallets: "Неограниченные кошельки",
  unlimited_transactions: "Неограниченные транзакции",
};

function formatPrice(amount: string, currency: string): string {
  const n = Number(amount);
  if (Number.isNaN(n)) return amount;
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n) + " " + currency;
}

function describeFeature(key: string, value: unknown): string {
  const label = FEATURE_LABELS[key] ?? key;
  if (typeof value === "boolean") return label;
  if (typeof value === "number") return `${label}: ${new Intl.NumberFormat("ru-RU").format(value)}`;
  return `${label}: ${value}`;
}

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/billing/plans`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Plan[]) => {
        if (cancelled) return;
        const active = (Array.isArray(data) ? data : [])
          .filter((p) => p.is_active)
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
        setPlans(active);
      })
      .catch((e) => !cancelled && setError(e.message ?? "Не удалось загрузить тарифы"));
    return () => {
      cancelled = true;
    };
  }, []);

  const yearlySavings = useMemo(() => {
    if (!plans) return null;
    const start = plans.find((p) => p.slug === "start");
    if (!start) return null;
    const monthly12 = Number(start.monthly_price) * 12;
    const yearly = Number(start.yearly_price);
    if (!monthly12 || !yearly) return null;
    const pct = Math.round((1 - yearly / monthly12) * 100);
    return pct > 0 ? pct : null;
  }, [plans]);

  return (
    <div className="py-24 bg-slate-50 dark:bg-slate-950 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-emerald-500/5 to-transparent pointer-events-none z-0" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-display font-bold text-slate-900 dark:text-white mb-6 tracking-tight">
            Тарифы{" "}
            <span className="bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 bg-clip-text text-transparent">
              ORGON
            </span>
          </h1>
          <p className="mx-auto max-w-2xl text-xl text-slate-600 dark:text-slate-400 font-light leading-relaxed">
            Прозрачное ценообразование. Без скрытых комиссий. Подходит обменникам, брокерам, банкам.
          </p>
        </motion.div>

        {/* Billing toggle */}
        <div className="flex justify-center mb-16">
          <div className="inline-flex rounded-full border border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.02] p-1">
            <button
              type="button"
              onClick={() => setBilling("monthly")}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-colors ${
                billing === "monthly"
                  ? "bg-emerald-500 text-white shadow"
                  : "text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              Помесячно
            </button>
            <button
              type="button"
              onClick={() => setBilling("yearly")}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-colors flex items-center gap-2 ${
                billing === "yearly"
                  ? "bg-emerald-500 text-white shadow"
                  : "text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              За год
              {yearlySavings !== null && (
                <span className="text-[10px] uppercase tracking-wide rounded-full bg-emerald-100 dark:bg-emerald-500/20 px-2 py-0.5 text-emerald-700 dark:text-emerald-300">
                  −{yearlySavings}%
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Loading / error state */}
        {!plans && !error && (
          <div className="text-center text-slate-500 dark:text-slate-400">Загрузка тарифов…</div>
        )}
        {error && (
          <div className="mx-auto max-w-md rounded-2xl border border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10 p-6 text-center text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Plans grid */}
        {plans && (
          <div className="grid gap-6 lg:grid-cols-3">
            {plans.map((plan, index) => {
              const visual = PLAN_VISUALS[plan.slug] ?? {
                gradient: "from-slate-500 to-slate-700",
                iconBg: "from-slate-500/10 to-slate-700/10",
                icon: "solar:tag-bold",
                tagline: "",
              };
              const featured = plan.slug === "business";
              const price =
                billing === "monthly" ? plan.monthly_price : plan.yearly_price;
              const featureItems = Object.entries(plan.features ?? {}).map(([k, v]) =>
                describeFeature(k, v),
              );

              return (
                <motion.div
                  key={plan.id}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.08 }}
                  className={`relative rounded-3xl border p-8 backdrop-blur-sm flex flex-col ${
                    featured
                      ? "border-emerald-500/40 bg-gradient-to-b from-emerald-500/[0.06] to-transparent shadow-xl shadow-emerald-500/10"
                      : "border-slate-200 dark:border-white/10 bg-white/60 dark:bg-white/[0.02]"
                  }`}
                >
                  {featured && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-emerald-500 px-3 py-1 text-xs font-semibold text-white">
                      Популярный
                    </div>
                  )}

                  <div
                    className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br ${visual.iconBg} border border-white/10 mb-6`}
                  >
                    <Icon icon={visual.icon} className="text-3xl text-slate-900 dark:text-white" />
                  </div>

                  <div className="mb-6">
                    <div className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
                      {visual.tagline || plan.description}
                    </div>
                    <h2 className="text-3xl font-display font-bold text-slate-900 dark:text-white">
                      {plan.name}
                    </h2>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-2 leading-relaxed">
                      {plan.description}
                    </p>
                  </div>

                  <div className="mb-8">
                    <div className="text-4xl font-bold text-slate-900 dark:text-white">
                      {formatPrice(price, plan.currency)}
                    </div>
                    <div className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                      {billing === "monthly" ? "за месяц" : "за год"}
                      {plan.margin_min ? ` · комиссия от ${plan.margin_min}%` : ""}
                    </div>
                  </div>

                  <ul className="space-y-3 mb-8 flex-1">
                    {featureItems.length === 0 && (
                      <li className="text-sm text-slate-500 dark:text-slate-400">
                        Свяжитесь с нами для деталей
                      </li>
                    )}
                    {featureItems.map((label) => (
                      <li key={label} className="flex items-start gap-3">
                        <Icon
                          icon="solar:check-circle-bold"
                          className="text-emerald-500 mt-0.5 flex-shrink-0 text-lg"
                        />
                        <span className="text-sm text-slate-700 dark:text-slate-300">{label}</span>
                      </li>
                    ))}
                  </ul>

                  <Link href="/register">
                    <Button variant={featured ? "primary" : "secondary"} fullWidth>
                      {plan.slug === "enterprise" ? "Связаться с продажами" : "Начать работу"}
                    </Button>
                  </Link>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* CTA bottom */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="mt-20 text-center"
        >
          <h3 className="text-2xl font-display font-semibold text-slate-900 dark:text-white mb-3">
            Не уверены какой тариф подойдёт?
          </h3>
          <p className="text-slate-600 dark:text-slate-400 mb-6 max-w-xl mx-auto">
            Расскажите про объёмы и специфику — подберём план или соберём индивидуальный пакет.
          </p>
          <Link href="mailto:sales@orgon.asystem.kg">
            <Button variant="primary" size="lg">
              <Icon icon="solar:letter-bold" className="text-xl mr-2" />
              Написать в продажи
            </Button>
          </Link>
        </motion.div>
      </div>
    </div>
  );
}
