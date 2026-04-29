"use client";

// Bottom-bar player for the architecture simulator.
// Shows: scenario picker, persona context, current step caption,
// and a Restart button (we play one scenario in a continuous loop —
// pause/scrub felt unnecessary for sales demos and adds complexity).

import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { Scenario, ScenarioStep } from "../scenarios/types";

const TONE_PILL: Record<NonNullable<ScenarioStep["tone"]>, string> = {
  default: "bg-primary/10 text-primary border-primary/30",
  success: "bg-success/10 text-success border-success/30",
  warning: "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30",
  danger:  "bg-destructive/10 text-destructive border-destructive/30",
  info:    "bg-primary/10 text-primary border-primary/30",
};

interface Props {
  scenarios: Scenario[];
  current: Scenario;
  onSelect: (s: Scenario) => void;
  onRestart: () => void;
  step: ScenarioStep | null;
  stepIndex: number;
}

export function ScenarioPlayer({
  scenarios, current, onSelect, onRestart, step, stepIndex,
}: Props) {
  return (
    <div className="border-t border-border bg-card">
      <div className="px-5 py-4 flex items-start gap-6 max-w-[1400px] mx-auto">
        {/* Persona / context */}
        <div className="shrink-0 w-[260px]">
          <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint">
            Сценарий
          </div>
          <div className="mt-0.5 text-[15px] font-medium text-foreground leading-tight">
            {current.title}
          </div>
          <div className="mt-2 flex items-center gap-2 text-[12px] text-muted-foreground">
            <span className="text-base leading-none">{current.persona.flag}</span>
            <span className="leading-tight">{current.persona.context}</span>
          </div>
        </div>

        {/* Current step */}
        <div className="flex-1 min-w-0">
          <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint">
            Текущий шаг {stepIndex >= 0 ? `${stepIndex + 1}/${current.steps.length}` : "·"}
          </div>
          <div className="mt-0.5 min-h-[40px] flex items-start gap-3">
            {step?.tone && (
              <span
                className={cn(
                  "shrink-0 mt-0.5 inline-flex items-center px-2 py-0.5 border rounded-sm",
                  "font-mono text-[9px] tracking-[0.12em] uppercase",
                  TONE_PILL[step.tone],
                )}
              >
                {step.tone === "danger" ? "blocked"
                  : step.tone === "warning" ? "alert"
                  : step.tone === "success" ? "ok"
                  : step.kind}
              </span>
            )}
            <div className="text-[14px] text-foreground leading-snug">
              {step
                ? step.caption
                : <span className="text-muted-foreground">Ожидание следующего цикла…</span>}
            </div>
          </div>
          {step?.payload && (
            <div className="mt-2 rounded-md border border-border bg-muted/40 p-2.5 max-w-[680px]">
              <div className="font-mono text-[10px] tracking-tight text-faint">
                {step.payload.label}
              </div>
              {step.payload.body && (
                <pre className="mt-1 font-mono text-[11px] text-muted-foreground whitespace-pre-wrap break-all">
                  {step.payload.body}
                </pre>
              )}
            </div>
          )}
        </div>

        {/* Scenario picker + restart */}
        <div className="shrink-0 flex flex-col items-end gap-2">
          <button
            onClick={onRestart}
            className={cn(
              "inline-flex items-center gap-2 px-3 h-9 border border-border bg-background",
              "text-[12px] font-medium text-foreground",
              "hover:bg-muted hover:border-strong transition-colors",
            )}
          >
            <Icon icon="solar:restart-linear" className="text-[14px]" />
            Запустить заново
          </button>
          <select
            value={current.id}
            onChange={(e) => {
              const next = scenarios.find((s) => s.id === e.target.value);
              if (next) onSelect(next);
            }}
            className={cn(
              "h-9 min-w-[260px] px-3 border border-border bg-background",
              "text-[12px] text-foreground",
              "focus:outline-none focus:ring-2 focus:ring-primary/30",
            )}
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.persona.flag} {s.title}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
