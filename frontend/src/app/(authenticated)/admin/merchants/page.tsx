"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import toast from "react-hot-toast";

import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { LastUpdated } from "@/components/common/LastUpdated";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";
import { useAutoRefresh } from "@/lib/useAutoRefresh";

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
  /** 'manual' = onboarded via /api/admin/merchants (this UI).
   *  'api'    = self-provisioned via /platform/merchants (e.g. asystem-core). */
  provisioning_source: "manual" | "api" | string;
};

const KIND_LABEL: Record<string, string> = {
  exchanger: "Обменник",
  bank: "Банк",
  exchange: "Биржа",
  internal: "Внутренний",
};

const SOURCE_LABEL: Record<string, { label: string; tone: string; tooltip: string }> = {
  manual: {
    label: "Вручную",
    tone: "bg-muted text-muted-foreground",
    tooltip: "Создан через эту админку (POST /api/admin/merchants).",
  },
  api: {
    label: "API",
    tone: "bg-primary/15 text-primary",
    tooltip:
      "Создан через POST /platform/merchants — обычно edge-функцией asystem-core при подключении нового оператора.",
  },
};

export default function AdminMerchantsPage() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const [items, setItems] = useState<Merchant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastSync, setLastSync] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchList = useCallback(async (opts: { silent?: boolean } = {}) => {
    if (opts.silent) setRefreshing(true);
    try {
      const data = (await api.listMerchants()) as Merchant[];
      setItems(Array.isArray(data) ? data : []);
      setError("");
      setLastSync(Date.now());
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Не удалось загрузить merchants";
      if (!opts.silent) setError(msg);
      if (msg.toLowerCase().includes("forbidden") || msg.includes("403")) {
        // Not a platform admin — soft-redirect to dashboard so the
        // user doesn't sit on an unhelpful error screen.
        router.replace("/dashboard");
      }
    } finally {
      if (!opts.silent) setLoading(false);
      if (opts.silent) setRefreshing(false);
    }
  }, [router]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);
  useAutoRefresh(() => fetchList({ silent: true }), 60_000);

  return (
    <>
      <Header title="Merchants" />
      <div className="p-4 sm:p-6 lg:p-8 space-y-4 max-w-6xl">
        <div className="flex items-end justify-between gap-3 flex-wrap">
          <div>
            <h2 className="text-2xl font-medium">
              {items.length} {plural(items.length, ["merchant", "merchants", "merchants"])}
            </h2>
            <div className="mt-1.5">
              <LastUpdated
                at={lastSync}
                refreshing={refreshing}
                onRefresh={() => fetchList({ silent: true })}
              />
            </div>
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={() => router.push("/admin/merchants/new")}
          >
            <Icon icon="solar:add-circle-bold" className="text-base" />
            Onboard merchant
          </Button>
        </div>

        {loading ? (
          <Card>
            <div className="p-8"><LoadingSpinner /></div>
          </Card>
        ) : error ? (
          <Card>
            <div className="p-4 text-xs text-destructive">{error}</div>
          </Card>
        ) : items.length === 0 ? (
          <Card>
            <div className="p-8 text-center text-xs text-muted-foreground">
              Ещё нет merchant-ов. Нажмите «Onboard merchant», чтобы создать первого.
            </div>
          </Card>
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-muted-foreground border-b border-border">
                  <tr className="text-left">
                    <th className="px-4 py-3 font-medium">Название</th>
                    <th className="px-3 py-3 font-medium">Тип</th>
                    <th className="px-3 py-3 font-medium">План</th>
                    <th className="px-3 py-3 font-medium">Среда</th>
                    <th className="px-3 py-3 font-medium">Статус</th>
                    <th
                      className="px-3 py-3 font-medium"
                      title="Откуда мерчант появился в системе"
                    >
                      Источник
                    </th>
                    <th className="px-3 py-3 font-medium text-right">API-keys</th>
                    <th className="px-3 py-3 font-medium text-right">Юзеры</th>
                    <th className="px-3 py-3 font-medium">Webhook</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {items.map((m, idx) => (
                    <motion.tr
                      key={m.id}
                      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.4,
                        ease: [0.22, 1, 0.36, 1],
                        delay: reduceMotion ? 0 : Math.min(idx * 0.05, 0.6),
                      }}
                      className="hover:bg-muted/40 cursor-pointer"
                      onClick={() => router.push(`/admin/merchants/${m.id}`)}
                    >
                      <td className="px-4 py-3">
                        <Link
                          href={`/admin/merchants/${m.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="font-medium hover:text-primary"
                        >
                          {m.name}
                        </Link>
                        <div className="text-[10px] text-muted-foreground font-mono">{m.slug}</div>
                      </td>
                      <td className="px-3 py-3 text-muted-foreground">
                        {m.merchant_kind ? KIND_LABEL[m.merchant_kind] ?? m.merchant_kind : "—"}
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant="outline">{m.pricing_plan ?? "—"}</Badge>
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={
                            m.sandbox
                              ? "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
                              : "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                          }
                        >
                          {m.sandbox ? "sandbox" : "live"}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <span
                          className={
                            m.status === "active"
                              ? "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                              : "rounded-full bg-destructive/15 text-destructive px-2 py-0.5 text-[10px]"
                          }
                        >
                          {m.status}
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        {(() => {
                          const src = SOURCE_LABEL[m.provisioning_source] ?? SOURCE_LABEL.manual;
                          return (
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] ${src.tone}`}
                              title={src.tooltip}
                            >
                              {src.label}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="px-3 py-3 text-right font-mono">{m.api_keys_active}</td>
                      <td className="px-3 py-3 text-right font-mono">{m.end_users_count}</td>
                      <td className="px-3 py-3 text-muted-foreground truncate max-w-xs">
                        {m.webhook_url ? (
                          <span className="font-mono text-[10px]">{m.webhook_url}</span>
                        ) : (
                          <span className="text-muted-foreground/60">не настроен</span>
                        )}
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </>
  );
}

function plural(n: number, forms: [string, string, string]) {
  const n10 = n % 10;
  const n100 = n % 100;
  if (n10 === 1 && n100 !== 11) return forms[0];
  if (n10 >= 2 && n10 <= 4 && (n100 < 12 || n100 > 14)) return forms[1];
  return forms[2];
}
