"use client";
import { Icon } from "@/lib/icons";
export default function OrganizationSettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Icon icon="solar:buildings-bold" className="text-2xl text-indigo-500" />
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Organization Settings</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Branding, fiat gateways, API keys for your exchange</p>
        </div>
      </div>
      <div className="space-y-4">
        {[
          { title: "Company Profile", desc: "Name, contacts, registration details" },
          { title: "Branding", desc: "Logo, colors, custom domain for white-label" },
          { title: "Fiat Gateway", desc: "Bank API keys, payment processor integration" },
          { title: "API Keys", desc: "Programmatic access to wallets and transactions" },
        ].map((s) => (
          <div key={s.title} className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900 hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer">
            <h3 className="font-semibold text-slate-900 dark:text-white">{s.title}</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
