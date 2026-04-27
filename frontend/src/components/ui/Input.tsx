import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  fullWidth?: boolean;
  /** Render label as eyebrow (mono uppercase) — default true for Crimson Ledger */
  eyebrowLabel?: boolean;
  /** Use mono font in the input itself (for emails, addresses, hashes) */
  mono?: boolean;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, fullWidth = true, eyebrowLabel = true, mono = false, className, ...props }, ref) => {
    return (
      <div className={cn(fullWidth && 'w-full')}>
        {label && (
          <label
            htmlFor={props.id}
            className={cn(
              'block mb-1.5',
              eyebrowLabel
                ? 'font-mono text-[11px] tracking-[0.12em] uppercase text-faint'
                : 'text-xs font-medium text-muted-foreground',
            )}
          >
            {label}
          </label>
        )}

        <input
          ref={ref}
          className={cn(
            'block w-full h-10 px-3 py-2',
            'bg-card text-foreground placeholder:text-faint',
            'border border-border',
            'transition-colors duration-150',
            'focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            mono && 'font-mono text-[13px]',
            error && 'border-destructive focus:border-destructive focus:ring-destructive/20',
            className,
          )}
          {...props}
        />

        {error && (
          <p className="mt-1.5 text-xs text-destructive">{error}</p>
        )}

        {helperText && !error && (
          <p className="mt-1.5 text-xs text-muted-foreground">{helperText}</p>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';

export default Input;
