"use client";

import { useEffect, useState } from "react";
import { Icon } from "@/lib/icons";

/**
 * Renders "обновлено N сек назад" with a quiet pulsing dot, ticking
 * once per second so the user can tell at a glance whether data is
 * fresh. `at` is the epoch ms of the last successful fetch.
 */
export function LastUpdated({
  at,
  refreshing = false,
  onRefresh,
}: {
  at: number | null;
  refreshing?: boolean;
  onRefresh?: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const label = (() => {
    if (!at) return "ещё нет данных";
    const ago = Math.max(0, Math.floor((now - at) / 1000));
    if (ago < 5) return "только что";
    if (ago < 60) return `${ago} сек назад`;
    return `${Math.floor(ago / 60)} мин назад`;
  })();

  return (
    <span className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
      <span className="relative flex h-1.5 w-1.5">
        <span
          className={
            refreshing
              ? "absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"
              : "absolute inline-flex h-full w-full rounded-full bg-success/40"
          }
        />
        <span
          className={
            refreshing
              ? "relative inline-flex h-1.5 w-1.5 rounded-full bg-primary"
              : "relative inline-flex h-1.5 w-1.5 rounded-full bg-success"
          }
        />
      </span>
      <span>Обновлено: {label}</span>
      {onRefresh ? (
        <button
          type="button"
          onClick={onRefresh}
          className="ml-1 inline-flex items-center text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Обновить"
          title="Обновить сейчас"
        >
          <Icon
            icon="solar:refresh-linear"
            className={refreshing ? "text-sm animate-spin" : "text-sm"}
          />
        </button>
      ) : null}
    </span>
  );
}
