"use client";

// Webhook settings page for the operator's own merchant. Linked from
// `/settings` admin tiles — previously orphan (Wave 38 / Sprint 12).
//
// What this page does today:
//   * Resolves the operator's merchant_id via /api/organizations (same
//     pattern the rest of /settings uses).
//   * Reuses ApiKeysSection's data path for parity with the rest of
//     the platform — the WebhookEditor and the delivery log live on
//     `/admin/merchants/[id]` because they're owned by platform admin.
//   * Surfaces a clear pointer to those admin pages for operators who
//     need to actually edit the URL or inspect deliveries.
//
// The page is intentionally minimal: full per-merchant webhook editor
// + delivery log is a richer flow at /admin/merchants/[id]. Building a
// second copy here would duplicate logic; instead we surface the
// fastest path to that page + read-only summary.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import { Icon } from "@/lib/icons";
import { api } from "@/lib/api";

type MerchantSummary = {
  id: string;
  name: string;
  slug: string;
  webhook_url: string | null;
  status: string;
  sandbox: boolean;
};

export default function WebhooksSettingsPage() {
  const [merchant, setMerchant] = useState<MerchantSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const orgs = await api.getOrganizations({ limit: 1 });
      const list = (Array.isArray(orgs)
        ? orgs
        : (orgs as { organizations?: unknown[] })?.organizations || []) as Array<{ id?: string }>;
      const first = list[0];
      if (!first?.id) {
        setError(
          "У вас нет привязанного merchant'а. " +
            "Создание merchant'а — на странице /admin/merchants (требует роли platform_admin).",
        );
        setLoading(false);
        return;
      }
      const m = (await api.getMerchant(first.id)) as MerchantSummary;
      setMerchant(m);
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Не удалось загрузить настройки webhook'а");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <Header title="Webhooks" />
      <div className="p-4 sm:p-6 lg:p-8 space-y-4 max-w-3xl">
        <Card>
          <CardHeader
            title="Webhook URL"
            subtitle="Куда ORGON шлёт события мерчанта (wallet.activated, wallet.deposit.detected, transaction.*, policy.triggered, …)"
          />
          <div className="p-4 text-xs space-y-3">
            {loading ? (
              <LoadingSpinner />
            ) : error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-destructive">
                {error}
              </div>
            ) : !merchant ? (
              <div className="text-muted-foreground">Нет данных.</div>
            ) : (
              <>
                <div className="space-y-2">
                  <p className="text-muted-foreground">Текущее значение:</p>
                  {merchant.webhook_url ? (
                    <p className="font-mono break-all text-foreground">{merchant.webhook_url}</p>
                  ) : (
                    <p className="text-muted-foreground italic">
                      не настроен — события копятся в очереди и истекут через 90 дней
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
                  <span className="text-muted-foreground">Merchant:</span>
                  <span className="font-medium text-foreground">{merchant.name}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {merchant.slug}
                  </span>
                  <span
                    className={
                      merchant.sandbox
                        ? "rounded-full bg-warning/15 text-warning px-2 py-0.5 text-[10px]"
                        : "rounded-full bg-success/15 text-success px-2 py-0.5 text-[10px]"
                    }
                  >
                    {merchant.sandbox ? "sandbox" : "live"}
                  </span>
                </div>

                <div className="pt-3 border-t border-border space-y-2">
                  <p className="text-muted-foreground">Что можно делать дальше:</p>
                  <Link
                    href={`/admin/merchants/${merchant.id}`}
                    className="inline-flex items-center gap-1.5 text-primary hover:underline"
                  >
                    <Icon icon="solar:pen-linear" />
                    Изменить URL или ротировать secret
                  </Link>
                  <br />
                  <Link
                    href={`/admin/merchants/${merchant.id}#deliveries`}
                    className="inline-flex items-center gap-1.5 text-primary hover:underline"
                  >
                    <Icon icon="solar:history-linear" />
                    Посмотреть журнал доставок
                  </Link>
                  <br />
                  <Link
                    href={`/admin/merchants/${merchant.id}#test`}
                    className="inline-flex items-center gap-1.5 text-primary hover:underline"
                  >
                    <Icon icon="solar:test-tube-linear" />
                    Отправить тестовое событие
                  </Link>
                </div>
              </>
            )}
          </div>
        </Card>

        <Card>
          <CardHeader
            title="Как это работает"
            subtitle="Контракт публикуется на /developers"
          />
          <div className="p-4 text-xs space-y-2 text-muted-foreground">
            <p>
              ORGON шлёт <code className="font-mono text-foreground">POST</code> на ваш URL с
              HMAC-подписью (SHA-256, заголовок{" "}
              <code className="font-mono text-foreground">X-ORGON-Webhook-Signature</code>).
              Полный контракт + примеры верификации —{" "}
              <Link href="/developers" className="text-primary hover:underline">
                /developers
              </Link>{" "}
              и{" "}
              <a
                href="/api/docs"
                target="_blank"
                rel="noreferrer noopener"
                className="text-primary hover:underline"
              >
                Swagger UI
              </a>
              .
            </p>
            <p>
              Retry: 6 попыток, расписание{" "}
              <code className="font-mono text-foreground">30s → 2m → 10m → 1h → 6h</code>{" "}
              (v1) или{" "}
              <code className="font-mono text-foreground">1m → 12m → 2h → 8h → 24h</code>{" "}
              (v2, env-flag). Replay-id (<code className="font-mono text-foreground">X-ORGON-Webhook-Id</code>)
              стабилен across retries — используйте для exactly-once дедупа.
            </p>
          </div>
        </Card>
      </div>
    </>
  );
}
