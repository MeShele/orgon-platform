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
  provisioning_source: "manual" | "api" | string;
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
            <Pair
              label="Источник"
              value={
                <span
                  className={
                    m.provisioning_source === "api"
                      ? "rounded-full bg-primary/15 text-primary px-2 py-0.5 text-[10px]"
                      : "rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[10px]"
                  }
                  title={
                    m.provisioning_source === "api"
                      ? "Создан через POST /platform/merchants (asystem-core или другая автоматизация)"
                      : "Создан вручную через эту админку"
                  }
                >
                  {m.provisioning_source === "api" ? "API" : "Вручную"}
                </span>
              }
            />
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

        <TreasurySection merchantId={merchantId} />

        <DepositLookupSection merchantId={merchantId} />

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
    // The setState calls inside `load` all sit behind `await`, so the
    // render isn't synchronous — but the lint rule can't see across
    // the callback boundary. Suppress with explicit `void` to mark
    // the promise as fire-and-forget.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
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
    // Same false-positive as above — setState behind await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
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

type DepositRow = {
  id: string;
  wallet_id: string;
  end_user_id: string | null;
  network: number;
  tx_hash: string;
  log_index: number;
  from_address: string | null;
  to_address: string;
  asset: string;
  amount: string;
  confirmations: number;
  block_number: number | null;
  block_timestamp: string | null;
  discovered_at: string | null;
  status: string;
};

type LookupResponse = {
  tx_hash: string;
  found: boolean;
  deposits: DepositRow[];
  hint: string | null;
  offchain_lookup?: { supported: boolean; hint: string };
};

function DepositLookupSection({ merchantId }: { merchantId: string }) {
  const [txHash, setTxHash] = useState("");
  const [includeOffchain, setIncludeOffchain] = useState(false);
  const [searching, setSearching] = useState(false);
  const [result, setResult] = useState<LookupResponse | null>(null);
  const [error, setError] = useState("");

  const search = async () => {
    const trimmed = txHash.trim();
    if (!trimmed) {
      setError("Введите tx_hash для поиска");
      setResult(null);
      return;
    }
    setSearching(true);
    setError("");
    try {
      const r = (await api.lookupMerchantDeposit(merchantId, trimmed, includeOffchain)) as LookupResponse;
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Lookup не удался");
      setResult(null);
    } finally {
      setSearching(false);
    }
  };

  const reset = () => {
    setTxHash("");
    setResult(null);
    setError("");
    setIncludeOffchain(false);
  };

  return (
    <Card>
      <CardHeader
        title="Deposit lookup"
        subtitle='Поиск депозита по tx_hash. Используется поддержкой когда юзер пишет "я отправил, где деньги".'
      />
      <div className="p-4 space-y-3 text-xs">
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            value={txHash}
            onChange={(e) => setTxHash(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void search();
            }}
            placeholder="0xabc...  или  hash из тронскана"
            className={inputClass + " font-mono flex-1"}
            disabled={searching}
          />
          <div className="flex gap-2">
            <Button variant="primary" size="sm" onClick={() => void search()} disabled={searching}>
              {searching ? "Ищу…" : "Найти"}
            </Button>
            {(result || error) && (
              <Button variant="ghost" size="sm" onClick={reset}>
                Сбросить
              </Button>
            )}
          </div>
        </div>

        <label className="flex items-center gap-2 text-muted-foreground cursor-pointer select-none">
          <input
            type="checkbox"
            checked={includeOffchain}
            onChange={(e) => setIncludeOffchain(e.target.checked)}
            className="rounded border-border"
          />
          <span>Искать также вне наших wallet&apos;ов (сейчас зарезервировано на будущее)</span>
        </label>

        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-destructive">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-3">
            <div
              className={
                result.found
                  ? "rounded-lg border border-success/30 bg-success/5 p-3"
                  : "rounded-lg border border-warning/30 bg-warning/5 p-3"
              }
            >
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={
                    result.found
                      ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                      : "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
                  }
                >
                  {result.found ? `Найдено: ${result.deposits.length}` : "Не найдено"}
                </span>
                <span className="font-mono text-muted-foreground truncate">{result.tx_hash}</span>
              </div>
              {result.hint && (
                <p className="text-muted-foreground leading-relaxed mt-1">{result.hint}</p>
              )}
            </div>

            {result.deposits.map((d) => (
              <DepositResultRow key={`${d.id}-${d.log_index}`} deposit={d} />
            ))}

            {result.offchain_lookup && (
              <div className="rounded-lg border border-border bg-muted/30 p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[10px]">
                    Offchain
                  </span>
                  <span
                    className={
                      result.offchain_lookup.supported
                        ? "text-success"
                        : "text-muted-foreground"
                    }
                  >
                    {result.offchain_lookup.supported ? "доступно" : "пока не реализовано"}
                  </span>
                </div>
                <p className="text-muted-foreground leading-relaxed">
                  {result.offchain_lookup.hint}
                </p>
              </div>
            )}
          </div>
        )}

        {!result && !error && !searching && (
          <p className="text-muted-foreground italic">
            Введите tx_hash из эксплорера, чтобы найти депозит. Если депозит не найден — система объяснит вероятные причины и что сказать пользователю.
          </p>
        )}
      </div>
    </Card>
  );
}

