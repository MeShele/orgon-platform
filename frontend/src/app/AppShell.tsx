"use client";

import { AceternitySidebar } from "@/components/layout/AceternitySidebar";
import { MobileSidebar } from "@/components/layout/MobileSidebar";
import { TooltipProvider } from "@/components/common/TooltipProvider";
import { ToastProvider } from "@/components/providers/ToastProvider";
import { SidebarProvider } from "@/components/aceternity/sidebar";
import { ReactNode, useState } from "react";
import { useToastEvents } from "@/hooks/useToastEvents";

export function AppShell({ children }: { children: ReactNode }) {
  useToastEvents();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <TooltipProvider>
      <ToastProvider />
      <SidebarProvider open={sidebarOpen} setOpen={setSidebarOpen}>
        <div className="flex min-h-screen w-full bg-background text-foreground overflow-x-hidden">
          <AceternitySidebar />
          <MobileSidebar />
          <main className="flex min-h-screen flex-1 flex-col overflow-x-hidden">
            {children}
          </main>
        </div>
      </SidebarProvider>
    </TooltipProvider>
  );
}
