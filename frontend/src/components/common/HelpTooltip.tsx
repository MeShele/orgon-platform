"use client";

import * as Tooltip from "@radix-ui/react-tooltip";
import { Icon } from "@/lib/icons";
import { useState } from "react";
import { HelpModal } from "./HelpModal";

type HelpTooltipProps = {
  text: string;
  example?: string;
  tips?: readonly string[];
  diagram?: string;
  side?: "top" | "bottom" | "left" | "right";
};

export function HelpTooltip({ text, example, tips, diagram, side = "top" }: HelpTooltipProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <Tooltip.Root delayDuration={200}>
        <Tooltip.Trigger asChild>
          <button
            type="button"
            onClick={diagram ? () => setModalOpen(true) : undefined}
            className="inline-flex items-center justify-center rounded-full text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 transition-colors cursor-help"
          >
            <Icon icon="solar:question-circle-linear" className="text-sm" />
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side={side}
            sideOffset={4}
            className="z-50 max-w-sm rounded-lg bg-slate-900 px-4 py-3 text-xs text-white shadow-xl border border-slate-700 dark:bg-slate-800 animate-in fade-in-0 zoom-in-95"
          >
            <div className="space-y-2">
              {/* Main text */}
              <div className="font-medium text-slate-100">{text}</div>
              
              {/* Example */}
              {example && (
                <div className="pt-2 border-t border-slate-700">
                  <div className="text-slate-400 mb-1">Пример:</div>
                  <div className="text-cyan-400 font-mono text-[10px] bg-slate-950/50 px-2 py-1 rounded">
                    {example}
                  </div>
                </div>
              )}
              
              {/* Tips */}
              {tips && tips.length > 0 && (
                <div className="pt-2 border-t border-slate-700">
                  <div className="text-slate-400 mb-1.5">💡 Подсказки:</div>
                  <ul className="space-y-1">
                    {tips.map((tip, idx) => (
                      <li key={idx} className="flex items-start gap-1.5 text-slate-300">
                        <span className="text-cyan-400 mt-0.5">•</span>
                        <span className="flex-1">{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Diagram link */}
              {diagram && (
                <div className="pt-2 text-slate-400 text-center">
                  (кликните на ? для диаграммы)
                </div>
              )}
            </div>
            <Tooltip.Arrow className="fill-slate-900 dark:fill-slate-800" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
      {diagram && (
        <HelpModal
          open={modalOpen}
          onOpenChange={setModalOpen}
          title={text}
          diagramKey={diagram}
        />
      )}
    </>
  );
}
