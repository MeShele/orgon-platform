"use client";

import { Header } from "@/components/layout/Header";
import { Card } from "@/components/ui/Card";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { pageLayout } from "@/lib/page-layout";
import useSWR from "swr";

interface Plan {
  id: string;
  name: string;
  monthly_price: number;
  yearly_price: number;
  currency?: string;
  features?: string[];
  is_active?: boolean;
}

interface Usage {
  current_plan: string;
  billing_cycle: string;
  usage: {
    transactions: { used: number; limit: number };
    wallets: { used: number; limit: number };
    api_calls: { used: number; limit: number };
  };
  next_invoice_date: string | null;
  outstanding_balance: number;
}

const planLabel: Record<string, string> = {
  starter: "Стартовый",
  professional: "Профессиональный",
  enterprise: "Корпоративный",
};

export default function BillingPage() {
  const { data: plans } = useSWR<Plan[]>(
    "/api/v1/billing/plans",
    async () => {
      const data = await api.get("/api/v1/billing/plans");
      return Array.isArray(data) ? data : data.plans || [];
    }
  );

  const { data: usage } = useSWR<Usage>(
    "/api/v1/billing/usage",
    () => api.get("/api/v1/billing/usage")
  );

  const usagePercent = (used: number, limit: number) =>
    limit > 0 ? Math.min(Math.round((used / limit) * 100), 100) : 0;

  return (
    <>
      <Header title="Биллинг" />
      <div className={pageLayout.container}>
        {/* Текущий план и использование */}
        {usage && (
          <div className={pageLayout.grid.cols3}>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2.5">
                  <Icon icon="solar:star-bold" className="text-xl text-primary dark:text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{planLabel[usage.current_plan] || usage.current_plan}</p>
                  <p className="text-xs text-muted-foreground">Текущий план</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-success/10 p-2.5">
                  <Icon icon="solar:wallet-bold" className="text-xl text-success" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">${usage.outstanding_balance}</p>
                  <p className="text-xs text-muted-foreground">Текущий баланс</p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="p-4 flex items-center gap-3">
                <div className="rounded-lg bg-warning/10 p-2.5">
                  <Icon icon="solar:calendar-bold" className="text-xl text-warning" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{usage.billing_cycle === "monthly" ? "Месячный" : "Годовой"}</p>
                  <p className="text-xs text-muted-foreground">Цикл оплаты</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Использование */}
        {usage && (
          <Card>
            <div className="p-4 sm:p-6">
              <h3 className="text-base font-semibold text-foreground mb-4 flex items-center gap-2">
                <Icon icon="solar:chart-bold" className="text-primary" />
                Использование
              </h3>
              <div className="space-y-4">
                {[
                  { label: "Транзакции", data: usage.usage.transactions, icon: "solar:transfer-horizontal-bold" },
                  { label: "Кошельки", data: usage.usage.wallets, icon: "solar:wallet-bold" },
                  { label: "API-запросы", data: usage.usage.api_calls, icon: "solar:programming-bold" },
                ].map((item) => {
                  const pct = usagePercent(item.data.used, item.data.limit);
                  return (
                    <div key={item.label}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm text-foreground flex items-center gap-2">
                          <Icon icon={item.icon} className="text-muted-foreground" />
                          {item.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{item.data.used} / {item.data.limit}</span>
                      </div>
                      <div className="h-2 rounded-full bg-muted">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            pct > 80 ? "bg-destructive" : pct > 50 ? "bg-warning" : "bg-primary"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </Card>
        )}

        {/* Тарифные планы */}
        <div>
          <h3 className="text-base font-semibold text-foreground mb-3">Тарифные планы</h3>
          <div className={pageLayout.grid.cols3}>
            {plans && plans.map((plan) => {
              const isCurrent = usage?.current_plan === plan.id;
              return (
                <Card key={plan.id} className={isCurrent ? "ring-2 ring-indigo-500" : ""}>
                  <div className="p-4 sm:p-6">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-lg font-bold text-foreground">{planLabel[plan.id] || plan.name}</h4>
                      {isCurrent && (
                        <span className="inline-flex items-center rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary dark:text-primary">
                          Текущий
                        </span>
                      )}
                    </div>
                    <p className="text-3xl font-bold text-primary dark:text-primary">
                      ${plan.monthly_price}
                      <span className="text-sm font-normal text-muted-foreground">/мес</span>
                    </p>
                    {plan.yearly_price > 0 && (
                      <p className="text-xs text-muted-foreground mt-1">или ${plan.yearly_price}/год</p>
                    )}
                    {plan.features && (
                      <ul className="mt-4 space-y-2">
                        {plan.features.map((f, i) => (
                          <li key={i} className="text-sm text-muted-foreground flex items-center gap-2">
                            <Icon icon="solar:check-circle-bold" className="text-success text-sm flex-shrink-0" />
                            {f}
                          </li>
                        ))}
                      </ul>
                    )}
                    {!isCurrent && (
                      <button className="mt-4 w-full rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 transition-colors">
                        Выбрать план
                      </button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
