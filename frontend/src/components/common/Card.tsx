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
        "rounded-xl border border-border bg-white shadow-sm dark:border-border dark:bg-card/40 dark:shadow-none",
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
    <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3 dark:border-border">
      <div>
        <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
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
          <p className="text-[10px] text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}
