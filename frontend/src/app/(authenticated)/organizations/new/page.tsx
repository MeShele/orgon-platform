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
      setError(err.message || "Failed to create organization");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Header title="New Organization" />
      
      <div className="p-2 sm:p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader title="Basic Information" />
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Organization Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => handleChange("name", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    placeholder="Acme Exchange"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={formData.display_name}
                    onChange={(e) => handleChange("display_name", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
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
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    placeholder="acme-exchange"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    URL-friendly identifier (lowercase, hyphens)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    License Type *
                  </label>
                  <select
                    value={formData.license_type}
                    onChange={(e) => handleChange("license_type", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                  >
                    <option value="free">Free (10 wallets, $10K/mo)</option>
                    <option value="pro">Pro (50 wallets, $100K/mo)</option>
                    <option value="enterprise">Enterprise (Unlimited)</option>
                  </select>
                </div>
              </div>
            </div>
          </Card>

          {/* Contact Information */}
          <Card>
            <CardHeader title="Contact Information" />
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
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    placeholder="info@acme.kg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Phone
                  </label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => handleChange("phone", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    placeholder="+996 555 123456"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Address
                  </label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => handleChange("address", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    placeholder="ул. Финансовая, 123"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    City *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.city}
                    onChange={(e) => handleChange("city", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                    placeholder="Bishkek"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Country *
                  </label>
                  <select
                    value={formData.country}
                    onChange={(e) => handleChange("country", e.target.value)}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                  >
                    <option value="KG">Kyrgyzstan</option>
                    <option value="KZ">Kazakhstan</option>
                    <option value="UZ">Uzbekistan</option>
                    <option value="TJ">Tajikistan</option>
                    <option value="RU">Russia</option>
                  </select>
                </div>
              </div>
            </div>
          </Card>

          {/* Limits & Settings */}
          <Card>
            <CardHeader title="Limits & Settings" />
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Max Wallets
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={formData.max_wallets}
                    onChange={(e) => handleChange("max_wallets", parseInt(e.target.value))}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-foreground mb-2">
                    Max Monthly Volume (USD)
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={formData.max_monthly_volume}
                    onChange={(e) => handleChange("max_monthly_volume", parseInt(e.target.value))}
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card dark:text-white"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.kyc_required}
                      onChange={(e) => handleChange("kyc_required", e.target.checked)}
                      className="w-5 h-5 rounded border-slate-300 text-foreground focus:ring-2 focus:ring-primary/30 dark:border-border dark:bg-card"
                    />
                    <div>
                      <span className="text-sm font-medium text-foreground">
                        Require KYC Verification
                      </span>
                      <p className="text-xs text-muted-foreground">
                        Enable Know Your Customer verification for this organization
                      </p>
                    </div>
                  </label>
                </div>
              </div>
            </div>
          </Card>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4 dark:bg-red-950/20 dark:border-red-900">
              <div className="flex items-start gap-3">
                <Icon icon="solar:danger-circle-bold" className="text-destructive text-xl flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-900 dark:text-red-200">
                    Error Creating Organization
                  </p>
                  <p className="text-xs text-red-700 dark:text-red-300 mt-1">
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
              className="px-4 py-2 text-sm font-medium rounded-lg border border-slate-300 text-foreground hover:bg-muted dark:border-border dark:text-faint dark:hover:bg-muted transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={clsx(
                "px-6 py-2 text-sm font-medium rounded-lg text-white transition-colors disabled:opacity-50",
                loading
                  ? "bg-slate-400 cursor-not-allowed"
                  : "bg-card hover:bg-muted dark:bg-white dark:text-slate-950 dark:hover:bg-muted"
              )}
            >
              {loading ? (
                <>
                  <Icon icon="solar:refresh-linear" className="inline animate-spin mr-2" />
                  Creating...
                </>
              ) : (
                <>
                  <Icon icon="solar:add-circle-linear" className="inline mr-2" />
                  Create Organization
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
