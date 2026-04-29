"use client";

// Larger, more readable graph node. ~300×96px with bigger icon, label,
// caption AND a one-line role preview at the bottom. Crimson Ledger
// palette via Tailwind semantic tokens. The "active" state pulses,
// "halt" state shows a destructive highlight.

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";
import type { NodeData, NodeKind } from "../graph-config";

// kind → palette tokens
const KIND_STYLE: Record<
  NodeKind,
  {
    border:  string;   // idle border
    iconBg:  string;
    iconText:string;
    /** subtle column tint applied to the whole card body */
    bodyBg:  string;
  }
> = {
  client:   { border: "border-foreground/15", iconBg: "bg-foreground/5",     iconText: "text-foreground",  bodyBg: "bg-card" },
  auth:     { border: "border-primary/30",    iconBg: "bg-primary/10",       iconText: "text-primary",     bodyBg: "bg-card" },
  policy:   { border: "border-amber-300/60",  iconBg: "bg-amber-50 dark:bg-amber-500/10", iconText: "text-amber-600 dark:text-amber-300", bodyBg: "bg-card" },
  core:     { border: "border-success/30",    iconBg: "bg-success/10",       iconText: "text-success",     bodyBg: "bg-card" },
  storage:  { border: "border-foreground/15", iconBg: "bg-muted",            iconText: "text-foreground",  bodyBg: "bg-card" },
  external: { border: "border-primary/30",    iconBg: "bg-primary/10",       iconText: "text-primary",     bodyBg: "bg-card" },
  chain:    { border: "border-foreground/15", iconBg: "bg-foreground/5",     iconText: "text-foreground",  bodyBg: "bg-card" },
  notify:   { border: "border-foreground/15", iconBg: "bg-foreground/5",     iconText: "text-muted-foreground", bodyBg: "bg-card" },
};

export function OrgonNode({ data, selected }: NodeProps) {
  const d = data as NodeData;
  const palette = KIND_STYLE[d.kind];
  const isActive = (data as NodeData & { active?: boolean }).active === true;
  const isHalt   = (data as NodeData & { halt?: boolean }).halt === true;

  return (
    <div
      className={cn(
        "group relative w-[300px] rounded-lg border-2 transition-all duration-200",
        "shadow-sm hover:shadow-md cursor-pointer",
        palette.border,
        palette.bodyBg,
        selected ? "ring-2 ring-primary/40" : "",
        isActive && !isHalt && "border-primary shadow-[0_0_0_4px_rgba(156,24,37,0.10)]",
        isHalt && "border-destructive shadow-[0_0_0_4px_rgba(220,38,38,0.18)]",
      )}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !border-0 !bg-foreground/30"
      />

      {/* Top row — icon + label */}
      <div className="flex items-start gap-3 p-3.5 pb-2.5">
        <div
          className={cn(
            "shrink-0 w-11 h-11 rounded-lg flex items-center justify-center",
            "transition-transform duration-200",
            palette.iconBg,
            isActive && "scale-110",
          )}
        >
          <Icon icon={d.icon} className={cn("text-[22px]", palette.iconText)} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="text-[14px] font-semibold leading-tight text-foreground truncate">
            {d.label}
          </div>
          {d.caption && (
            <div className="mt-0.5 text-[11px] tracking-tight text-muted-foreground truncate">
              {d.caption}
            </div>
          )}
        </div>

        {/* Click affordance */}
        <Icon
          icon="solar:square-top-down-linear"
          className="shrink-0 text-[14px] text-faint opacity-0 group-hover:opacity-100 transition-opacity"
        />
      </div>

      {/* Bottom row — role preview, single line, faded */}
      <div className="px-3.5 pb-3 -mt-0.5">
        <p className="text-[11px] text-muted-foreground leading-snug line-clamp-2">
          {d.detail.role}
        </p>
      </div>

      {/* Pulse ring overlay when active */}
      {isActive && !isHalt && (
        <span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-lg ring-2 ring-primary/40 animate-pulse"
        />
      )}

      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !border-0 !bg-foreground/30"
      />
    </div>
  );
}
