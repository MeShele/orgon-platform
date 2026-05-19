"use client";

// Public pricing page — surface the four-tier plan model the platform
// runs on (sandbox / starter / growth / enterprise). Real numbers in
// USD per the dfns-grade reference model documented in README.md.
//
// Linked from `Hero.tsx`, `(public)/about/page.tsx`,
// `(public)/features/page.tsx` — orphaned before Sprint 12 / Wave 38.
//
// `"use client"` because the Iconify integration in `@/lib/icons` is
// client-only — matches the pattern of other public pages (`/about`,
// `/features`).

import Link from "next/link";

import { PublicHeader } from "@/components/layout/PublicHeader";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";

type Plan = {
  name: string;
  tagline: string;
  priceUsd: string;
  priceSubtitle: string;
  features: string[];
  cta: { label: string; href: string };
  highlight?: boolean;
};

const PLANS: Plan[] = [
  {
    name: "Sandbox",
    tagline: "Для интеграции и тестов",
    priceUsd: "$0",
    priceSubtitle: "бесплатно, navсегда",
    features: [
      "Только testnet (5010 / 3040 / 5810)",
      "HMAC API + полный набор webhook'ов",
      "Self-service ключи через /platform/merchants",
      "Без SLA — пользуйтесь когда удобно",
    ],
    cta: { label: "Начать", href: "/register" },
  },
  {
    name: "Starter",
    tagline: "Малая обменка / fintech",
    priceUsd: "$299",
    priceSubtitle: "в месяц",
    features: [
      "Все networks (Tron / Ethereum / Bitcoin / ORGON-chain)",
      "До 10 000 API calls / день",
      "До 500 активных end-users",
      "AML rule engine + SAR pipeline",
      "Email-поддержка, ответ в течение 24ч",
    ],
    cta: { label: "Связаться", href: "mailto:support@orgon.asystem.kg" },
  },
  {
    name: "Growth",
    tagline: "Лицензированный VASP",
    priceUsd: "$1 499",
    priceSubtitle: "в месяц",
    features: [
      "Всё из Starter +",
      "До 100 000 API calls / день",
      "До 10 000 активных end-users",
      "Регуляторная отчётность Финнадзор КР (auto-email)",
      "Treasury endpoints для multi-wallet операций",
      "Telegram-поддержка с приоритетом",
    ],
    highlight: true,
    cta: { label: "Связаться", href: "mailto:support@orgon.asystem.kg" },
  },
  {
    name: "Enterprise",
    tagline: "Банк / биржа / mesh-платформа",
    priceUsd: "По запросу",
    priceSubtitle: "individual",
    features: [
      "Всё из Growth +",
      "Безлимит на API / users",
      "Per-tenant Postgres (data residency)",
      "M-of-N approval (E-08), Travel Rule (E-09)",
      "Dedicated SLA + on-call engineer",
      "Custom HMAC / mTLS / OAuth integration",
    ],
    cta: { label: "Связаться", href: "mailto:support@orgon.asystem.kg" },
  },
];

export default function PricingPage() {
  return (
    <>
      <PublicHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <header className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight text-foreground">
            Тарифы
          </h1>
          <p className="mt-3 text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto">
            Sandbox бесплатный навсегда — попробуйте интеграцию без обязательств.
            Платные тарифы — по факту использования, без скрытых процентов и
            эскроу-сборов сверху.
          </p>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PLANS.map((plan) => (
            <Card
              key={plan.name}
              className={
                plan.highlight
                  ? "ring-2 ring-primary/40 shadow-lg flex flex-col"
                  : "flex flex-col"
              }
            >
              <div className="p-5 flex flex-col h-full">
                {plan.highlight && (
                  <span className="inline-flex items-center gap-1 self-start rounded-full bg-primary/15 text-primary px-2 py-0.5 text-[10px] uppercase mb-2">
                    Популярный
                  </span>
                )}
                <h2 className="text-lg font-medium text-foreground">{plan.name}</h2>
                <p className="text-xs text-muted-foreground mt-0.5">{plan.tagline}</p>
                <div className="mt-4">
                  <p className="text-2xl font-semibold text-foreground">{plan.priceUsd}</p>
                  <p className="text-xs text-muted-foreground">{plan.priceSubtitle}</p>
                </div>
                <ul className="mt-5 space-y-2 text-xs text-foreground/90 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-2">
                      <Icon
                        icon="solar:check-circle-bold"
                        className="text-base text-success shrink-0 mt-0.5"
                      />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-6">
                  {plan.cta.href.startsWith("mailto:") ? (
                    <a
                      href={plan.cta.href}
                      className="block w-full text-center rounded-lg bg-primary text-primary-foreground px-3 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                      {plan.cta.label}
                    </a>
                  ) : (
                    <Link
                      href={plan.cta.href}
                      className="block w-full text-center rounded-lg bg-primary text-primary-foreground px-3 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
                    >
                      {plan.cta.label}
                    </Link>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>

        <section className="mt-12 text-sm text-muted-foreground space-y-3 max-w-3xl mx-auto">
          <p>
            Все тарифы включают полный custodial-stack: lazy wallet
            provisioning, multi-chain deposit watcher, AML rule engine,
            SAR pipeline под Финнадзор КР, webhook delivery с retry.
            Тариф ограничивает только лимиты по объёму — не функционал.
          </p>
          <p>
            Не нашли что нужно — напишите{" "}
            <a
              href="mailto:support@orgon.asystem.kg"
              className="text-primary hover:underline"
            >
              support@orgon.asystem.kg
            </a>{" "}
            или почитайте{" "}
            <Link href="/developers" className="text-primary hover:underline">
              developer onramp
            </Link>{" "}
            с copy-paste примерами интеграции.
          </p>
        </section>
      </main>
    </>
  );
}
