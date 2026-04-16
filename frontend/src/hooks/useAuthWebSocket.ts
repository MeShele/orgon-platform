"use client";

import { useEffect, useRef, useState, useCallback } from "react";

type WSNotification = {
  type: string;
  event?: string;
  title?: string;
  message?: string;
  data?: Record<string, unknown>;
};

function getAuthWebSocketURL(token: string): string {
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host =
    window.location.hostname === "localhost" && process.env.NEXT_PUBLIC_API_URL
      ? new URL(process.env.NEXT_PUBLIC_API_URL).host
      : window.location.host;
  return `${protocol}//${host}/ws/auth/${token}`;
}

export function useAuthWebSocket(token: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [notifications, setNotifications] = useState<WSNotification[]>([]);
  const [lastNotification, setLastNotification] = useState<WSNotification | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>(undefined);
  const pingInterval = useRef<NodeJS.Timeout>(undefined);

  const connect = useCallback(() => {
    if (!token) return;
    const url = getAuthWebSocketURL(token);
    if (!url) return;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setConnected(true);
        // Ping every 30s to keep alive
        pingInterval.current = setInterval(() => ws.send("ping"), 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data: WSNotification = JSON.parse(event.data);
          if (data.type === "pong") return;
          if (data.type === "notification") {
            setNotifications((prev) => [data, ...prev].slice(0, 50));
            setLastNotification(data);
          }
        } catch {}
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(pingInterval.current);
        reconnectTimeout.current = setTimeout(connect, 5000);
      };

      ws.onerror = () => ws.close();
      wsRef.current = ws;
    } catch {
      reconnectTimeout.current = setTimeout(connect, 5000);
    }
  }, [token]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeout.current);
      clearInterval(pingInterval.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const clearNotifications = useCallback(() => setNotifications([]), []);

  return { connected, notifications, lastNotification, clearNotifications };
}