function DepositResultRow({ deposit }: { deposit: DepositRow }) {
  return (
    <div className="rounded-lg border border-border bg-background p-3 space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[11px] font-medium">{deposit.amount} {deposit.asset}</span>
        <span
          className={
            deposit.status === "confirmed"
              ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
              : deposit.status === "pending"
              ? "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
              : "rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[10px]"
          }
        >
          {deposit.status}
        </span>
        <span className="font-mono text-[10px] text-muted-foreground">
          network {deposit.network}
        </span>
        <span className="text-[10px] text-muted-foreground ml-auto">
          {deposit.confirmations} confirmations
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-0.5 text-[10px] text-muted-foreground font-mono">
        <span>
          from:{" "}
          {deposit.from_address ? (
            <span className="text-foreground/80 break-all">{deposit.from_address}</span>
          ) : (
            "—"
          )}
        </span>
        <span>
          to: <span className="text-foreground/80 break-all">{deposit.to_address}</span>
        </span>
        {deposit.block_number && <span>block: {deposit.block_number}</span>}
        {deposit.block_timestamp && (
          <span>at: {new Date(deposit.block_timestamp).toLocaleString("ru-RU")}</span>
        )}
      </div>
    </div>
  );
}

type TreasuryWallet = {
  wallet_id: string;
  name: string | null;
  network: number | null;
  address: string | null;
  status: "active" | "pending";
  purpose: "treasury" | "fee" | "hot" | "cold" | string;
  end_user_id: string | null;
  as_of: string | null;
  balances: { token: string; value: string; decimals: string }[];
};

function TreasurySection({ merchantId }: { merchantId: string }) {
  const [data, setData] = useState<{ wallets: TreasuryWallet[] } | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const r = (await api.getMerchantTreasury(merchantId)) as { wallets: TreasuryWallet[] };
      setData(r);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить treasury");
      setData(null);
    }
  }, [merchantId]);

  useEffect(() => {
    // Same false-positive — setState behind await in `load`.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return (
    <Card>
      <CardHeader
        title="Treasury"
        subtitle="Кошельки мерчанта (treasury / fee / hot / cold). User-deposit адреса здесь не показываются — это per-user депозитные."
        action={
          <Button variant="ghost" size="sm" onClick={() => void load()}>
            Обновить
          </Button>
        }
      />
      <div className="p-4 text-xs">
        {error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-destructive">
            {error}
          </div>
        ) : data === null ? (
          <div className="text-muted-foreground">Загрузка балансов…</div>
        ) : data.wallets.length === 0 ? (
          <div className="text-muted-foreground">
            У этого merchant нет собственных treasury-кошельков.
            <br />
            Они появятся когда merchant создаст хотя бы один wallet с
            <code className="mx-1 rounded bg-muted px-1 font-mono">purpose=treasury/fee/hot/cold</code>
            через <code className="font-mono">POST /v1/wallets</code>.
          </div>
        ) : (
          <div className="space-y-3">
            {data.wallets.map((w) => (
              <TreasuryWalletRow key={w.wallet_id} wallet={w} />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function TreasuryWalletRow({ wallet }: { wallet: TreasuryWallet }) {
  const purposeColor =
    wallet.purpose === "treasury"
      ? "bg-primary/15 text-primary"
      : wallet.purpose === "fee"
      ? "bg-warning/15 text-warning"
      : wallet.purpose === "hot"
      ? "bg-success/15 text-success"
      : wallet.purpose === "cold"
      ? "bg-muted text-muted-foreground"
      : "bg-muted text-muted-foreground";
  const staleness = wallet.as_of ? stalenessLabel(wallet.as_of) : null;
  return (
    <div className="rounded-lg border border-border bg-muted/20 p-3">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <span className={`rounded-full px-2 py-0.5 text-[10px] ${purposeColor}`}>
          {wallet.purpose}
        </span>
        <span className="font-mono text-[11px] text-muted-foreground">
          network {wallet.network ?? "—"}
        </span>
        <span
          className={
            wallet.status === "active"
              ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
              : "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
          }
        >
          {wallet.status}
        </span>
        {staleness ? (
          <span
            className="text-[10px] text-muted-foreground ml-auto"
            title={`Последний sync балансов: ${wallet.as_of}`}
          >
            {staleness}
          </span>
        ) : (
          <span className="text-[10px] text-muted-foreground ml-auto">
            ещё не синхронизирован
          </span>
        )}
      </div>
      <div className="mb-2">
        <p className="font-mono text-[11px] break-all">
          {wallet.address || (
            <span className="text-muted-foreground">адрес ещё не активирован</span>
          )}
        </p>
        {wallet.name ? (
          <p className="text-[10px] text-muted-foreground mt-0.5 font-mono">
            name: {wallet.name}
          </p>
        ) : null}
      </div>
      {wallet.balances.length === 0 ? (
        <p className="text-muted-foreground italic">балансов пока нет</p>
      ) : (
        <div className="grid sm:grid-cols-2 gap-1">
          {wallet.balances.map((b) => (
            <div
              key={b.token}
              className="flex items-baseline justify-between rounded bg-background px-2 py-1"
            >
              <span className="font-mono text-[11px]">{b.token}</span>
              <span className="font-mono">{b.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function stalenessLabel(iso: string): string {
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return "";
  const seconds = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (seconds < 60) return `${seconds}с назад`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} мин назад`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч назад`;
  const days = Math.floor(hours / 24);
  return `${days} д назад`;
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
