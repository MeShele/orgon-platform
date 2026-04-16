"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Icon } from "@/lib/icons";
import { MermaidDiagram } from "./MermaidDiagram";
import { diagrams } from "@/lib/help-content";

type HelpModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  diagramKey: string;
};

export function HelpModal({ open, onOpenChange, title, diagramKey }: HelpModalProps) {
  const chart = diagrams[diagramKey];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm animate-in fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900 animate-in fade-in-0 zoom-in-95">
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-sm font-medium text-slate-900 dark:text-white">
              {title}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button className="rounded-lg p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
                <Icon icon="solar:close-circle-linear" className="text-lg" />
              </button>
            </Dialog.Close>
          </div>
          {chart ? (
            <div className="overflow-auto rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50">
              <MermaidDiagram chart={chart} />
            </div>
          ) : (
            <p className="text-xs text-slate-500">No diagram available for key: {diagramKey}</p>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
