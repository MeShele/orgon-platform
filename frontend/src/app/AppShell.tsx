"use client";

import { AceternitySidebar } from "@/components/layout/AceternitySidebar";
import { TooltipProvider } from "@/components/common/TooltipProvider";
import { ToastProvider } from "@/components/providers/ToastProvider";
import { AuthProvider } from "@/contexts/AuthContext";
import { SidebarProvider } from "@/components/aceternity/sidebar";
import { ReactNode, useState } from "react";
import { useToastEvents } from "@/hooks/useToastEvents";

export function AppShell({ children }: { children: ReactNode }) {
  // Enable toast notifications for real-time events
  useToastEvents();
  
  // Sidebar state management at AppShell level
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <AuthProvider>
      <TooltipProvider>
        <ToastProvider />
        <SidebarProvider open={sidebarOpen} setOpen={setSidebarOpen}>
          <div className="flex min-h-screen w-full bg-slate-50 dark:bg-slate-950 overflow-x-hidden">
            <AceternitySidebar />
            <main className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
              {children}
            </main>
          </div>
        </SidebarProvider>
      </TooltipProvider>
    </AuthProvider>
  );
}
