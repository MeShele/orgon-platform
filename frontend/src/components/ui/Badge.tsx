import * as React from 'react';
import { cn } from '@/lib/utils';

export type BadgeVariant =
  | 'primary' | 'success' | 'warning' | 'danger' | 'gray' | 'navy' | 'outline'
  // legacy colour aliases (use semantic variants in new code)
  | 'green'   // → success
  | 'red'     // → danger
  | 'yellow'  // → warning
  | 'blue';   // → primary

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  /** Mono uppercase letter-spaced — Crimson Ledger default */
  mono?: boolean;
  children: React.ReactNode;
}

const VARIANT: Record<BadgeVariant, string> = {
  primary: 'bg-primary text-primary-foreground border-primary',
  success: 'bg-success text-success-foreground border-success',
  warning: 'bg-warning text-warning-foreground border-warning',
  danger: 'bg-destructive text-destructive-foreground border-destructive',
  gray: 'bg-muted text-muted-foreground border-border',
  navy: 'bg-navy text-navy-foreground border-navy',
  outline: 'bg-transparent text-foreground border-strong',
  // legacy aliases
  green: 'bg-success text-success-foreground border-success',
  red: 'bg-destructive text-destructive-foreground border-destructive',
  yellow: 'bg-warning text-warning-foreground border-warning',
  blue: 'bg-primary text-primary-foreground border-primary',
};

export function Badge({ variant = 'gray', mono = true, className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 border',
        mono ? 'font-mono text-[10px] tracking-wider uppercase' : 'text-[11px] font-medium',
        VARIANT[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export default Badge;
