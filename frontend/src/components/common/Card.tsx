import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import { HelpTooltip } from "./HelpTooltip";

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900/40 dark:shadow-none",
        className
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
  helpText,
  helpExample,
  helpTips,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  helpText?: string;
  helpExample?: string;
  helpTips?: readonly string[];
}) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-slate-800">
      <div>
        <h3 className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
          {title}
          {helpText && (
            <HelpTooltip
              text={helpText}
              example={helpExample}
              tips={helpTips}
            />
          )}
        </h3>
        {subtitle && (
          <p className="text-[10px] text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}
