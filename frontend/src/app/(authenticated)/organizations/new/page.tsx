"use client"

import { api } from "@/lib/api";;

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/Header";
import { Card, CardHeader } from "@/components/common/Card";
import { Icon } from "@/lib/icons";
import clsx from "clsx";

interface FormData {
  name: string;
  display_name: string;
  slug: string;
  license_type: "free" | "pro" | "enterprise";
  email: string;
  phone: string;
  address: string;
  city: string;
  country: string;
  max_wallets: number;
  max_monthly_volume: number;
  kyc_required: boolean;
}

export default function NewOrganizationPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const [formData, setFormData] = useState<FormData>({
    name: "",
    display_name: "",
    slug: "",
    license_type: "free",
    email: "",
    phone: "",
    address: "",
    city: "",
    country: "KG",
    max_wallets: 10,
    max_monthly_volume: 50000,
    kyc_required: true,
  });

  const handleChange = (field: keyof FormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Auto-generate slug from name
    if (field === "name" && !formData.slug) {
      const slug = value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
      setFormData(prev => ({ ...prev, slug }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.createOrganization(formData);
      
      
      // Redirect to organizations list
      router.push("/organizations");
    } catch (err: any) {
      setError(err.message || "Не удалось создать организацию");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="Новая организация" />

      <div className="p-2 sm:p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader title="Основная информация" />
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Название организации *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => handleChange("name", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="Acme Exchange"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Отображаемое имя
                  </label>
                  <input
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => handleChange("display_name", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="Acme"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Slug *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.slug}
                    onChange={(e) => handleChange("slug", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="acme-exchange"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    URL-идентификатор: только латиница, цифры и дефисы
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Тип лицензии *
                  </label>
                  <select
                    value={formData.license_type}
                    onChange={(e) => handleChange("license_type", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                  >
                    <option value="free">Бесплатный (10 кошельков, $10K / мес)</option>
                    <option value="pro">Pro (50 кошельков, $100K / мес)</option>
                    <option value="enterprise">Корпоративный (без лимитов)</option>
                  </select>
                </div>
              </div>
            </div>
          </Card>

          {/* Contact Information */}
          <Card>
            <CardHeader title="Контактная информация" />
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => handleChange("email", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="info@acme.kg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Телефон
                  </label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => handleChange("phone", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="+996 555 123456"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Адрес
                  </label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => handleChange("address", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="ул. Финансовая, 123"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Город *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.city}
                    onChange={(e) => handleChange("city", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    placeholder="Бишкек"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Страна *
                  </label>
                  <select
                    value={formData.country}
                    onChange={(e) => handleChange("country", e.target.value)}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                  >
                    <option value="KG">Кыргызстан</option>
                    <option value="KZ">Казахстан</option>
                    <option value="UZ">Узбекистан</option>
                    <option value="TJ">Таджикистан</option>
                    <option value="RU">Россия</option>
                  </select>
                </div>
              </div>
            </div>
          </Card>

          {/* Limits & Settings */}
          <Card>
            <CardHeader title="Лимиты и настройки" />
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Лимит кошельков
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.max_wallets}
                    onChange={(e) => handleChange("max_wallets", parseInt(e.target.value))}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Лимит оборота / мес (USD)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={formData.max_monthly_volume}
                    onChange={(e) => handleChange("max_monthly_volume", parseInt(e.target.value))}
                    className="w-full rounded-lg border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.kyc_required}
                      onChange={(e) => handleChange("kyc_required", e.target.checked)}
                      className="w-5 h-5 rounded border-border text-foreground focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    />
                    <div>
                      <span className="text-sm font-medium text-foreground">
                        Требовать KYC-верификацию
                      </span>
                      <p className="text-xs text-muted-foreground">
                        Включить проверку клиентов (Know Your Customer) для этой организации
                      </p>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </Card>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg bg-destructive/5 border border-destructive/30 p-4">
              <div className="flex items-start gap-3">
                <Icon icon="solar:danger-circle-bold" className="text-destructive text-xl flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-destructive">
                    Не удалось создать организацию
                  </p>
                  <p className="text-xs text-destructive mt-1">
                    {error}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => router.push("/organizations")}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium rounded-lg border border-border text-foreground hover:bg-muted dark:border-border dark:text-faint dark:hover:bg-muted transition-colors disabled:opacity-50"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={loading}
              className={clsx(
                "px-6 py-2 text-sm font-medium rounded-lg text-primary-foreground transition-colors disabled:opacity-50",
                loading
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-card hover:bg-muted dark:bg-white dark:text-foreground dark:hover:bg-muted"
              )}
            >
              {loading ? (
                <>
                  <Icon icon="solar:refresh-linear" className="inline animate-spin mr-2" />
                  Создание…
                </>
              ) : (
                <>
                  <Icon icon="solar:add-circle-linear" className="inline mr-2" />
                  Создать организацию
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
