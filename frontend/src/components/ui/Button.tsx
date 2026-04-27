import * as React from 'react';
import { cn } from '@/lib/utils';

export type ButtonVariant =
  | 'primary'      // crimson, brand action
  | 'secondary'    // border, neutral
  | 'ghost'        // no border, hover quiet
  | 'navy'         // navy block, white text — for popular/feature CTAs
  | 'destructive'  // crimson, dangerous
  | 'danger'       // alias of destructive (legacy callers)
  | 'warning'      // amber
  | 'success';     // green
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  fullWidth?: boolean;
  children: React.ReactNode;
}

const SIZE: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-5 text-sm',
  lg: 'h-12 px-6 text-[15px]',
};

const VARIANT: Record<ButtonVariant, string> = {
  primary:
    'bg-primary text-primary-foreground border border-primary hover:opacity-90 active:opacity-80',
  secondary:
    'bg-transparent text-foreground border border-strong hover:bg-muted',
  ghost:
    'bg-transparent text-foreground border border-transparent hover:bg-muted',
  navy:
    'bg-navy text-navy-foreground border border-navy hover:opacity-90 active:opacity-80',
  destructive:
    'bg-destructive text-destructive-foreground border border-destructive hover:opacity-90',
  danger:
    'bg-destructive text-destructive-foreground border border-destructive hover:opacity-90',
  warning:
    'bg-warning text-warning-foreground border border-warning hover:opacity-90',
  success:
    'bg-success text-success-foreground border border-success hover:opacity-90',
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, fullWidth = false, className, disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center gap-2',
          'font-medium tracking-tight',
          'transition-colors duration-150',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary',
          SIZE[size],
          VARIANT[variant],
          fullWidth && 'w-full',
          loading && 'cursor-wait',
          className,
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <svg className="-ml-0.5 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
            <path d="M4 12a8 8 0 0 1 8-8" stroke="currentColor" strokeWidth="3" />
          </svg>
        )}
        {children}
      </button>
    );
  },
);

Button.displayName = 'Button';

export default Button;
