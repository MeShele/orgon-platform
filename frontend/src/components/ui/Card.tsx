/**
 * Card Component - Design System
 */

import React from 'react';
import { cn, components } from '@/lib/theme';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
  padding?: boolean;
  children: React.ReactNode;
}

export function Card({
  hover = false,
  padding = true,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        components.card.base,
        components.card.default,
        hover && components.card.hover,
        padding && components.card.padding,
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;
