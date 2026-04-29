"use client";

// Per-feature mini-illustration for the /features page.
// Six visualisations, one per feature, sharing a common container so
// the section reads as a single design system. Each illustration is
// custom-built to communicate the concept rather than just be a big
// faded icon.

import { motion } from "framer-motion";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

const containerCls = "w-full max-w-[440px]";

// ─── 01 · Multi-signature ──────────────────────────────────────────

function MultiSigIllustration() {
  const signers = [
    { initials: "АН", role: "CFO",       signed: true,  delay: 0.1 },
    { initials: "БК", role: "CTO",       signed: true,  delay: 0.25 },
    { initials: "СМ", role: "Compliance", signed: false, delay: 0.4 },
  ];
  return (
    <div className={containerCls}>
      {/* TX header */}
      <div className="rounded-md border border-border bg-card p-3.5">
        <div className="flex items-center justify-between">
          <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-faint">
            Транзакция
          </div>
          <span className="inline-flex items-center px-1.5 py-0.5 border border-amber-300 bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/40 rounded-sm font-mono text-[9px] tracking-[0.12em] uppercase">
            2 / 3 · ожидает
          </span>
        </div>
        <div className="mt-2 font-mono text-[11px] text-foreground">
          TX_W3K · 50 000 USDT
        </div>
        <div className="mt-1 font-mono text-[10px] text-muted-foreground truncate">
          → TX9k…c4Z
        </div>
      </div>

      {/* connector */}
      <div className="my-2 flex justify-center">
        <div className="h-5 w-px bg-border" />
      </div>

      {/* Signers */}
      <div className="grid grid-cols-3 gap-2">
        {signers.map((s) => (
          <motion.div
            key={s.initials}
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: s.delay, duration: 0.4 }}
            className={cn(
              "rounded-md border bg-card p-2.5 text-center",
              s.signed ? "border-success/40" : "border-border",
            )}
          >
            <div
              className={cn(
                "mx-auto w-9 h-9 rounded-full flex items-center justify-center font-mono text-[11px] font-semibold",
                s.signed
                  ? "bg-success/10 text-success"
                  : "bg-muted text-muted-foreground",
              )}
            >
              {s.initials}
            </div>
            <div className="mt-1.5 text-[10.5px] text-foreground">{s.role}</div>
            <div className="mt-0.5 inline-flex items-center justify-center">
              <Icon
                icon={s.signed ? "solar:check-circle-bold" : "solar:clock-circle-linear"}
                className={cn(
                  "text-[12px]",
                  s.signed ? "text-success" : "text-muted-foreground",
                )}
              />
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

// ─── 02 · Schedule ─────────────────────────────────────────────────

function ScheduleIllustration() {
  // Mini calendar — 28 days, some marked.
  const marked = new Set([3, 7, 10, 14, 17, 21, 24, 28]);
  const today = 17;
  return (
    <div className={containerCls}>
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Icon icon="solar:calendar-mark-bold" className="text-[16px] text-primary" />
            <div className="text-[12px] font-medium text-foreground">Апрель 2026</div>
          </div>
          <div className="font-mono text-[10px] tracking-[0.16em] text-faint">8 ПЛАТЕЖЕЙ</div>
        </div>

        <div className="grid grid-cols-7 gap-1">
          {["П", "В", "С", "Ч", "П", "С", "В"].map((d) => (
            <div
              key={d}
              className="text-center font-mono text-[9px] tracking-[0.12em] uppercase text-faint pb-1"
            >
              {d}
            </div>
          ))}
          {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => {
            const isMarked = marked.has(d);
            const isToday = d === today;
            return (
              <div
                key={d}
                className={cn(
                  "aspect-square flex items-center justify-center rounded-sm text-[10.5px] font-mono",
                  isToday && "bg-primary text-primary-foreground font-semibold",
                  !isToday && isMarked && "bg-primary/10 text-primary border border-primary/30",
                  !isToday && !isMarked && "text-muted-foreground",
                )}
              >
                {d}
              </div>
            );
          })}
        </div>

        <div className="mt-3 flex items-center justify-between text-[10.5px]">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-primary" />
            <span className="text-muted-foreground">Запланированный платёж</span>
          </div>
          <code className="font-mono text-[9px] tracking-tight text-faint">
            cron: 0 9 */3 * *
          </code>
        </div>
      </div>
    </div>
  );
}

// ─── 03 · Analytics ────────────────────────────────────────────────

function AnalyticsIllustration() {
  const bars = [42, 58, 36, 71, 64, 88, 76];
  const max = Math.max(...bars);
  return (
    <div className={containerCls}>
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-faint">
              Объём 7 дней
            </div>
            <div className="mt-0.5 text-[20px] font-semibold tabular text-foreground">
              $ 4 312 580
            </div>
          </div>
          <div className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm bg-success/10 text-success">
            <Icon icon="solar:arrow-up-linear" className="text-[11px]" />
            <span className="font-mono text-[10.5px] font-medium">+18.4%</span>
          </div>
        </div>

        {/* Bars */}
        <div className="mt-4 flex items-end justify-between gap-1.5 h-[88px]">
          {bars.map((h, i) => {
            const pct = (h / max) * 100;
            return (
              <motion.div
                key={i}
                initial={{ height: 0 }}
                whileInView={{ height: `${pct}%` }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05, duration: 0.5, ease: "easeOut" }}
                className={cn(
                  "flex-1 rounded-sm",
                  i === bars.length - 1 ? "bg-primary" : "bg-primary/25",
                )}
              />
            );
          })}
        </div>
        <div className="mt-1.5 grid grid-cols-7 gap-1.5 font-mono text-[9px] tracking-[0.1em] text-faint text-center">
          {["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"].map((d) => (
            <div key={d}>{d}</div>
          ))}
        </div>

        {/* Mini stats row */}
        <div className="mt-3 grid grid-cols-3 gap-2 pt-3 border-t border-border">
          {[
            { l: "Подписей", v: "284" },
            { l: "Кошельков", v: "47" },
            { l: "Сетей", v: "5" },
          ].map((s) => (
            <div key={s.l}>
              <div className="text-[15px] font-semibold tabular text-foreground">{s.v}</div>
              <div className="font-mono text-[9px] tracking-[0.12em] uppercase text-faint mt-0.5">
                {s.l}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── 04 · Address Book ─────────────────────────────────────────────

function AddressBookIllustration() {
  const contacts = [
    { initials: "БК", name: "Binance Custody",    addr: "0xa1B…d5F", tag: "Биржа",     fav: true },
    { initials: "Б1", name: "Бинанс KZ payouts",   addr: "TR9k…c4Z", tag: "Расчёт",    fav: false },
    { initials: "ХК", name: "Hot wallet · USDT",   addr: "TX42…8a1", tag: "Внутренний", fav: true },
    { initials: "ЛЛ", name: "Liquidity Lab",       addr: "0x77F…12c", tag: "Партнёр",   fav: false },
  ];
  return (
    <div className={containerCls}>
      <div className="rounded-md border border-border bg-card overflow-hidden">
        <div className="px-3.5 py-2.5 border-b border-border flex items-center justify-between">
          <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-faint">
            Адресная книга
          </div>
          <Icon icon="solar:magnifer-linear" className="text-[13px] text-muted-foreground" />
        </div>
        <ul className="divide-y divide-border">
          {contacts.map((c, i) => (
            <motion.li
              key={c.name}
              initial={{ opacity: 0, x: -8 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06, duration: 0.35 }}
              className="px-3.5 py-2.5 flex items-center gap-3"
            >
              <div className="shrink-0 w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center font-mono text-[11px] font-semibold">
                {c.initials}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-medium text-foreground truncate flex items-center gap-1.5">
                  {c.name}
                  {c.fav && <Icon icon="solar:star-bold" className="text-[11px] text-amber-500" />}
                </div>
                <div className="font-mono text-[10.5px] text-muted-foreground truncate">
                  {c.addr}
                </div>
              </div>
              <span className="shrink-0 inline-flex items-center px-1.5 py-0.5 border border-border rounded-sm font-mono text-[9px] tracking-[0.12em] uppercase text-muted-foreground">
                {c.tag}
              </span>
            </motion.li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// ─── 05 · Audit Log ────────────────────────────────────────────────

function AuditIllustration() {
  const lines = [
    { ts: "14:33", actor: "admin@kz",       action: "tx.signed",     ref: "TX_W3K", tone: "ok" as const },
    { ts: "14:33", actor: "system",         action: "tx.broadcast",  ref: "TX_W3K", tone: "ok" as const },
    { ts: "14:31", actor: "compliance@kz",  action: "aml.review",    ref: "TX_J17", tone: "alert" as const },
    { ts: "14:28", actor: "system",         action: "rls.context",   ref: "org_7f3", tone: "step" as const },
    { ts: "14:27", actor: "operator@kz",    action: "tx.created",    ref: "TX_J17", tone: "step" as const },
  ];
  const TONE: Record<string, string> = {
    ok:    "text-success",
    alert: "text-amber-600 dark:text-amber-300",
    step:  "text-primary",
    block: "text-destructive",
  };
  return (
    <div className={containerCls}>
      <div className="rounded-md border border-border bg-foreground/[0.03] dark:bg-card overflow-hidden">
        <div className="px-3.5 py-2.5 border-b border-border bg-card flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon icon="solar:document-text-bold" className="text-[14px] text-foreground" />
            <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-faint">
              audit_log
            </span>
          </div>
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 border border-success/40 bg-success/5 text-success rounded-sm font-mono text-[9px] tracking-[0.12em] uppercase">
            <Icon icon="solar:lock-keyhole-bold" className="text-[10px]" />
            append-only
          </span>
        </div>
        <ol className="font-mono text-[10.5px] divide-y divide-border">
          {lines.map((l, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.07, duration: 0.3 }}
              className="px-3.5 py-2 flex items-center gap-2.5"
            >
              <span className="text-faint w-9">{l.ts}</span>
              <span className={cn("font-semibold w-[88px] truncate", TONE[l.tone])}>
                {l.action}
              </span>
              <span className="text-muted-foreground flex-1 truncate">{l.actor}</span>
              <span className="text-foreground">{l.ref}</span>
            </motion.li>
          ))}
        </ol>
      </div>
    </div>
  );
}

// ─── 06 · Networks ─────────────────────────────────────────────────

function NetworksIllustration() {
  const nets = [
    { name: "Tron",        sym: "TRX",  color: "bg-rose-500/10 text-rose-600 border-rose-300/40 dark:text-rose-300 dark:border-rose-500/30",       active: true  },
    { name: "Ethereum",    sym: "ETH",  color: "bg-indigo-500/10 text-indigo-600 border-indigo-300/40 dark:text-indigo-300 dark:border-indigo-500/30", active: true  },
    { name: "BNB Chain",   sym: "BNB",  color: "bg-amber-500/10 text-amber-700 border-amber-300/40 dark:text-amber-300 dark:border-amber-500/30",     active: true  },
    { name: "Polygon",     sym: "POL",  color: "bg-violet-500/10 text-violet-600 border-violet-300/40 dark:text-violet-300 dark:border-violet-500/30", active: true  },
    { name: "Bitcoin",     sym: "BTC",  color: "bg-orange-500/10 text-orange-600 border-orange-300/40 dark:text-orange-300 dark:border-orange-500/30",  active: true  },
    { name: "Solana",      sym: "SOL",  color: "bg-emerald-500/10 text-emerald-600 border-emerald-300/40 dark:text-emerald-300 dark:border-emerald-500/30", active: false },
  ];
  return (
    <div className={containerCls}>
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-faint">
            Поддерживаемые сети
          </div>
          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-sm bg-success/10 text-success font-mono text-[9px] tracking-[0.12em] uppercase">
            <span className="w-1 h-1 rounded-full bg-success animate-pulse" />
            live
          </span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {nets.map((n, i) => (
            <motion.div
              key={n.sym}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              className={cn(
                "rounded-md border px-2.5 py-3 flex flex-col items-center justify-center text-center",
                n.color,
                !n.active && "opacity-40",
              )}
            >
              <div className="font-mono text-[15px] font-semibold tracking-tight">{n.sym}</div>
              <div className="text-[10.5px] mt-0.5 leading-tight">{n.name}</div>
              {!n.active && (
                <span className="mt-1 font-mono text-[8px] tracking-[0.14em] uppercase text-muted-foreground">
                  скоро
                </span>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Switchboard ──────────────────────────────────────────────────

const ILLUSTRATIONS = [
  MultiSigIllustration,
  ScheduleIllustration,
  AnalyticsIllustration,
  AddressBookIllustration,
  AuditIllustration,
  NetworksIllustration,
];

export function FeatureIllustration({ index }: { index: number }) {
  const Component = ILLUSTRATIONS[index] ?? ILLUSTRATIONS[0];
  return <Component />;
}
