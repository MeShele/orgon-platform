"use client";
import { Icon } from "@/lib/icons";
export default function OrganizationSettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Icon icon="solar:buildings-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">Organization Settings</h1>
          <p className="text-sm text-muted-foreground">Branding, fiat gateways, API keys for your exchange</p>
        </div>
      </div>
      <div className="space-y-4">
        {[
          { title: "Company Profile", desc: "Name, contacts, registration details" },
          { title: "Branding", desc: "Logo, colors, custom domain for white-label" },
          { title: "Fiat Gateway", desc: "Bank API keys, payment processor integration" },
          { title: "API Keys", desc: "Programmatic access to wallets and transactions" },
        ].map((s) => (
          <div key={s.title} className="rounded-xl border border-border bg-card p-5 dark:border-border dark:bg-card hover:border-indigo-300 dark:hover:border-indigo-700 transition-colors cursor-pointer">
            <h3 className="font-semibold text-foreground">{s.title}</h3>
            <p className="text-sm text-muted-foreground">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
