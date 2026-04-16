"use client";

import { useEffect, useRef } from "react";
import { useWebSocket } from "@/contexts/WebSocketContext";
import toast from "react-hot-toast";

/**
 * Hook that automatically shows toast notifications for real-time events.
 */
export function useToastEvents() {
  const { lastEvent, connected } = useWebSocket();

  useEffect(() => {
    if (!lastEvent) return;

    const { type, data } = lastEvent;

    switch (type) {
      // Transaction events
      case "transaction.created":
        const token = typeof data.token === "string" ? data.token.split(":::")[0] : "";
        toast.success(`Transaction sent: ${data.value || ""} ${token}`, {
          icon: "🚀",
        });
        break;

      case "transaction.confirmed":
        toast.success(`Transaction confirmed!`, {
          icon: "✅",
        });
        break;

      case "transaction.failed":
        toast.error(`Transaction failed: ${data.error || "Unknown error"}`, {
          icon: "❌",
        });
        break;

      // Signature events
      case "signature.pending":
        toast(`New signature request: ${data.value || "N/A"}`, {
          icon: "✍️",
          duration: 6000,
        });
        break;

      case "signature.approved":
        toast.success(`Signature approved`, {
          icon: "✅",
        });
        break;

      case "signature.rejected":
        toast.error(`Signature rejected`, {
          icon: "⛔",
        });
        break;

      // Balance events
      case "balance.updated":
        // Silent update (dashboard will refresh)
        break;

      case "balance.low":
        toast.error(`Low balance: ${data.token} (${data.current_value})`, {
          icon: "⚠️",
          duration: 8000,
        });
        break;

      // Wallet events
      case "wallet.created":
        toast.success(`Wallet created: ${data.name}`, {
          icon: "🎉",
        });
        break;

      case "wallet.updated":
        toast(`Wallet updated: ${data.name}`, {
          icon: "♻️",
        });
        break;

      // Sync events
      case "sync.completed":
        const items = data.items_synced || 0;
        const durationMs = typeof data.duration_ms === "number" ? data.duration_ms : 0;
        toast.success(
          `Synced ${items} ${data.type || "items"} (${(durationMs / 1000).toFixed(1)}s)`,
          {
            icon: "🔄",
            duration: 3000,
          }
        );
        break;

      case "sync.failed":
        toast.error(`Sync failed: ${data.type || "unknown"}`, {
          icon: "⚠️",
        });
        break;

      // Network events
      case "network.fee_spike":
        toast.error(`Network fee spike: ${data.network || "unknown"}`, {
          icon: "📈",
          duration: 8000,
        });
        break;

      case "network.congestion":
        toast(`Network congestion: ${data.network || "unknown"}`, {
          icon: "🐌",
          duration: 6000,
        });
        break;

      // Connection events
      case "connected":
        // Silent - connection indicator in header
        break;

      default:
        // Ignore unknown events
        break;
    }
  }, [lastEvent]);

  // Show connection status on disconnect/reconnect
  // Only show after prolonged disconnect (10s), not on brief reconnects
  const hasConnectedOnce = useRef(false);
  const disconnectTimer = useRef<NodeJS.Timeout>(undefined);
  useEffect(() => {
    if (connected === true) {
      hasConnectedOnce.current = true;
      clearTimeout(disconnectTimer.current);
      toast.dismiss("connection-lost");
    } else if (connected === false && hasConnectedOnce.current) {
      disconnectTimer.current = setTimeout(() => {
        toast.error("Connection lost. Reconnecting...", {
          icon: "🔌",
          id: "connection-lost",
        });
      }, 10000);
    }
    return () => clearTimeout(disconnectTimer.current);
  }, [connected]);

  return { connected };
}
