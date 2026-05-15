"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";

const inputClass =
  "w-full rounded-lg border border-border bg-muted px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 transition-colors";

const selectClass = inputClass.replace("placeholder:text-muted-foreground", "");

export default function NewMerchantPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [kind, setKind] = useState<"exchanger" | "bank" | "exchange" | "internal">("exchanger");
  const [plan, setPlan] = useState<"sandbox" | "starter" | "growth" | "enterprise">("sandbox");
  const [sandbox, setSandbox] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const slugLooksValid = /^[a-z0-9][a-z0-9\-]*$/.test(slug);
  const canSubmit = name.trim().length >= 2 && slugLooksValid && !submitting;

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    setError("");
    try {
      const created = (await api.createMerchant({
        name: name.trim(),
        slug: slug.trim(),
        merchant_kind: kind,
        pricing_plan: plan,
        sandbox,
        webhook_url: webhookUrl.trim() || undefined,
      })) as { id: string; name: string };
      toast.success(`Merchant «${created.name}» создан`);
      router.replace(`/admin/merchants/${created.id}`);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Ошибка создания merchant'а";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Header title="Новый merchant" />
      <div className="p-4 sm:p-6 lg:p-8 max-w-2xl">
        <Card>
          <CardHeader
            title="Onboarding merchant"
            subtitle="Создаёт organization-row с merchant полями. API-ключи выпускаются после создания на странице merchant'а."
          />
          <form onSubmit={onSubmit} className="p-4 space-y-3 text-xs">
            <Field label="Название" hint="Имя tenant, видно в дашборде">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Криптообменник Foo"
                className={inputClass}
                maxLength={200}
              />
            </Field>
            <Field
              label="Slug"
              hint="Уникальный идентификатор: латиница, цифры и дефисы. Используется в URL и API."
            >
              <input
                value={slug}
                onChange={(e) =>
                  setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9\-]/g, ""))
                }
                placeholder="foo-exchange"
                className={`${inputClass} font-mono ${!slug || slugLooksValid ? "" : "border-destructive/60"}`}
                maxLength={60}
              />
            </Field>
            <Field label="Тип merchant">
              <select value={kind} onChange={(e) => setKind(e.target.value as never)} className={selectClass}>
                <option value="exchanger">Обменник</option>
                <option value="bank">Банк</option>
                <option value="exchange">Биржа</option>
                <option value="internal">Внутренний (нашего ASYSTEM)</option>
              </select>
            </Field>
            <Field label="Pricing plan">
              <select value={plan} onChange={(e) => setPlan(e.target.value as never)} className={selectClass}>
                <option value="sandbox">sandbox (без лимитов, только testnet)</option>
                <option value="starter">starter</option>
                <option value="growth">growth</option>
                <option value="enterprise">enterprise</option>
              </select>
            </Field>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={sandbox} onChange={(e) => setSandbox(e.target.checked)} />
              <span>
                Sandbox merchant — все ключи будут okt_*, работают только с testnet сетями.
              </span>
            </label>
            <Field label="Webhook URL" hint="Куда отправлять события. Можно настроить позже.">
              <input
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
                placeholder="https://api.merchant.com/orgon/webhook"
                className={`${inputClass} font-mono`}
                maxLength={500}
              />
            </Field>

            {error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-destructive">
                {error}
              </div>
            ) : null}

            <div className="flex justify-end gap-2 pt-3">
              <Button variant="secondary" size="md" onClick={() => router.back()} disabled={submitting}>
                Отмена
              </Button>
              <Button variant="primary" size="md" disabled={!canSubmit} loading={submitting}>
                Создать merchant
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-muted-foreground mb-1">{label}</label>
      {children}
      {hint ? <p className="mt-1 text-[10px] text-muted-foreground/80">{hint}</p> : null}
    </div>
  );
}
