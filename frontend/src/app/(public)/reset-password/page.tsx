"use client";

import { useState, FormEvent, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";

function ResetPasswordForm() {
  const t = useTranslations("auth.resetPassword");
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) return setError(t("errors.passwordTooShort"));
    if (password !== confirmPassword) return setError(t("errors.passwordMismatch"));
    if (!token) return setError(t("errors.invalidToken"));

    setLoading(true);
    try {
      const res = await fetch("/api/auth/reset-password/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || t("errors.serverError"));
      }
      setSuccess(true);
    } catch (err: any) {
      setError(err.message || t("errors.serverError"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 py-12">
      <div className="w-full max-w-md border border-border bg-card p-8 sm:p-10">
        <Eyebrow dash tone="primary">Новый пароль</Eyebrow>
        <h1 className="mt-5 text-[28px] font-medium tracking-[-0.02em] text-foreground">
          {t("title")}
        </h1>
        <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

        {success ? (
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
              Войти
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                {error}
              </div>
            )}
            {!token && !error && (
              <div className="p-3 border border-warning/40 bg-warning/5 text-[13px] text-warning">
                {t("errors.invalidToken")}
              </div>
            )}

            <Input
              type="password"
              label={t("passwordLabel")}
              placeholder={t("passwordPlaceholder")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
              autoComplete="new-password"
              mono
              helperText="Минимум 8 символов"
            />

            <Input
              type="password"
              label={t("confirmPasswordLabel")}
              placeholder={t("confirmPasswordPlaceholder")}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
              mono
            />

            <Button type="submit" loading={loading} disabled={!token} fullWidth size="md">
              {t("submitButton")}
              <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="font-mono text-[12px] text-faint">Загрузка…</div>
        </div>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
