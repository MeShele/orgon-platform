"use client";

// Right-side drawer that opens when a graph node is clicked.
// Shows what the node represents in plain Russian + actual code refs +
// sample HTTP/SQL/JSON. Designed to read like documentation — when a
// technical buyer clicks "Signature Service" they see what's there.

import { motion, AnimatePresence } from "framer-motion";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { NodeData, NodeKind } from "../graph-config";

const KIND_LABEL: Record<NodeKind, string> = {
  client:   "Клиентская сторона",
  auth:     "Слой аутентификации",
  policy:   "Бизнес-правила",
  core:     "Бизнес-логика",
  storage:  "Хранилище",
  external: "Внешняя интеграция",
  chain:    "Блокчейн",
  notify:   "Канал уведомлений",
};

const KIND_ACCENT: Record<NodeKind, string> = {
  client:   "border-foreground/20  text-foreground",
  auth:     "border-primary/30      text-primary",
  policy:   "border-amber-300       text-amber-700 dark:text-amber-300 dark:border-amber-500/40",
  core:     "border-success/30      text-success",
  storage:  "border-foreground/20   text-foreground",
  external: "border-primary/30      text-primary",
  chain:    "border-foreground/20   text-foreground",
  notify:   "border-foreground/20   text-muted-foreground",
};

interface Props {
  node: NodeData | null;
  onClose: () => void;
}

export function NodeDetailPanel({ node, onClose }: Props) {
  return (
    <AnimatePresence>
      {node && (
        <>
          {/* Backdrop intentionally minimal — graph stays visible behind */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="absolute inset-0 z-30 bg-foreground/10 backdrop-blur-[1px]"
            aria-hidden
          />

          <motion.aside
            key="panel"
            initial={{ x: "100%", opacity: 0.6 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className={cn(
              "absolute top-0 right-0 bottom-0 z-40",
              "w-full sm:w-[440px]",
              "bg-card border-l border-border shadow-xl",
              "flex flex-col",
            )}
            role="dialog"
            aria-modal="false"
            aria-label="Описание узла"
          >
            {/* Header */}
            <header className="shrink-0 border-b border-border px-5 py-4 flex items-start gap-4">
              <div
                className={cn(
                  "shrink-0 w-12 h-12 rounded-md flex items-center justify-center bg-muted",
                )}
              >
                <Icon icon={node.icon} className="text-[22px] text-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <span
                  className={cn(
                    "inline-flex items-center px-2 py-0.5 border rounded-sm",
                    "font-mono text-[9px] tracking-[0.14em] uppercase",
                    KIND_ACCENT[node.kind],
                  )}
                >
                  {KIND_LABEL[node.kind]}
                </span>
                <h2 className="mt-1.5 text-[16px] font-medium text-foreground leading-tight">
                  {node.label}
                </h2>
                {node.caption && (
                  <p className="mt-0.5 text-[12px] text-muted-foreground leading-snug">
                    {node.caption}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Закрыть"
                className="shrink-0 inline-flex items-center justify-center w-8 h-8 text-muted-foreground hover:text-foreground"
              >
                <Icon icon="solar:close-circle-linear" className="text-[18px]" />
              </button>
            </header>

            {/* Body */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
              {/* Role */}
              <section>
                <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint mb-1.5">
                  Что делает
                </div>
                <p className="text-[13px] text-foreground leading-relaxed">
                  {node.detail.role}
                </p>
              </section>

              {/* Code references */}
              {node.detail.code && node.detail.code.length > 0 && (
                <section>
                  <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint mb-1.5">
                    Код
                  </div>
                  <ul className="space-y-1">
                    {node.detail.code.map((path) => (
                      <li
                        key={path}
                        className="flex items-center gap-2 px-2.5 py-1.5 border border-border bg-muted/40 rounded-sm"
                      >
                        <Icon icon="solar:file-text-linear" className="text-[12px] text-muted-foreground" />
                        <code className="font-mono text-[11px] text-foreground break-all">
                          {path}
                        </code>
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {/* Sample payload */}
              {node.detail.sample && (
                <section>
                  <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-faint mb-1.5">
                    Пример вызова
                  </div>
                  <pre className="px-3 py-2.5 border border-border bg-muted/40 rounded-sm font-mono text-[11px] text-foreground whitespace-pre-wrap break-all leading-relaxed">
                    {node.detail.sample}
                  </pre>
                </section>
              )}
            </div>

            {/* Footer hint */}
            <footer className="shrink-0 border-t border-border px-5 py-3 bg-muted/40">
              <p className="text-[11px] text-muted-foreground leading-snug">
                Все узлы и связи на схеме соответствуют рабочему коду —
                это не статичная иллюстрация.
              </p>
            </footer>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
