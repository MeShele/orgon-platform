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
