"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from '@/hooks/useTranslations';
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

export default function RegisterPage() {
  const t = useTranslations('auth.register');
  const tc = useTranslations('common');
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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    // Validation
    if (formData.password !== formData.confirmPassword) {
      setError(t('errors.passwordMismatch'));
      return;
    }

    if (formData.password.length < 8) {
      setError(t('errors.passwordTooShort'));
      return;
    }

    setLoading(true);

    try {
      await register(formData.email, formData.password, formData.fullName, formData.role);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || t('errors.emailExists'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
            {t('title')}
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            {t('subtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-500/20 rounded-lg text-sm text-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          <Input
            type="text"
            label={t('fullNameLabel')}
            placeholder={t('fullNamePlaceholder')}
            value={formData.fullName}
            onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
            required
            fullWidth
            autoFocus
          />

          <Input
            type="email"
            label={t('emailLabel')}
            placeholder={t('emailPlaceholder')}
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
            fullWidth
            autoComplete="email"
          />

          <Input
            type="password"
            label={t('passwordLabel')}
            placeholder={t('passwordPlaceholder')}
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            required
            fullWidth
            autoComplete="new-password"
            helperText={t('passwordPlaceholder')}
          />

          <Input
            type="password"
            label={t('confirmPasswordLabel')}
            placeholder={t('confirmPasswordPlaceholder')}
            value={formData.confirmPassword}
            onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
            required
            fullWidth
            autoComplete="new-password"
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('roleLabel')}
            </label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              <option value="viewer">{t('roles.viewer')}</option>
              <option value="signer">{t('roles.signer')}</option>
              <option value="admin">{t('roles.admin')}</option>
            </select>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {t('roleLabel')}
            </p>
          </div>

          <div className="flex items-start gap-2">
            <input
              type="checkbox"
              id="terms"
              required
              className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="terms" className="text-sm text-gray-700 dark:text-gray-300">
              {t('termsAgree')}{" "}
              <Link href="/terms" className="text-blue-600 dark:text-blue-400 hover:underline">
                {t('termsOfService')}
              </Link>
              {" "}{t('and')}{" "}
              <Link href="/privacy" className="text-blue-600 dark:text-blue-400 hover:underline">
                {t('privacyPolicy')}
              </Link>
            </label>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            loading={loading}
          >
            {t('createButton')}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-gray-600 dark:text-gray-400">
            {t('alreadyHaveAccount')}{" "}
          </span>
          <Link
            href="/login"
            className="text-blue-600 dark:text-blue-400 hover:underline font-medium"
          >
            {t('signInLink')}
          </Link>
        </div>
      </Card>
    </div>
  );
}
