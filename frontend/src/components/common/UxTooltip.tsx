"use client";

import { useState } from "react";
import { Icon } from "@/lib/icons";

interface UxTooltipProps {
  text: string;
  children?: React.ReactNode;
}

export function UxTooltip({ text, children }: UxTooltipProps) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      {children}
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="ml-1 text-muted-foreground hover:text-primary transition-colors"
      >
        <Icon icon="solar:question-circle-linear" className="text-base" />
      </button>
      {show && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 rounded-lg bg-card dark:bg-slate-700 p-3 text-xs text-white shadow-lg z-50">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900 dark:border-t-slate-700" />
        </div>
      )}
    </span>
  );
}
