"use client";

import { ReactNode, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Icon } from "@/lib/icons";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: "top" | "bottom" | "left" | "right";
  maxWidth?: string;
  delay?: number;
  showIcon?: boolean;
}

export function Tooltip({
  content,
  children,
  position = "top",
  maxWidth = "280px",
  delay = 200,
  showIcon = false,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    const id = setTimeout(() => setIsVisible(true), delay);
    setTimeoutId(id);
  };

  const handleMouseLeave = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      setTimeoutId(null);
    }
    setIsVisible(false);
  };

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  const arrowClasses = {
    top: "top-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-slate-900",
    bottom: "bottom-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-slate-900",
    left: "left-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-slate-900",
    right: "right-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-slate-900",
  };

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {showIcon && (
        <Icon
          icon="solar:question-circle-linear"
          className="ml-1 text-muted-foreground hover:text-muted-foreground dark:text-muted-foreground dark:hover:text-faint cursor-help"
        />
      )}
      
      <AnimatePresence>
        {isVisible && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={`absolute z-50 ${positionClasses[position]}`}
            style={{ maxWidth }}
          >
            <div className="relative bg-foreground text-background text-sm rounded-lg shadow-xl px-3 py-2 border border-border">
              {content}
              <div
                className={`absolute w-0 h-0 border-4 ${arrowClasses[position]}`}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface HelpTextProps {
  title: string;
  description: string;
  example?: string;
  tips?: readonly string[];
}

export function HelpText({ title, description, example, tips }: HelpTextProps) {
  return (
    <div className="space-y-2">
      <div className="font-semibold text-white">{title}</div>
      <div className="text-faint text-xs leading-relaxed">{description}</div>
      
      {example && (
        <div className="mt-2 pt-2 border-t border-border">
          <div className="text-xs text-muted-foreground mb-1">Пример:</div>
          <div className="text-xs text-cyan-400 font-mono bg-slate-950/50 px-2 py-1 rounded">
            {example}
          </div>
        </div>
      )}
      
      {tips && tips.length > 0 && (
        <div className="mt-2 pt-2 border-t border-border">
          <div className="text-xs text-muted-foreground mb-1">💡 Подсказки:</div>
          <ul className="text-xs text-faint space-y-1">
            {tips.map((tip, idx) => (
              <li key={idx} className="flex items-start gap-1">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
