"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ApiKeysSection } from "../../../settings/ApiKeysSection";
import { api } from "@/lib/api";

type Merchant = {
  id: string;
  name: string;
  slug: string;
  merchant_kind: string | null;
  pricing_plan: string | null;
  sandbox: boolean;
  status: string;
  webhook_url: string | null;
  api_keys_active: number;
  end_users_count: number;
  created_at: string;
};

const inputClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 transition-colors";

export default function MerchantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const merchantId = params.id as string;

  const [m, setM] = useState<Merchant | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const r = (await api.getMerchant(merchantId)) as Merchant;
      setM(r);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить merchant");
    } finally {
      setLoading(false);
    }
  }, [merchantId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onPatch = async (patch: Record<string, unknown>, successMsg: string) => {
    try {
      await api.updateMerchant(merchantId, patch);
      toast.success(successMsg);
      void refresh();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Не удалось обновить");
    }
  };

  if (loading) {
    return (
      <>
        <Header title="Merchant" />
        <div className="p-6"><LoadingSpinner /></div>
      </>
    );
  }
  if (error || !m) {
    return (
      <>
        <Header title="Merchant" />
        <div className="p-6">
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
            {error || "Не найден"}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Header title={m.name} />
      <div className="p-4 sm:p-6 lg:p-8 space-y-4 max-w-4xl">
        <Card>
          <CardHeader
            title={m.name}
            subtitle={m.slug}
            action={
              <Button
                variant={m.status === "active" ? "secondary" : "primary"}
                size="sm"
                onClick={() =>
                  onPatch(
                    { status: m.status === "active" ? "suspended" : "active" },
                    m.status === "active" ? "Merchant приостановлен" : "Merchant активирован",
                  )
                }
              >
                {m.status === "active" ? "Приостановить" : "Возобновить"}
              </Button>
            }
          />
          <div className="grid sm:grid-cols-2 gap-3 p-4 text-xs">
            <Pair label="Тип" value={m.merchant_kind ?? "—"} />
            <Pair
              label="Pricing plan"
              value={<Badge variant="outline">{m.pricing_plan ?? "—"}</Badge>}
            />
            <Pair
              label="Среда"
              value={
                <span
                  className={
                    m.sandbox
                      ? "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
                      : "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                  }
                >
                  {m.sandbox ? "sandbox" : "live"}
                </span>
              }
            />
            <Pair
              label="Статус"
              value={
                <span
                  className={
                    m.status === "active"
                      ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                      : "rounded-full bg-destructive/15 text-destructive px-2 py-0.5 text-[10px]"
                  }
                >
                  {m.status}
                </span>
              }
            />
            <Pair label="API-keys активных" value={String(m.api_keys_active)} />
            <Pair label="End-users" value={String(m.end_users_count)} />
            <Pair label="Создан" value={new Date(m.created_at).toLocaleString("ru-RU")} />
          </div>
        </Card>

        <Card>
          <CardHeader title="Webhook" subtitle="Адрес куда мы шлём события (HMAC-подписано)" />
          <WebhookEditor
            current={m.webhook_url}
            onSave={(url) => onPatch({ webhook_url: url }, "Webhook URL обновлён")}
          />
        </Card>

        <BillingSection merchantId={merchantId} planFromMerchant={m.pricing_plan} />

        <InvoicesSection merchantId={merchantId} />

        <ApiKeysSection merchantId={merchantId} />

        <div>
          <Button variant="ghost" size="sm" onClick={() => router.push("/admin/merchants")}>
            ← К списку merchants
          </Button>
        </div>
      </div>
    </>
  );
}

function BillingSection({ merchantId, planFromMerchant }: { merchantId: string; planFromMerchant: string | null }) {
  const [usage, setUsage] = useState<{
    plan: string;
    sandbox: boolean;
    limits: { api_calls: number; tx_count: number; active_users: number };
    today: { api_calls: number; tx_count: number; active_users: number };
    history: { day: string; api_calls: number; tx_count: number; active_users: number }[];
  } | null>(null);

  const load = useCallback(async () => {
    try {
      const u = (await api.getMerchantUsage(merchantId, 30)) as never;
      setUsage(u);
    } catch {
      setUsage(null);
    }
  }, [merchantId]);

  useEffect(() => {
    load();
  }, [load]);

  if (!usage) {
    return (
      <Card>
        <CardHeader title="Биллинг" subtitle={`План: ${planFromMerchant ?? "—"}`} />
        <div className="p-4 text-xs text-muted-foreground">Загрузка статистики…</div>
      </Card>
    );
  }

  const histMax = Math.max(1, ...usage.history.map((h) => h.api_calls));

  return (
    <Card>
      <CardHeader
        title="Биллинг"
        subtitle={`План: ${usage.plan}${usage.sandbox ? " · sandbox" : ""}`}
      />
      <div className="p-4 space-y-4 text-xs">
        <div className="grid sm:grid-cols-3 gap-3">
          <Metric
            label="API-запросы сегодня"
            used={usage.today.api_calls}
            limit={usage.limits.api_calls}
          />
          <Metric
            label="Транзакции сегодня"
            used={usage.today.tx_count}
            limit={usage.limits.tx_count}
          />
          <Metric
            label="Активные юзеры"
            used={usage.today.active_users}
            limit={usage.limits.active_users}
          />
        </div>
        {usage.history.length > 0 ? (
          <div>
            <p className="text-muted-foreground mb-2">API-запросы за 30 дней</p>
            <div className="flex items-end gap-0.5 h-16">
              {usage.history.map((h) => (
                <div
                  key={h.day}
                  className="flex-1 bg-primary/30 rounded-t"
                  style={{
                    height: `${Math.max(2, (h.api_calls / histMax) * 100)}%`,
                  }}
                  title={`${h.day}: ${h.api_calls} api / ${h.tx_count} tx / ${h.active_users} active`}
                />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </Card>
  );
}

function Metric({ label, used, limit }: { label: string; used: number; limit: number }) {
  const unlimited = limit < 0;
  const pct = unlimited ? 0 : Math.min(100, Math.round((used / Math.max(1, limit)) * 100));
  const tone = pct >= 90 ? "bg-destructive" : pct >= 70 ? "bg-warning" : "bg-success";
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-1.5">
      <p className="text-muted-foreground">{label}</p>
      <p className="text-base text-foreground font-mono">
        {used.toLocaleString("ru-RU")}{" "}
        {unlimited ? (
          <span className="text-muted-foreground text-[10px]">/ ∞</span>
        ) : (
          <span className="text-muted-foreground text-[10px]">/ {limit.toLocaleString("ru-RU")}</span>
        )}
      </p>
      {!unlimited ? (
        <div className="h-1 rounded-full bg-muted overflow-hidden">
          <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
        </div>
      ) : null}
    </div>
  );
}

type Invoice = {
  id: string;
  billing_period: string;
  plan: string;
  currency: string;
  amount_total: string;
  items: { label: string; amount: number; qty?: number; unit?: number; unit_per_1000?: number }[];
  api_calls_total: number;
  tx_count_total: number;
  status: "open" | "paid" | "void";
  issued_at: string | null;
  paid_at: string | null;
};

function InvoicesSection({ merchantId }: { merchantId: string }) {
  const [items, setItems] = useState<Invoice[] | null>(null);

  const load = useCallback(async () => {
    try {
      const r = (await api.listMerchantInvoices(merchantId, 24)) as { invoices: Invoice[] };
      setItems(r.invoices || []);
    } catch {
      setItems([]);
    }
  }, [merchantId]);

  useEffect(() => {
    load();
  }, [load]);

  const markPaid = async (invoiceId: string) => {
    try {
      await api.markInvoicePaid(merchantId, invoiceId);
      toast.success("Инвойс отмечен оплаченным");
      void load();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : "Ошибка");
    }
  };

  return (
    <Card>
      <CardHeader title="Инвойсы" subtitle="Генерируются автоматически 1-го числа каждого месяца" />
      <div className="p-4 text-xs">
        {items === null ? (
          <div className="text-muted-foreground">Загрузка…</div>
        ) : items.length === 0 ? (
          <div className="text-muted-foreground">
            Пока инвойсов нет. Первый сформируется 1-го числа следующего месяца.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-muted-foreground border-b border-border">
                <tr className="text-left">
                  <th className="py-2 pr-3 font-medium">Период</th>
                  <th className="py-2 pr-3 font-medium">План</th>
                  <th className="py-2 pr-3 font-medium text-right">API</th>
                  <th className="py-2 pr-3 font-medium text-right">TX</th>
                  <th className="py-2 pr-3 font-medium text-right">Сумма</th>
                  <th className="py-2 pr-3 font-medium">Статус</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {items.map((i) => (
                  <tr key={i.id}>
                    <td className="py-2 pr-3 font-mono">{i.billing_period}</td>
                    <td className="py-2 pr-3"><Badge variant="outline">{i.plan}</Badge></td>
                    <td className="py-2 pr-3 text-right font-mono">{i.api_calls_total.toLocaleString("ru-RU")}</td>
                    <td className="py-2 pr-3 text-right font-mono">{i.tx_count_total.toLocaleString("ru-RU")}</td>
                    <td className="py-2 pr-3 text-right font-mono">${i.amount_total}</td>
                    <td className="py-2 pr-3">
                      <span
                        className={
                          i.status === "paid"
                            ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                            : i.status === "void"
                            ? "rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[10px]"
                            : "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
                        }
                      >
                        {i.status}
                      </span>
                    </td>
                    <td className="py-2 pr-3">
                      {i.status === "open" ? (
                        <button
                          onClick={() => markPaid(i.id)}
                          className="text-primary hover:underline"
                        >
                          Отметить оплаченным
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Card>
  );
}

function Pair({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-muted-foreground mb-0.5">{label}</p>
      <div className="text-foreground">{value}</div>
    </div>
  );
}

function WebhookEditor({
  current,
  onSave,
}: {
  current: string | null;
  onSave: (url: string) => void;
}) {
  const [val, setVal] = useState(current ?? "");
  const [editing, setEditing] = useState(false);
  return (
    <div className="p-4 text-xs">
      {!editing ? (
        <div className="flex items-center justify-between gap-3">
          <span className="font-mono break-all">
            {current ? (
              current
            ) : (
              <span className="text-muted-foreground">не настроен</span>
            )}
          </span>
          <Button variant="secondary" size="sm" onClick={() => setEditing(true)}>
            Изменить
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <input
            value={val}
            onChange={(e) => setVal(e.target.value)}
            placeholder="https://api.merchant.com/orgon/webhook"
            className={inputClass + " font-mono"}
          />
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              onSave(val.trim());
              setEditing(false);
            }}
          >
            Сохранить
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setVal(current ?? "");
              setEditing(false);
            }}
          >
            Отмена
          </Button>
        </div>
      )}
    </div>
  );
}
