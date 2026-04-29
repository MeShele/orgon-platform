"use client";

// Right-side reading panel. Pure documentation: scenario summary at
// the top, vertical numbered step list below. No "active step", no
// auto-scroll, no playback synchronisation — the graph is always
// alive, the panel is always readable, the two don't try to act in
// lockstep. User reads at their own pace.

import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { Scenario, ScenarioStep } from "../scenarios/types";

const TONE_PILL: Record<NonNullable<ScenarioStep["tone"]>, string> = {
  default: "bg-primary/10 text-primary border-primary/30",
  success: "bg-success/10 text-success border-success/30",
  warning: "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/40",
  danger:  "bg-destructive/10 text-destructive border-destructive/30",
  info:    "bg-primary/10 text-primary border-primary/30",
};

const TONE_LABEL: Record<NonNullable<ScenarioStep["tone"]>, string> = {
  default: "step",
  info:    "step",
  success: "ok",
  warning: "alert",
  danger:  "block",
};

interface Props {
  scenarios: Scenario[];
  current: Scenario;
  onSelect: (s: Scenario) => void;
}

export function StepsTimeline({ scenarios, current, onSelect }: Props) {
  return (
    <aside className="shrink-0 w-full lg:w-[400px] border-l border-border bg-card flex flex-col">
      {/* Top — scenario picker + persona context. Sticky on lg so the
          picker stays in reach while the user reads the step list below. */}
      <header
        className="shrink-0 border-b border-border px-5 pt-4 pb-3 space-y-3 bg-card lg:sticky lg:top-14 lg:z-20"
      >
        <div>
          <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-faint mb-1">
            Сценарий
          </div>
          <select
            value={current.id}
            onChange={(e) => {
              const next = scenarios.find((s) => s.id === e.target.value);
              if (next) onSelect(next);
            }}
            className={cn(
              "w-full h-10 px-3 border border-border bg-background",
              "text-[13px] font-medium text-foreground",
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

        <div className="flex items-start gap-2.5">
          <span className="text-xl leading-none mt-0.5">{current.persona.flag}</span>
          <div className="flex-1 min-w-0">
            <div className="text-[12px] font-medium text-foreground">
              {current.persona.label}
            </div>
            <div className="text-[11px] text-muted-foreground leading-snug">
              {current.persona.context}
            </div>
          </div>
        </div>
      </header>

      {/* Scenario summary */}
      <div className="shrink-0 px-5 py-3 border-b border-border bg-muted/40">
        <p className="text-[12px] text-foreground leading-snug">
          {current.summary}
        </p>
      </div>

      {/* Vertical static step list — flows with page scroll. */}
      <ol className="px-5 py-4 space-y-3 relative">
        {/* Vertical track behind the dots */}
        <div
          aria-hidden
          className="absolute left-[36px] top-4 bottom-4 w-px bg-border pointer-events-none"
        />

        {current.steps.map((step, i) => {
          const tone = step.tone ?? "default";
          return (
            <li key={i} className="relative pl-9">
              {/* Step dot */}
              <span
                aria-hidden
                className="absolute left-[28px] top-2 w-4 h-4 rounded-full bg-card border-2 border-border"
              />
              <div className="rounded-md border border-border bg-card p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-faint">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    className={cn(
                      "inline-flex items-center px-1.5 py-0.5 border rounded-sm",
                      "font-mono text-[9px] tracking-[0.12em] uppercase",
                      TONE_PILL[tone],
                    )}
                  >
                    {TONE_LABEL[tone]}
                  </span>
                </div>
                <p className="text-[12.5px] text-foreground leading-snug">
                  {step.caption}
                </p>
                {step.payload && (
                  <details className="mt-2 group/payload">
                    <summary className="cursor-pointer list-none flex items-center gap-1 font-mono text-[10px] tracking-tight text-faint hover:text-foreground transition-colors select-none">
                      <Icon
                        icon="solar:alt-arrow-right-linear"
                        className="text-[10px] group-open/payload:rotate-90 transition-transform"
                      />
                      {step.payload.label}
                    </summary>
                    {step.payload.body && (
                      <pre className="mt-1.5 px-2.5 py-2 border border-border bg-muted/40 rounded-sm font-mono text-[10.5px] text-muted-foreground whitespace-pre-wrap break-all leading-relaxed">
                        {step.payload.body}
                      </pre>
                    )}
                  </details>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {/* Bottom hint */}
      <footer className="shrink-0 border-t border-border px-5 py-3 bg-muted/30">
        <p className="text-[11px] text-muted-foreground leading-snug">
          Каждый узел графа кликабелен — откроется панель с описанием и
          ссылкой на код.
        </p>
      </footer>
    </aside>
  );
}
