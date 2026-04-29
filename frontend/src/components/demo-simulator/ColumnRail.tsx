"use client";

// Static layer-legend strip rendered above the graph. Lives outside
// React Flow so it doesn't move with zoom/pan and never collides with
// the page header or the right-side panel. Just labels the four
// architectural layers that the columns below represent.

import { COLUMN_LABELS } from "./graph-config";

export function ColumnRail() {
  return (
    <div className="shrink-0 border-b border-border bg-muted/30">
      <div className="grid grid-cols-4 divide-x divide-border">
        {COLUMN_LABELS.map((c, i) => (
          <div key={c.label} className="px-5 py-2.5">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[9px] tracking-[0.18em] text-faint">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-foreground">
                {c.label}
              </span>
            </div>
            <div className="mt-0.5 text-[11px] text-muted-foreground leading-snug truncate">
              {c.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
