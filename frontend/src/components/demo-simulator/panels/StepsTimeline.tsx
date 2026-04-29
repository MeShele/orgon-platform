"use client";

// Right-side documentation panel. Replaces the old bottom player —
// presents the scenario as a readable, vertical timeline of steps that
// auto-scrolls to track playback. Reads more like documentation than a
// playback controller, which matches the "objective walkthrough"
// vibe rather than "movie player".

import { useEffect, useRef } from "react";
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
  onRestart: () => void;
  /** Active step index (-1 when idle / before first or after last). */
  stepIndex: number;
}

export function StepsTimeline({
  scenarios, current, onSelect, onRestart, stepIndex,
}: Props) {
  const listRef = useRef<HTMLOListElement | null>(null);
  const activeRef = useRef<HTMLLIElement | null>(null);

  // Auto-scroll the active step into view as playback advances.
  useEffect(() => {
    if (activeRef.current && listRef.current) {
      activeRef.current.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [stepIndex]);

  return (
    <aside className="shrink-0 w-[400px] border-l border-border bg-card flex flex-col h-full">
      {/* Top bar — scenario picker + persona */}
      <header className="shrink-0 border-b border-border px-5 pt-4 pb-3 space-y-3">
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
          <button
            type="button"
            onClick={onRestart}
            title="Запустить заново"
            className={cn(
              "shrink-0 inline-flex items-center justify-center w-9 h-9 border border-border",
              "text-muted-foreground hover:text-foreground hover:bg-muted hover:border-strong",
              "transition-colors",
            )}
            aria-label="Запустить заново"
          >
            <Icon icon="solar:restart-linear" className="text-[15px]" />
          </button>
        </div>
      </header>

      {/* Scenario summary */}
      <div className="shrink-0 px-5 py-3 border-b border-border bg-muted/40">
        <p className="text-[12px] text-foreground leading-snug">
          {current.summary}
        </p>
      </div>

      {/* Vertical step list */}
      <ol
        ref={listRef}
        className="flex-1 overflow-y-auto px-5 py-4 space-y-3 relative"
      >
        {/* Vertical track behind the dots */}
        <div className="absolute left-[36px] top-4 bottom-4 w-px bg-border pointer-events-none" />

        {current.steps.map((step, i) => {
          const isActive = i === stepIndex;
          const isPast = stepIndex >= 0 && i < stepIndex;
          const tone = step.tone ?? "default";

          return (
            <li
              key={i}
              ref={isActive ? activeRef : null}
              className="relative pl-9"
            >
              {/* Dot */}
              <span
                aria-hidden
                className={cn(
                  "absolute left-[28px] top-2 w-4 h-4 rounded-full border-2 transition-all",
                  isActive && "bg-primary border-primary scale-125 shadow-[0_0_0_4px_rgba(156,24,37,0.18)]",
                  !isActive && isPast && "bg-success/30 border-success/40",
                  !isActive && !isPast && "bg-card border-border",
                )}
              />

              <div
                className={cn(
                  "rounded-md border p-3 transition-all duration-200",
                  isActive
                    ? "border-primary bg-primary/5 shadow-sm"
                    : isPast
                    ? "border-border/60 bg-card opacity-70"
                    : "border-border bg-card",
                )}
              >
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
                  <details
                    className="mt-2 group/payload"
                    open={isActive}
                  >
                    <summary className="cursor-pointer list-none flex items-center gap-1 font-mono text-[10px] tracking-tight text-faint hover:text-foreground transition-colors select-none">
                      <Icon icon="solar:alt-arrow-right-linear" className="text-[10px] group-open/payload:rotate-90 transition-transform" />
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
