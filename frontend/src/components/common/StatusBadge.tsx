import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  pending:
    "bg-amber-50 text-amber-600 ring-amber-500/20 dark:bg-amber-500/10 dark:text-amber-400",
  signed:
    "bg-blue-50 text-blue-600 ring-blue-500/20 dark:bg-blue-500/10 dark:text-blue-400",
  confirmed:
    "bg-emerald-50 text-emerald-600 ring-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400",
  rejected:
    "bg-red-50 text-red-600 ring-red-500/20 dark:bg-red-500/10 dark:text-red-400",
  failed:
    "bg-red-50 text-red-600 ring-red-500/20 dark:bg-red-500/10 dark:text-red-400",
  ok: "bg-emerald-50 text-emerald-600 ring-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-400",
  error:
    "bg-red-50 text-red-600 ring-red-500/20 dark:bg-red-500/10 dark:text-red-400",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-lg px-3 py-1.5 text-xs font-semibold ring-1 ring-inset uppercase tracking-wide",
        statusStyles[status] ||
          "bg-slate-50 text-slate-600 ring-slate-500/20 dark:bg-slate-500/10 dark:text-slate-400"
      )}
    >
      {status}
    </span>
  );
}

export function StatusDot({ active = true }: { active?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center gap-1.5 rounded px-1.5 py-0.5 text-[10px] font-medium",
        active
          ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400"
          : "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400"
      )}
    >
      <span
        className={cn(
          "h-1 w-1 rounded-full",
          active ? "bg-emerald-500 dark:bg-emerald-400" : "bg-red-500 dark:bg-red-400"
        )}
      />
      {active ? "ok" : "down"}
    </div>
  );
}
