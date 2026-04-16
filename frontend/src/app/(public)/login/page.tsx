"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from '@/hooks/useTranslations';
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { Icon } from "@/lib/icons";
import { MovingBorderButton } from "@/components/aceternity/moving-border";

export default function LoginPage() {
  const t = useTranslations('auth.login');
  const t2fa = useTranslations('settings.twofa');
  const tc = useTranslations('common');
  const router = useRouter();
  const { login: authLogin } = useAuth();
  
  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [twoFACode, setTwoFACode] = useState("");
  
  // Flow state
  const [step, setStep] = useState<'credentials' | '2fa'>('credentials');
  const [tempToken, setTempToken] = useState("");
  
  // UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCredentialsSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.login(email, password);

      // Check if 2FA is required
      if (response.requires_2fa) {
        setTempToken(response.temp_token);
        setStep('2fa');
        setLoading(false);
        return;
      }

      // No 2FA - complete login
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Login failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  // Quick login function
  const handleQuickLogin = async (quickEmail: string, quickPassword: string) => {
    setEmail(quickEmail);
    setPassword(quickPassword);
    setError("");
    setLoading(true);

    try {
      const response = await api.login(quickEmail, quickPassword);

      // Check if 2FA is required
      if (response.requires_2fa) {
        setTempToken(response.temp_token);
        setStep('2fa');
        setLoading(false);
        return;
      }

      // No 2FA - complete login
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      console.error('Quick login error:', err);
      setError(err.message || "Quick login failed. Please try manual login.");
    } finally {
      setLoading(false);
    }
  };

  const handle2FASubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (twoFACode.length !== 6) {
      setError(t2fa('errors.invalidCode'));
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await api.verify2FA(tempToken, twoFACode);

      // Login successful
      await authLogin(response);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || t2fa('errors.verificationFailed'));
      setTwoFACode(""); // Clear code on error
    } finally {
      setLoading(false);
    }
  };

  const handleBackToCredentials = () => {
    setStep('credentials');
    setTempToken("");
    setTwoFACode("");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4" suppressHydrationWarning>
      <Card className="w-full max-w-md">
        {/* Step 1: Email & Password */}
        {step === 'credentials' && (
          <>
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                {t('title')}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {t('subtitle')}
              </p>
            </div>

            <form onSubmit={handleCredentialsSubmit} className="space-y-6">
              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/20 rounded-lg text-sm text-red-700 dark:text-red-400">
                  {error}
                </div>
              )}

              <Input
                type="email"
                label={t('emailLabel')}
                placeholder={t('emailPlaceholder')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                fullWidth
                autoComplete="email"
                autoFocus
              />

              <Input
                type="password"
                label={t('passwordLabel')}
                placeholder={t('passwordPlaceholder')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                fullWidth
                autoComplete="current-password"
              />

              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  {t('rememberMe')}
                </label>
                <Link
                  href="/forgot-password"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {t('forgotPassword')}
                </Link>
              </div>

              <MovingBorderButton
                type="submit"
                duration={3000}
                disabled={loading}
                className="w-full"
              >
                <span className="flex items-center justify-center gap-2">
                  {loading && <Icon icon="solar:refresh-linear" className="animate-spin" />}
                  {t('signInButton')}
                </span>
              </MovingBorderButton>
            </form>

            <div className="mt-6 text-center text-sm">
              <span className="text-gray-600 dark:text-gray-400">
                {t('noAccount')}{" "}
              </span>
              <Link
                href="/register"
                className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                {t('signUpLink')}
              </Link>
            </div>

            <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-500/20 rounded-lg text-sm">
              <div className="text-blue-800 dark:text-blue-200 font-medium mb-3">
                {t('quickLoginTitle')}
              </div>
              
              {/* Quick Login Buttons by Role */}
              <div className="space-y-2">
                {/* Admin */}
                <button
                  type="button"
                  onClick={() => handleQuickLogin('demo-admin@orgon.io', 'demo2026')}
                  disabled={loading}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white dark:bg-slate-800 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-2">
                    <Icon icon="solar:shield-user-linear" className="text-red-600 dark:text-red-400" />
                    <div className="text-left">
                      <div className="text-xs font-semibold text-red-800 dark:text-red-200">Admin</div>
                      <div className="text-[10px] text-red-600 dark:text-red-400 font-mono">demo-admin@orgon.io</div>
                    </div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 font-medium">admin</span>
                </button>

                {/* Signer */}
                <button
                  type="button"
                  onClick={() => handleQuickLogin('demo-signer@orgon.io', 'demo2026')}
                  disabled={loading}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white dark:bg-slate-800 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-2">
                    <Icon icon="solar:pen-new-square-linear" className="text-amber-600 dark:text-amber-400" />
                    <div className="text-left">
                      <div className="text-xs font-semibold text-amber-800 dark:text-amber-200">Signer</div>
                      <div className="text-[10px] text-amber-600 dark:text-amber-400 font-mono">demo-signer@orgon.io</div>
                    </div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 font-medium">signer</span>
                </button>

                {/* Viewer */}
                <button
                  type="button"
                  onClick={() => handleQuickLogin('demo-viewer@orgon.io', 'demo2026')}
                  disabled={loading}
                  className="w-full flex items-center justify-between px-3 py-2 bg-white dark:bg-slate-800 border border-blue-300 dark:border-blue-700 rounded-lg hover:bg-blue-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-2">
                    <Icon icon="solar:eye-linear" className="text-blue-600 dark:text-blue-400" />
                    <div className="text-left">
                      <div className="text-xs font-semibold text-blue-800 dark:text-blue-200">Viewer</div>
                      <div className="text-[10px] text-blue-600 dark:text-blue-400 font-mono">demo-viewer@orgon.io</div>
                    </div>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium">viewer</span>
                </button>
              </div>

              <div className="mt-3 text-xs text-blue-600 dark:text-blue-400 text-center">
                {t('quickLoginOr')}
              </div>
            </div>
          </>
        )}

        {/* Step 2: 2FA Code */}
        {step === '2fa' && (
          <>
            <div className="text-center mb-8">
              <div className="mb-4">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto">
                  <Icon icon="solar:shield-check-bold" className="text-3xl text-blue-600 dark:text-blue-400" />
                </div>
              </div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                {t2fa('verificationCode')}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {t2fa('enterCode')}
              </p>
            </div>

            <form onSubmit={handle2FASubmit} className="space-y-6">
              {error && (
                <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/20 rounded-lg text-sm text-red-700 dark:text-red-400">
                  {error}
                </div>
              )}

              <div>
                <Input
                  type="text"
                  label={t2fa('verificationCode')}
                  placeholder="000000"
                  value={twoFACode}
                  onChange={(e) => setTwoFACode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  required
                  fullWidth
                  autoFocus
                  helperText={t2fa('enterCode')}
                />
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
                  {t2fa('enterCodeToDisable').replace('для отключения 2FA', '').replace('to disable 2FA', '')}
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleBackToCredentials}
                  fullWidth
                >
                  <Icon icon="solar:arrow-left-linear" className="mr-2" />
                  {tc('back')}
                </Button>
                <MovingBorderButton
                  type="submit"
                  duration={3000}
                  disabled={twoFACode.length !== 6 || loading}
                  className="flex-1"
                >
                  <span className="flex items-center justify-center gap-2">
                    {loading && <Icon icon="solar:refresh-linear" className="animate-spin" />}
                    {t2fa('verify')}
                  </span>
                </MovingBorderButton>
              </div>
            </form>

            <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm text-center">
              <div className="text-gray-600 dark:text-gray-400 whitespace-pre-line">
                {t2fa('backupCodeHelp')}
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
