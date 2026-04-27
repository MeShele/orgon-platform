"use client";

/**
 * ToastProvider — react-hot-toast wired to Crimson Ledger CSS tokens.
 * Uses CSS variables so light/dark switch automatically without a re-mount.
 */

import { Toaster } from "react-hot-toast";

export function ToastProvider() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: "var(--card)",
          color: "var(--card-foreground)",
          border: "1px solid var(--border)",
          padding: "12px 16px",
          borderRadius: "0",
          boxShadow: "var(--shadow-md)",
          fontSize: "13px",
          fontFamily: "var(--font-sans)",
        },
        success: {
          iconTheme: {
            primary: "var(--success)",
            secondary: "var(--success-foreground)",
          },
        },
        error: {
          iconTheme: {
            primary: "var(--destructive)",
            secondary: "var(--destructive-foreground)",
          },
        },
        loading: {
          iconTheme: {
            primary: "var(--primary)",
            secondary: "var(--primary-foreground)",
          },
        },
      }}
    />
  );
}
