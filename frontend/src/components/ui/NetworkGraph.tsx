/**
 * NetworkGraph — multi-signature signers laid out around a central hub.
 *
 *   ● = signed (filled with primary color)
 *   ○ = pending (ring only)
 *
 * Signer addresses can be either email or blockchain address — we just
 * use the first 2 letters of the cleaned-up local part as initials.
 * If an explicit `initials` is provided, it wins.
 */

'use client';

import * as React from 'react';

export interface SignerNode {
  /** Email, blockchain address, or any unique identifier */
  address: string;
  /** Whether this signer has signed yet */
  state: 'signed' | 'pending' | 'rejected';
  /** Display name (full) — optional, used for labels next to graph */
  name?: string;
  /** Override auto-derived initials */
  initials?: string;
  /** Timestamp when signed (ISO or pre-formatted) */
  time?: string | null;
}

export interface NetworkGraphProps {
  signers: SignerNode[];
  size?: number;
  className?: string;
  /** Ring color for pending nodes — defaults to current border-strong */
  ringColor?: string;
  /** Color for signed nodes / connecting lines — defaults to primary */
  accentColor?: string;
  /** Label color */
  labelColor?: string;
}

/** Pull the first two letters of the "local" part of an email/address */
export function deriveInitials(addressOrName: string): string {
  if (!addressOrName) return '··';
  const cleaned = addressOrName.split('@')[0].replace(/^0x/i, '').replace(/[^a-zA-Zа-яА-ЯёЁ]/g, '');
  if (cleaned.length === 0) return addressOrName.slice(0, 2).toUpperCase();
  return cleaned.slice(0, 2).toUpperCase();
}

export function NetworkGraph({
  signers,
  size = 220,
  className,
  ringColor = 'var(--border-strong)',
  accentColor = 'var(--primary)',
  labelColor = 'var(--foreground)',
}: NetworkGraphProps) {
  const n = signers.length;
  if (n === 0) return null;

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.36;

  const nodes = signers.map((s, i) => {
    const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
    return {
      ...s,
      initials: s.initials ?? deriveInitials(s.name ?? s.address),
      x: cx + Math.cos(angle) * r,
      y: cy + Math.sin(angle) * r,
    };
  });

  const nodeR = size * 0.085;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      role="img"
      aria-label="Multi-signature signer network"
    >
      {/* edges hub → node */}
      {nodes.map((node, i) => (
        <line
          key={`edge-${i}`}
          x1={cx}
          y1={cy}
          x2={node.x}
          y2={node.y}
          stroke={node.state === 'signed' ? accentColor : ringColor}
          strokeWidth={node.state === 'signed' ? 1.2 : 0.6}
          strokeDasharray={node.state === 'signed' ? '0' : '2 3'}
        />
      ))}

      {/* central hub */}
      <circle cx={cx} cy={cy} r={size * 0.06} fill={labelColor} />
      <circle cx={cx} cy={cy} r={size * 0.10} fill="none" stroke={ringColor} strokeWidth={0.5} />

      {/* signer nodes */}
      {nodes.map((node, i) => (
        <g key={`node-${i}`}>
          <circle
            cx={node.x}
            cy={node.y}
            r={nodeR}
            fill={node.state === 'signed' ? accentColor : 'transparent'}
            stroke={node.state === 'signed' ? accentColor : ringColor}
            strokeWidth={1.2}
          />
          <text
            x={node.x}
            y={node.y + size * 0.026}
            textAnchor="middle"
            fontSize={size * 0.06}
            fontFamily="ui-monospace, 'IBM Plex Mono', monospace"
            fontWeight={600}
            fill={node.state === 'signed' ? '#ffffff' : labelColor}
          >
            {node.initials}
          </text>
        </g>
      ))}
    </svg>
  );
}

export default NetworkGraph;
