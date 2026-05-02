"use client";

import { createContext, useContext, useEffect, useRef, useState, useCallback, ReactNode } from "react";

type WSEvent = {
  type: string;
  data: Record<string, unknown>;
};

type WebSocketContextType = {
  connected: boolean;
  lastEvent: WSEvent | null;
  sendPing: () => void;
};

const WebSocketContext = createContext<WebSocketContextType>({
  connected: false,
  lastEvent: null,
  sendPing: () => {},
});

function getWebSocketURL(): string {
  if (typeof window === "undefined") return "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.hostname === 'localhost' && process.env.NEXT_PUBLIC_API_URL
    ? new URL(process.env.NEXT_PUBLIC_API_URL).host
    : window.location.host;
  // Backend exposes /ws/auth/{token} which validates the JWT from the URL.
  // Without a token the connection 404s and the header would show "Офлайн".
  const token = localStorage.getItem("orgon_access_token") ?? "";
  if (!token) return ""; // skip connect until login completes
  return `${protocol}//${host}/ws/auth/${encodeURIComponent(token)}`;
}

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WSEvent | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout>(undefined);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    const wsURL = getWebSocketURL();
    if (!wsURL || !mountedRef.current) return;

    // Don't create duplicate connections
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      return;
    }

    try {
      const ws = new WebSocket(wsURL);

      ws.onopen = () => {
        if (mountedRef.current) setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (mountedRef.current) setLastEvent(data);
        } catch {}
      };

      ws.onclose = () => {
        if (mountedRef.current) {
          setConnected(false);
          reconnectTimeout.current = setTimeout(connect, 5000);
        }
      };

      ws.onerror = () => {
        ws.close();
      };

      wsRef.current = ws;
    } catch {
      if (mountedRef.current) {
        reconnectTimeout.current = setTimeout(connect, 5000);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect]);

  const sendPing = useCallback(() => {
    wsRef.current?.send("ping");
  }, []);

  return (
    <WebSocketContext.Provider value={{ connected, lastEvent, sendPing }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  return useContext(WebSocketContext);
}
