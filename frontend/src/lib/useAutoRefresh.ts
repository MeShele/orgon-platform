"use client";

import { useEffect, useRef } from "react";

/**
 * useAutoRefresh — fire `callback` every `intervalMs` while the
 * component is mounted and the tab is visible.
 *
 * Why visibility-aware: when a user switches tabs we don't want to
 * keep hammering our backend (and indirectly Safina via scheduler).
 * We pause on hidden, fire once immediately on resume so the data
 * the user sees right after switching back is fresh.
 *
 * Callback is stored in a ref so consumers can pass an inline
 * closure without re-arming the interval on every render.
 */
export function useAutoRefresh(
  callback: () => void | Promise<void>,
  intervalMs: number,
  enabled: boolean = true,
) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return;

    let id: ReturnType<typeof setInterval> | null = null;

    const arm = () => {
      if (id !== null) return;
      id = setInterval(() => {
        void cbRef.current();
      }, intervalMs);
    };
    const disarm = () => {
      if (id !== null) {
        clearInterval(id);
        id = null;
      }
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        // Fire immediately on resume — user expects fresh data after
        // returning from another tab.
        void cbRef.current();
        arm();
      } else {
        disarm();
      }
    };

    if (typeof document !== "undefined" && document.visibilityState === "visible") {
      arm();
    }
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibility);
    }
    return () => {
      disarm();
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibility);
      }
    };
  }, [intervalMs, enabled]);
}
