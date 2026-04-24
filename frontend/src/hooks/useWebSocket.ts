"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type WSEvent = {
  type: string;
  data: Record<string, unknown>;
};

function getWebSocketURL(): string {
  if (typeof window === "undefined") return "";

  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl) {
    // Convert https://orgon-api.asystem.kg to wss://orgon-api.asystem.kg/ws/updates
    return apiUrl.replace(/^https:/, "wss:").replace(/^http:/, "ws:") + "/ws/updates";
  }

  // Fallback: same host (dev mode)
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/updates`;
}

export function useWebSocket(url?: string) {
  const wsURL = url || getWebSocketURL();
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>(undefined);

  const connect = useCallback(() => {
    if (!wsURL) return;
    
    try {
      const ws = new WebSocket(wsURL);

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastEvent(data);
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        // Reconnect after 5s
        reconnectTimeout.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      reconnectTimeout.current = setTimeout(connect, 5000);
    }
  }, [wsURL]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendPing = useCallback(() => {
    wsRef.current?.send("ping");
  }, []);

  return { connected, lastEvent, sendPing };
}
