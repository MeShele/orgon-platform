import * as React from 'react';
import { cn } from '@/lib/utils';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** visual surface — default is muted card, navy is for popular/feature blocks, plain has no border */
  surface?: 'default' | 'navy' | 'plain';
  hover?: boolean;
  padding?: boolean;
  children?: React.ReactNode;
}

export function Card({ surface = 'default', hover, padding = true, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        surface === 'navy' && 'bg-navy text-navy-foreground border border-transparent',
        surface === 'default' && 'bg-card text-card-foreground border border-border',
        surface === 'plain' && 'bg-transparent text-foreground',
        padding && 'p-6',
        hover && 'transition-colors hover:border-strong',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  eyebrow?: React.ReactNode;
}

export function CardHeader({ title, subtitle, action, eyebrow, className, children, ...props }: CardHeaderProps) {
  return (
    <div className={cn('flex items-start justify-between gap-4 px-5 py-4 border-b border-border', className)} {...props}>
      <div>
        {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
        {title && <h3 className="text-[15px] font-medium tracking-tight text-foreground">{title}</h3>}
        {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
        {children}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('px-5 py-4', className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center justify-end gap-2 px-5 py-3 border-t border-border bg-muted', className)} {...props}>
      {children}
    </div>
  );
}

export default Card;
