/**
 * ORGON · Crimson Ledger primitives
 * Small typographic / inline atoms reused across the redesign.
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

// ─────────────────────────────────────────────────────────
// Eyebrow — mono uppercase label, optionally prefixed with "──"
// ─────────────────────────────────────────────────────────
export interface EyebrowProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Show the leading `─── ` decorative dash */
  dash?: boolean;
  /** Override default `text-faint` color (e.g. `text-primary`) */
  tone?: 'faint' | 'primary' | 'foreground' | 'muted';
}

export function Eyebrow({ dash = false, tone = 'faint', className, children, ...props }: EyebrowProps) {
  const toneClass =
    tone === 'primary' ? 'text-primary'
    : tone === 'foreground' ? 'text-foreground'
    : tone === 'muted' ? 'text-muted-foreground'
    : 'text-faint';
  return (
    <div
      className={cn(
        'font-mono text-[11px] tracking-[0.12em] uppercase',
        toneClass,
        className,
      )}
      {...props}
    >
      {dash && <span aria-hidden="true">─── </span>}
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// Mono — inline monospace span for addresses, hashes, IDs
// ─────────────────────────────────────────────────────────
export interface MonoProps extends React.HTMLAttributes<HTMLSpanElement> {
  size?: 'xs' | 'sm' | 'md';
  /** Truncate middle: 0xAB12··EF34 */
  truncate?: boolean;
  /** Number of chars at start when truncating (default 6) */
  startChars?: number;
  /** Number of chars at end when truncating (default 4) */
  endChars?: number;
  children: React.ReactNode;
}

export function Mono({ size = 'sm', truncate, startChars = 6, endChars = 4, className, children, ...props }: MonoProps) {
  let content: React.ReactNode = children;
  if (truncate && typeof children === 'string' && children.length > startChars + endChars + 2) {
    content = `${children.slice(0, startChars)}··${children.slice(-endChars)}`;
  }
  const sizeClass = size === 'xs' ? 'text-[10px]' : size === 'md' ? 'text-[13px]' : 'text-[11px]';
  return (
    <span className={cn('font-mono tracking-tight', sizeClass, className)} {...props}>
      {content}
    </span>
  );
}

// ─────────────────────────────────────────────────────────
// BigNum — tabular-nums, tight letter-spacing for large numbers
// ─────────────────────────────────────────────────────────
export interface BigNumProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'xxl';
  weight?: 'normal' | 'medium' | 'semibold';
  children: React.ReactNode;
}

export function BigNum({ size = 'md', weight = 'medium', className, children, ...props }: BigNumProps) {
  const sizeClass =
    size === 'sm' ? 'text-base'
    : size === 'md' ? 'text-2xl'
    : size === 'lg' ? 'text-[28px]'
    : size === 'xl' ? 'text-[36px]'
    : 'text-[48px]';
  const weightClass =
    weight === 'normal' ? 'font-normal'
    : weight === 'semibold' ? 'font-semibold'
    : 'font-medium';
  return (
    <div
      className={cn(
        'tabular leading-tight tracking-[-0.02em]',
        sizeClass,
        weightClass,
        className,
      )}
      style={{ fontVariantNumeric: 'tabular-nums', fontFeatureSettings: '"tnum"' }}
      {...props}
    >
      {children}
    </div>
  );
}

// ─────────────────────────────────────────────────────────
// StatusDot — 6×6 colored dot for status pills
// ─────────────────────────────────────────────────────────
export type StatusKind = 'confirmed' | 'sent' | 'pending' | 'rejected' | 'success' | 'warning' | 'danger' | 'neutral';

const STATUS_CLASSES: Record<StatusKind, string> = {
  confirmed: 'bg-success',
  success: 'bg-success',
  sent: 'bg-foreground',
  pending: 'bg-warning',
  warning: 'bg-warning',
  rejected: 'bg-destructive',
  danger: 'bg-destructive',
  neutral: 'bg-faint',
};

export interface StatusDotProps {
  kind: StatusKind;
  /** Pending shows a small square instead of circle (Crimson Ledger convention) */
  shape?: 'auto' | 'circle' | 'square';
  className?: string;
}

export function StatusDot({ kind, shape = 'auto', className }: StatusDotProps) {
  const isSquare = shape === 'square' || (shape === 'auto' && (kind === 'pending' || kind === 'warning'));
  return (
    <span
      aria-hidden="true"
      className={cn(
        'inline-block w-1.5 h-1.5 shrink-0',
        isSquare ? '' : 'rounded-full',
        STATUS_CLASSES[kind],
        className,
      )}
    />
  );
}

// ─────────────────────────────────────────────────────────
// StatusPill — StatusDot + uppercase mono label
// ─────────────────────────────────────────────────────────
export interface StatusPillProps {
  kind: StatusKind;
  label: string;
  className?: string;
}

export function StatusPill({ kind, label, className }: StatusPillProps) {
  const colorClass =
    kind === 'confirmed' || kind === 'success' ? 'text-success'
    : kind === 'pending' || kind === 'warning' ? 'text-warning'
    : kind === 'rejected' || kind === 'danger' ? 'text-destructive'
    : kind === 'sent' ? 'text-foreground'
    : 'text-faint';

  return (
    <span className={cn('inline-flex items-center gap-1.5 font-mono text-[10px] tracking-[0.06em] uppercase', colorClass, className)}>
      <StatusDot kind={kind} />
      {label}
    </span>
  );
}

// ─────────────────────────────────────────────────────────
// Divider — horizontal rule using border token
// ─────────────────────────────────────────────────────────
export function Divider({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('h-px w-full bg-border', className)} {...props} />;
}
