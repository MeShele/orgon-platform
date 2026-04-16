"use client";

import { useEffect, useCallback, useState } from "react";
import { useWebSocket } from "@/contexts/WebSocketContext";

type EventType =
  | "balance.updated"
  | "transaction.created"
  | "transaction.sent"
  | "transaction.confirmed"
  | "transaction.failed"
  | "signature.pending"
  | "signature.approved"
  | "signature.rejected"
  | "wallet.created"
  | "wallet.updated"
  | "sync.completed"
  | "sync.started"
  | "sync.failed";

type EventHandler = (data: Record<string, unknown>) => void;

export function useRealtimeEvents() {
  const { connected, lastEvent } = useWebSocket();
  const [handlers, setHandlers] = useState<Map<EventType, Set<EventHandler>>>(
    new Map()
  );

  // Subscribe to an event type
  const on = useCallback((eventType: EventType, handler: EventHandler) => {
    setHandlers((prev) => {
      const newMap = new Map(prev);
      if (!newMap.has(eventType)) {
        newMap.set(eventType, new Set());
      }
      newMap.get(eventType)!.add(handler);
      return newMap;
    });

    // Return unsubscribe function
    return () => {
      setHandlers((prev) => {
        const newMap = new Map(prev);
        const eventHandlers = newMap.get(eventType);
        if (eventHandlers) {
          eventHandlers.delete(handler);
          if (eventHandlers.size === 0) {
            newMap.delete(eventType);
          }
        }
        return newMap;
      });
    };
  }, []);

  // Process incoming events
  useEffect(() => {
    if (!lastEvent) return;

    const { type, data } = lastEvent;
    const eventHandlers = handlers.get(type as EventType);

    if (eventHandlers) {
      eventHandlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Event handler error for ${type}:`, error);
        }
      });
    }
  }, [lastEvent, handlers]);

  return { connected, on };
}

/**
 * Hook for listening to specific event types.
 * 
 * Example:
 * ```tsx
 * useEvent("transaction.created", (data) => {
 *   mutate("/api/transactions");
 * });
 * ```
 */
export function useEvent(eventType: EventType, handler: EventHandler) {
  const { on } = useRealtimeEvents();

  useEffect(() => {
    return on(eventType, handler);
  }, [on, eventType, handler]);
}
