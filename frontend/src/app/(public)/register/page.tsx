"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Eyebrow } from "@/components/ui/primitives";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

const ROLES = [
  { value: "viewer", icon: "solar:eye-bold",          desc: "Просмотр данных без права действия" },
  { value: "signer", icon: "solar:pen-new-square-bold", desc: "Подписание транзакций" },
  { value: "admin",  icon: "solar:shield-user-bold",  desc: "Полный доступ к управлению" },
];

export default function RegisterPage() {
  const t = useTranslations("auth.register");
  const router = useRouter();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    fullName: "",
    role: "viewer",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError(t("errors.passwordMismatch"));
      return;
    }
    if (formData.password.length < 8) {
      setError(t("errors.passwordTooShort"));
      return;
    }

    setLoading(true);
    try {
      await register(formData.email, formData.password, formData.fullName, formData.role);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || t("errors.emailExists"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* LEFT — navy block */}
      <aside className="hidden lg:flex flex-col justify-between bg-navy text-navy-foreground p-14 relative overflow-hidden">
        <Link href="/" className="inline-flex items-center gap-3 relative z-10">
          <Image src="/orgon-icon.png" alt="ORGON" width={36} height={36} priority />
          <div className="flex flex-col leading-tight">
            <span className="font-mono text-[10px] tracking-[0.18em] text-white/55">ASYSTEM</span>
            <span className="font-medium text-[16px] tracking-[0.06em] text-white">ORGON</span>
          </div>
        </Link>

        <div className="relative z-10 max-w-lg">
          <Eyebrow tone="primary" dash>Создание аккаунта</Eyebrow>
          <h2 className="mt-5 text-[40px] xl:text-[44px] font-medium tracking-[-0.025em] leading-[1.05]">
            Подключитесь к ORGON
          </h2>
          <p className="mt-4 text-white/70 text-[15px] leading-[1.55]">
            После регистрации сможете создать первую организацию и пригласить
            подписантов. Полный доступ к B2B API сразу после KYB-верификации.
          </p>
        </div>

        <ul className="relative z-10 space-y-2 text-[12px] font-mono tracking-[0.04em] text-white/55">
          <li>· Multi-signature M-of-N до 7-of-15</li>
          <li>· White-label под собственный домен</li>
          <li>· FATF-совместимый аудит-лог</li>
        </ul>
      </aside>

      {/* RIGHT — form */}
      <main className="flex flex-col justify-center px-6 py-12 sm:px-10 lg:px-16">
        <div className="lg:hidden mb-8">
          <Link href="/" className="inline-flex items-center gap-3 text-foreground">
            <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} priority />
            <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
          </Link>
        </div>

        <div className="max-w-[480px] w-full">
          <h1 className="text-[28px] font-medium tracking-[-0.02em] text-foreground">
            {t("title")}
          </h1>
          <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                {error}
              </div>
            )}

            <Input
              type="text"
              label={t("fullNameLabel")}
              placeholder={t("fullNamePlaceholder")}
              value={formData.fullName}
              onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
              required
              autoFocus
            />

            <Input
              type="email"
              label={t("emailLabel")}
              placeholder={t("emailPlaceholder")}
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
              autoComplete="email"
              mono
            />

            <Input
              type="password"
              label={t("passwordLabel")}
              placeholder={t("passwordPlaceholder")}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
              autoComplete="new-password"
              helperText="Минимум 8 символов"
              mono
            />

            <Input
              type="password"
              label={t("confirmPasswordLabel")}
              placeholder={t("confirmPasswordPlaceholder")}
              value={formData.confirmPassword}
              onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
              required
              autoComplete="new-password"
              mono
            />

            <div>
              <div className="eyebrow mb-2">{t("roleLabel")}</div>
              <div className="grid grid-cols-3 gap-px bg-border border border-border">
                {ROLES.map((r) => {
                  const selected = formData.role === r.value;
                  return (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, role: r.value })}
                      className={cn(
                        "p-4 flex flex-col items-start gap-2 text-left transition-colors",
                        selected ? "bg-primary text-primary-foreground" : "bg-card hover:bg-muted",
                      )}
                    >
                      <Icon icon={r.icon} className="text-[20px]" />
                      <div>
                        <div className="text-[12px] font-medium uppercase tracking-[0.05em]">
                          {t(`roles.${r.value}`)}
                        </div>
                        <div
                          className={cn(
                            "mt-1 text-[11px] leading-[1.4]",
                            selected ? "text-primary-foreground/85" : "text-muted-foreground",
                          )}
                        >
                          {r.desc}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <label className="flex items-start gap-3 text-[12px] text-muted-foreground">
              <input
                type="checkbox"
                required
                className="mt-0.5 accent-primary"
              />
              <span>
                {t("termsAgree")}{" "}
                <Link href="/terms" className="text-primary hover:underline">
                  {t("termsOfService")}
                </Link>
                {" "}{t("and")}{" "}
                <Link href="/privacy" className="text-primary hover:underline">
                  {t("privacyPolicy")}
                </Link>
              </span>
            </label>

            <Button type="submit" loading={loading} fullWidth size="md">
              {t("createButton")}
              <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
            </Button>
          </form>

          <div className="mt-6 text-[13px] text-muted-foreground">
            {t("alreadyHaveAccount")}{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              {t("signInLink")}
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
