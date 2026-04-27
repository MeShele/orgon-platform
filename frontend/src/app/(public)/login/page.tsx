"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "@/hooks/useTranslations";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Eyebrow, Mono } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";

const DEMO_ACCOUNTS = [
  { email: "demo-admin@orgon.io",  role: "Admin",  blurb: "полный доступ",        icon: "solar:shield-user-bold" },
  { email: "demo-signer@orgon.io", role: "Signer", blurb: "подписание транзакций", icon: "solar:pen-new-square-bold" },
  { email: "demo-viewer@orgon.io", role: "Viewer", blurb: "только просмотр",       icon: "solar:eye-bold" },
];

const DEMO_PASSWORD = "demo2026";

export default function LoginPage() {
  const t = useTranslations("auth.login");
  const t2fa = useTranslations("settings.twofa");
  const tc = useTranslations("common");
  const router = useRouter();
  const { login: authLogin } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFACode, setTwoFACode] = useState("");
  const [step, setStep] = useState<"credentials" | "2fa">("credentials");
  const [tempToken, setTempToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function performLogin(emailValue: string, passwordValue: string) {
    setError("");
    setLoading(true);
    try {
      const response = await api.login(emailValue, passwordValue);
      if (response.requires_2fa) {
        setTempToken(response.temp_token);
        setStep("2fa");
        setLoading(false);
        return;
      }
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
      setLoading(false);
    }
  }

  function handleCredentialsSubmit(e: FormEvent) {
    e.preventDefault();
    performLogin(email, password);
  }

  function handleQuickLogin(quickEmail: string) {
    setEmail(quickEmail);
    setPassword(DEMO_PASSWORD);
    performLogin(quickEmail, DEMO_PASSWORD);
  }

  async function handle2FASubmit(e: FormEvent) {
    e.preventDefault();
    if (twoFACode.length !== 6) {
      setError(t2fa("errors.invalidCode"));
      return;
    }
    setError("");
    setLoading(true);
    try {
      const response = await api.verify2FA(tempToken, twoFACode);
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || t2fa("errors.verificationFailed"));
      setTwoFACode("");
      setLoading(false);
    }
  }

  function handleBackToCredentials() {
    setStep("credentials");
    setTempToken("");
    setTwoFACode("");
    setError("");
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      {/* LEFT — light brand panel, paper */}
      <aside className="hidden lg:flex flex-col justify-between bg-muted border-r border-border p-14 relative overflow-hidden">
        <Link href="/" className="inline-flex items-center gap-3 relative z-10 text-foreground">
          <Image src="/orgon-icon.png" alt="ORGON" width={36} height={36} priority />
          <div className="flex flex-col leading-tight">
            <span className="font-mono text-[10px] tracking-[0.18em] text-faint">ASYSTEM</span>
            <span className="font-medium text-[16px] tracking-[0.06em] text-foreground">ORGON</span>
          </div>
        </Link>

        {/* Decorative concentric ring (crimson, low-opacity) */}
        <svg
          width={460}
          height={460}
          viewBox="0 0 460 460"
          className="absolute -top-20 -right-32 pointer-events-none"
          aria-hidden="true"
        >
          <circle cx={230} cy={230} r={220} fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.10} />
          <circle cx={230} cy={230} r={155} fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.12} />
          <circle cx={230} cy={230} r={95}  fill="none" stroke="var(--primary)" strokeWidth={1.2} opacity={0.16} />
          <circle cx={230} cy={230} r={35}  fill="var(--primary)" opacity={0.10} />
        </svg>

        <div className="relative z-10 max-w-lg">
          <Eyebrow tone="primary" dash>Институциональное кастоди</Eyebrow>
          <h2 className="mt-5 text-[40px] xl:text-[48px] font-medium tracking-[-0.025em] leading-[1.05] text-foreground">
            «Деньги в надёжных руках. Всегда — вместе.»
          </h2>
          <Mono size="md" className="mt-5 block text-muted-foreground">
            ASYSTEM · ORGON · институциональная мульти-подписная кастоди
          </Mono>
        </div>

        <div className="relative z-10 grid grid-cols-3 gap-3 font-mono text-[10px] tracking-[0.10em] uppercase text-faint">
          <div>M-of-N подписи</div>
          <div>FATF Travel Rule</div>
          <div>White-label API</div>
        </div>
      </aside>

      {/* RIGHT — auth card */}
      <main className="flex flex-col justify-center px-6 py-12 sm:px-10 lg:px-16">
        <div className="lg:hidden mb-8">
          <Link href="/" className="inline-flex items-center gap-3 text-foreground">
            <Image src="/orgon-icon.png" alt="ORGON" width={32} height={32} priority />
            <span className="font-medium text-[15px] tracking-[0.06em]">ORGON</span>
          </Link>
        </div>

        {step === "credentials" && (
          <div className="max-w-[420px] w-full">
            <h1 className="text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {t("title")}
            </h1>
            <p className="mt-2 text-[14px] text-muted-foreground">{t("subtitle")}</p>

            <form onSubmit={handleCredentialsSubmit} className="mt-8 space-y-5">
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
                autoComplete="email"
                autoFocus
                mono
              />

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="eyebrow">{t("passwordLabel")}</label>
                  <Link href="/forgot-password" className="text-[11px] font-mono tracking-[0.04em] text-primary hover:underline">
                    {t("forgotPassword")}
                  </Link>
                </div>
                <input
                  type="password"
                  placeholder="● ● ● ● ● ● ● ●"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="block w-full h-10 px-3 py-2 bg-card text-foreground placeholder:text-faint border border-border focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 font-mono text-[13px]"
                />
              </div>

              <Button type="submit" loading={loading} fullWidth size="md">
                {t("signInButton")}
                <Icon icon="solar:arrow-right-linear" className="text-[14px]" />
              </Button>
            </form>

            <div className="mt-6 text-[13px] text-muted-foreground">
              {t("noAccount")}{" "}
              <Link href="/register" className="text-primary hover:underline font-medium">
                {t("signUpLink")}
              </Link>
            </div>

            {/* Demo accounts */}
            <div className="mt-10 pt-8 border-t border-border">
              <Eyebrow>{t("quickLoginTitle")}</Eyebrow>
              <ul className="mt-4 space-y-2">
                {DEMO_ACCOUNTS.map((d) => (
                  <li key={d.email}>
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => handleQuickLogin(d.email)}
                      className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-card border border-border text-left hover:border-strong transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Icon icon={d.icon} className="text-[18px] text-primary shrink-0" />
                        <div className="min-w-0">
                          <div className="text-[13px] font-medium text-foreground truncate">
                            {d.role} · {d.blurb}
                          </div>
                          <Mono size="xs" className="text-muted-foreground truncate block">{d.email}</Mono>
                        </div>
                      </div>
                      <Icon icon="solar:arrow-right-linear" className="text-[14px] text-faint shrink-0" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {step === "2fa" && (
          <div className="max-w-[420px] w-full">
            <Icon icon="solar:shield-check-bold" className="text-[40px] text-primary" />
            <h1 className="mt-4 text-[28px] font-medium tracking-[-0.02em] text-foreground">
              {t2fa("verificationCode")}
            </h1>
            <p className="mt-2 text-[14px] text-muted-foreground">{t2fa("enterCode")}</p>

            <form onSubmit={handle2FASubmit} className="mt-8 space-y-5">
              {error && (
                <div className="p-3 border border-destructive/40 bg-destructive/5 text-[13px] text-destructive">
                  {error}
                </div>
              )}

              <Input
                type="text"
                label={t2fa("verificationCode")}
                placeholder="000000"
                value={twoFACode}
                onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                required
                autoFocus
                mono
              />

              <div className="flex gap-3">
                <Button type="button" variant="secondary" onClick={handleBackToCredentials} fullWidth>
                  <Icon icon="solar:arrow-left-linear" className="text-[14px]" />
                  {tc("back")}
                </Button>
                <Button type="submit" loading={loading} disabled={twoFACode.length !== 6} fullWidth>
                  {t2fa("verify")}
                </Button>
              </div>
            </form>

            <div className="mt-8 p-4 bg-muted text-[12px] text-muted-foreground whitespace-pre-line">
              {t2fa("backupCodeHelp")}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
