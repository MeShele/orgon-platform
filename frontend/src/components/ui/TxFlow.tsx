/**
 * TxFlow — schematic flow:  WALLET ──● {M/N} ╌╌╌▶ CHAIN
 * Used in Hero / Features sections to explain multi-signature flow at a glance.
 * Pure SVG, token-driven via currentColor + CSS variable refs.
 */

import * as React from 'react';

export interface TxFlowProps {
  width?: number;
  height?: number;
  threshold?: string;
  walletLabel?: string;
  chainLabel?: string;
  className?: string;
  /** Override CSS-var-based colors */
  accent?: string;
  muted?: string;
  fg?: string;
}

export function TxFlow({
  width = 360,
  height = 96,
  threshold = '2/3',
  walletLabel = 'WALLET',
  chainLabel = 'CHAIN',
  className,
  accent = 'var(--primary)',
  muted = 'var(--border-strong)',
  fg = 'var(--foreground)',
}: TxFlowProps) {
  const cy = height / 2;
  const left = { x: 8, w: 76, h: 36 };
  const right = { x: width - 84, w: 76, h: 36 };
  const hubX = width / 2;
  const hubR = 16;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label="Multi-signature transaction flow"
    >
      <defs>
        <pattern id="orgon-tx-dotgrid" width={8} height={8} patternUnits="userSpaceOnUse">
          <circle cx={1} cy={1} r={0.6} fill={muted} opacity={0.5} />
        </pattern>
      </defs>

      {/* Background dot grid */}
      <rect x={0} y={0} width={width} height={height} fill="url(#orgon-tx-dotgrid)" opacity={0.4} />

      {/* Wallet block (outline) */}
      <rect x={left.x} y={cy - left.h / 2} width={left.w} height={left.h} fill="none" stroke={fg} strokeWidth={0.8} />
      <text
        x={left.x + left.w / 2}
        y={cy + 3.5}
        textAnchor="middle"
        fontSize={9}
        fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
        fill={fg}
      >
        {walletLabel}
      </text>

      {/* Solid arrow into hub */}
      <line x1={left.x + left.w} y1={cy} x2={hubX - hubR} y2={cy} stroke={accent} strokeWidth={1.2} />
      <circle cx={hubX - hubR - 2} cy={cy} r={2} fill={accent} />

      {/* Hub circle with threshold label */}
      <circle cx={hubX} cy={cy} r={hubR} fill="none" stroke={accent} strokeWidth={1} />
      <text
        x={hubX}
        y={cy + 3.5}
        textAnchor="middle"
        fontSize={9}
        fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
        fill={accent}
        fontWeight={600}
      >
        {threshold}
      </text>

      {/* Dashed arrow hub → chain */}
      <line
        x1={hubX + hubR}
        y1={cy}
        x2={right.x}
        y2={cy}
        stroke={accent}
        strokeWidth={1.2}
        strokeDasharray="3 2"
      />

      {/* Chain block (filled) */}
      <rect x={right.x} y={cy - right.h / 2} width={right.w} height={right.h} fill={fg} />
      <text
        x={right.x + right.w / 2}
        y={cy + 3.5}
        textAnchor="middle"
        fontSize={9}
        fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
        fill="var(--background)"
      >
        {chainLabel}
      </text>
    </svg>
  );
}

export default TxFlow;
