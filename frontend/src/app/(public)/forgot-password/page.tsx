"use client";

import { useState, FormEvent } from "react";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

export default function ForgotPasswordPage() {
  const t = useTranslations("auth.forgotPassword");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || t("errors.serverError"));
      }
      setSent(true);
    } catch (err: any) {
      setError(err.message || t("errors.serverError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md border border-border bg-card p-8 sm:p-10">
        <Eyebrow dash tone="primary">Восстановление доступа</Eyebrow>
        <h1 className="mt-5 text-[28px] font-medium tracking-[-0.02em] text-foreground">
          {t("title")}
        </h1>
        <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

        {sent ? (
          <div className="mt-8 space-y-6">
            <div className="p-4 border border-success/40 bg-success/5 text-[13px] text-success">
              <Icon icon="solar:check-circle-bold" className="text-[18px] inline-block mr-2" />
              {t("success")}
            </div>
            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-[13px] text-primary hover:underline font-medium"
            >
              <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
              {t("backToLogin")}
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                {error}
              </div>
            )}

            <Input
              type="email"
              label={t("emailLabel")}
              placeholder={t("emailPlaceholder")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              autoComplete="email"
              mono
            />

            <Button type="submit" loading={loading} fullWidth size="md">
              {t("submitButton")}
              <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
            </Button>

            <Link
              href="/login"
              className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
            >
              <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
              {t("backToLogin")}
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
