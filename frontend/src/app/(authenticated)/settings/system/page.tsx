"use client";
import { Icon } from "@/lib/icons";
export default function SystemSettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Icon icon="solar:server-bold" className="text-2xl text-primary" />
        <div>
          <h1 className="text-2xl font-bold text-foreground">System Settings</h1>
          <p className="text-sm text-muted-foreground">Monitoring, database connections, API health</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { title: "Safina API", status: "Connected", ok: true },
          { title: "Database", status: "Healthy", ok: true },
          { title: "Redis Cache", status: "Active", ok: true },
          { title: "WebSocket", status: "Running", ok: true },
        ].map((s) => (
          <div key={s.title} className="rounded-xl border border-border bg-card p-5 dark:border-border dark:bg-card">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-foreground">{s.title}</h3>
              <span className={`text-xs px-2 py-1 rounded-full ${s.ok ? "bg-emerald-100 text-success dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-destructive/10 text-destructive"}`}>{s.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
