"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Eyebrow, BigNum, Mono } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

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

const FEATURE_LABELS: Record<string, string> = {
  // dfns-style 4-tier model
  all_interfaces:         "Все интерфейсы",
  max_wallets:            "Кошельков",
  max_team_members:       "Участников команды",
  max_blockchains:        "Блокчейнов",
  all_blockchains:        "Все блокчейны",
  unlimited_wallets:      "Кошельки без лимита",
  unlimited_team_members: "Команда без лимита",
  support_24h:            "Поддержка < 24 ч",
  support_1h:             "Поддержка < 1 ч",
  custom_pricing:         "Индивидуальная цена",
  // legacy keys (still present in older seeds, kept for backwards-compat)
  max_transactions:       "Транзакций / мес",
  tx_commission:          "Комиссия за транзакцию",
  crypto_acquiring:       "Крипто-эквайринг",
  kyc_price:              "KYC за пользователя ($)",
  basic_support:          "Базовая поддержка",
  priority_support:       "Приоритетная поддержка",
  dedicated_support:      "Выделенная поддержка",
  dedicated_manager:      "Персональный менеджер",
  api_access:             "API доступ",
  white_label:            "White-label",
  sla_24_7:               "SLA 24/7",
  unlimited_transactions: "Неограниченные транзакции",
};

function formatPrice(amount: string, currency: string): string {
  const n = Number(amount);
  if (Number.isNaN(n)) return amount;
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n)} ${currency}`;
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
    fetch(`/api/v1/billing/plans`)
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
    // Pick a non-Enterprise tier (Enterprise is custom-priced → 0).
    const sample = plans.find((p) => p.slug === "starter")
                ?? plans.find((p) => p.slug === "basic")
                ?? plans.find((p) => Number(p.monthly_price) > 0)
                ?? plans[0];
    if (!sample) return null;
    const monthly12 = Number(sample.monthly_price) * 12;
    const yearly = Number(sample.yearly_price);
    if (!monthly12 || !yearly) return null;
    const pct = Math.round((1 - yearly / monthly12) * 100);
    return pct > 0 ? pct : null;
  }, [plans]);

  return (
    <>
      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 pt-20 pb-12 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Тарифы</Eyebrow>
          <h1 className="mt-6 text-[44px] sm:text-[56px] lg:text-[64px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            Прозрачные тарифы<br />для команд любого масштаба
          </h1>
          <p className="mt-6 max-w-2xl mx-auto text-[15px] sm:text-[16px] leading-[1.6] text-muted-foreground">
            Цены в USD. Меняйте план в любой момент. Годовая оплата — со
            скидкой. Enterprise — индивидуальные условия по договору.
          </p>

          <div className="mt-10 inline-flex border border-strong p-0.5">
            {(["monthly", "yearly"] as const).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setBilling(opt)}
                className={cn(
                  "px-6 h-9 text-[13px] font-medium transition-colors flex items-center gap-2",
                  billing === opt ? "bg-foreground text-background" : "text-foreground hover:bg-muted",
                )}
              >
                {opt === "monthly" ? "Помесячно" : "За год"}
                {opt === "yearly" && yearlySavings !== null && (
                  <span className={cn("font-mono text-[10px] tracking-wider", billing === opt ? "text-background" : "text-primary")}>
                    −{yearlySavings}%
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* PLAN GRID */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-14">
          {!plans && !error && (
            <div className="text-center text-muted-foreground py-20">Загрузка тарифов…</div>
          )}
          {error && (
            <div className="mx-auto max-w-md border border-destructive/40 bg-destructive/5 p-6 text-center text-destructive">
              {error}
            </div>
          )}
          {plans && (
            <div className="grid lg:grid-cols-3 gap-px bg-border border border-border">
              {plans.map((plan, i) => {
                const featured = plan.slug === "business";
                const price = billing === "monthly" ? plan.monthly_price : plan.yearly_price;
                const features = Object.entries(plan.features ?? {}).map(([k, v]) => describeFeature(k, v));
                return (
                  <article
                    key={plan.id}
                    className={cn(
                      "p-8 lg:p-10 relative flex flex-col bg-card text-card-foreground",
                      featured && "ring-2 ring-primary -m-px",
                    )}
                  >
                    {featured && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2 font-mono text-[10px] tracking-[0.16em] uppercase text-primary-foreground bg-primary px-3 py-1">
                        Популярный
                      </div>
                    )}
                    <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-primary">
                      0{i + 1} / {plan.name.toUpperCase()}
                    </div>
                    <h2 className="mt-6 text-[32px] font-medium tracking-[-0.02em] text-foreground">
                      {plan.name}
                    </h2>
                    <p className="mt-2 text-[13px] leading-[1.5] text-muted-foreground">
                      {plan.description}
                    </p>

                    <div className="mt-7">
                      <div className="flex items-baseline gap-2">
                        <BigNum size="xxl" className="text-foreground">
                          {new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Number(price))}
                        </BigNum>
                        <span className="font-mono text-[12px] text-muted-foreground">
                          {plan.currency}
                        </span>
                      </div>
                      <Mono size="sm" className="mt-1 block text-muted-foreground">
                        {billing === "monthly" ? "/ месяц" : "/ год"}
                        {plan.margin_min ? ` · комиссия от ${plan.margin_min}%` : ""}
                      </Mono>
                    </div>

                    {plan.slug === "enterprise" ? (
                      <a
                        href="mailto:sales@orgon.asystem.kg?subject=ORGON%20Enterprise%20enquiry"
                        className="mt-8"
                      >
                        <Button variant="primary" fullWidth size="md">
                          Связаться с продажами
                          <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
                        </Button>
                      </a>
                    ) : (
                      <Link href="/register" className="mt-8">
                        <Button variant={featured ? "primary" : "secondary"} fullWidth size="md">
                          Выбрать план
                          <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
                        </Button>
                      </Link>
                    )}

                    <ul className="mt-8 pt-7 border-t border-border space-y-3">
                      {features.length === 0 && (
                        <li className="text-[13px] text-muted-foreground">
                          Свяжитесь с нами для подробностей
                        </li>
                      )}
                      {features.map((f) => (
                        <li key={f} className="flex items-start gap-2.5">
                          <Icon
                            icon="solar:check-circle-bold"
                            className="text-[16px] shrink-0 mt-0.5 text-success"
                          />
                          <span className="text-[13px] leading-[1.5] text-foreground">
                            {f}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <section className="border-b border-border bg-muted/40">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-10 py-20 text-center">
          <Eyebrow dash tone="primary" className="!justify-center">Не уверены</Eyebrow>
          <h2 className="mt-5 text-[28px] sm:text-[36px] font-medium tracking-[-0.025em] leading-[1.1] text-foreground">
            Подберём план под ваши объёмы
          </h2>
          <p className="mt-4 max-w-xl mx-auto text-[15px] text-muted-foreground leading-[1.6]">
            Расскажите про ваш кейс — биржа, обменник, банк или fintech — и
            покажем, как ORGON встраивается в вашу инфраструктуру.
          </p>
          <a
            href="mailto:sales@orgon.asystem.kg?subject=ORGON%20pricing%20enquiry"
            className="inline-block mt-8"
          >
            <Button variant="primary" size="lg">
              <Icon icon="solar:letter-bold" className="text-[16px]" />
              Написать в продажи
            </Button>
          </a>
        </div>
      </section>
    </>
  );
}
