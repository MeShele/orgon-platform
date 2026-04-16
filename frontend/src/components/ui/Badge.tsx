/**
 * Badge Component - Design System
 */

import React from 'react';
import { cn, components } from '@/lib/theme';

export type BadgeVariant = 'primary' | 'success' | 'warning' | 'danger' | 'gray';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: React.ReactNode;
}

export function Badge({
  variant = 'gray',
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        components.badge.base,
        components.badge[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export default Badge;
