/**
 * Sparkline — minimalistic 1px line chart with optional fill underneath.
 * Token-driven: defaults to var(--primary) for stroke.
 */

import * as React from 'react';

export interface SparklineProps {
  points: number[];
  width?: number;
  height?: number;
  strokeWidth?: number;
  /** CSS color or token. Default: `currentColor` so the parent can color it */
  stroke?: string;
  /** Fill below the line. Default: matching stroke at 10% alpha */
  fill?: string | null;
  className?: string;
  ariaLabel?: string;
}

export function Sparkline({
  points,
  width = 120,
  height = 36,
  strokeWidth = 1.2,
  stroke = 'currentColor',
  fill,
  className,
  ariaLabel,
}: SparklineProps) {
  if (!points || points.length < 2) {
    return null;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = width / (points.length - 1);

  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(2)} ${(height - ((p - min) / range) * height).toFixed(2)}`)
    .join(' ');

  const area = `${path} L ${width} ${height} L 0 ${height} Z`;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label={ariaLabel ?? 'Trend sparkline'}
    >
      {fill !== null && (
        <path d={area} fill={fill ?? stroke} fillOpacity={fill ? 1 : 0.1} />
      )}
      <path
        d={path}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default Sparkline;
