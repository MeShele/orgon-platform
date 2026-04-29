"use client";

// Single custom React Flow node that branches on data.kind for visual
// theme. Crimson Ledger palette via Tailwind semantic tokens.

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { NodeData, NodeKind } from "../graph-config";

// kind → Tailwind classes for the body. These are intentionally muted
// when idle; the GraphCanvas applies an `is-active` class to "wake up"
// the node when a scenario step lands on it.
const KIND_STYLE: Record<NodeKind, { ring: string; iconBg: string; iconText: string }> = {
  client:   { ring: "border-foreground/20",       iconBg: "bg-foreground/5",       iconText: "text-foreground" },
  auth:     { ring: "border-primary/30",          iconBg: "bg-primary/10",         iconText: "text-primary" },
  policy:   { ring: "border-warning/30",          iconBg: "bg-warning/10",         iconText: "text-warning" },
  core:     { ring: "border-success/30",          iconBg: "bg-success/10",         iconText: "text-success" },
  storage:  { ring: "border-foreground/20",       iconBg: "bg-muted",              iconText: "text-foreground" },
  external: { ring: "border-primary/30",          iconBg: "bg-primary/10",         iconText: "text-primary" },
  chain:    { ring: "border-foreground/20",       iconBg: "bg-foreground/5",       iconText: "text-foreground" },
  notify:   { ring: "border-foreground/20",       iconBg: "bg-foreground/5",       iconText: "text-muted-foreground" },
};

// Active highlight is applied via inline className modifier; we use a
// special data-attribute that GraphCanvas toggles via setNodes.
export function OrgonNode({ data, selected }: NodeProps) {
  const d = data as NodeData;
  const palette = KIND_STYLE[d.kind];
  const isActive = (data as NodeData & { active?: boolean }).active === true;
  const isHalt = (data as NodeData & { halt?: boolean }).halt === true;

  return (
    <div
      className={cn(
        "group relative w-[220px] rounded-md bg-card border-2 transition-all duration-200",
        palette.ring,
        selected ? "ring-2 ring-primary/40" : "",
        isActive && !isHalt && "border-primary shadow-[0_0_0_4px_rgba(156,24,37,0.10)]",
        isHalt && "border-destructive shadow-[0_0_0_4px_rgba(220,38,38,0.18)]",
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-1.5 !h-1.5 !border-0 !bg-foreground/30"
      />

      <div className="flex items-start gap-2.5 p-3">
        <div
          className={cn(
            "shrink-0 w-9 h-9 rounded-md flex items-center justify-center",
            palette.iconBg,
            isActive && "scale-110",
            "transition-transform duration-200",
          )}
        >
          <Icon icon={d.icon} className={cn("text-[18px]", palette.iconText)} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium leading-tight text-foreground truncate">
            {d.label}
          </div>
          {d.caption && (
            <div className="mt-0.5 text-[10px] tracking-tight text-muted-foreground truncate">
              {d.caption}
            </div>
          )}
        </div>
      </div>

      {/* Subtle pulse ring when active — pure CSS, no per-render JS */}
      {isActive && !isHalt && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-md ring-2 ring-primary/40 animate-pulse"
        />
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-1.5 !h-1.5 !border-0 !bg-foreground/30"
      />
    </div>
  );
}
