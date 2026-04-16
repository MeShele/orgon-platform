"use client";

import { cn } from "@/lib/utils";
import Link, { LinkProps } from "next/link";
import React, { useState, createContext, useContext } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Icon } from "@/lib/icons";

interface Links {
  label: string;
  href: string;
  icon: React.JSX.Element | React.ReactNode;
  activeIcon?: React.JSX.Element | React.ReactNode;
}

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  animate: boolean;
  hovered: boolean;
  setHovered: React.Dispatch<React.SetStateAction<boolean>>;
}

const SidebarContext = createContext<SidebarContextProps | undefined>(
  undefined
);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
};

export const SidebarProvider = ({
  children,
  open: openProp,
  setOpen: setOpenProp,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  const [openState, setOpenState] = useState(false);
  const [hoveredState, setHoveredState] = useState(false);

  const open = openProp !== undefined ? openProp : openState;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setOpenState;

  return (
    <SidebarContext.Provider value={{ open, setOpen, animate: animate, hovered: hoveredState, setHovered: setHoveredState }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const Sidebar = ({
  children,
  open,
  setOpen,
  animate,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  return (
    <SidebarProvider open={open} setOpen={setOpen} animate={animate}>
      {children}
    </SidebarProvider>
  );
};

export const SidebarBody = (props: React.ComponentProps<typeof motion.div>) => {
  return (
    <>
      <DesktopSidebar {...props} />
      <MobileSidebar {...(props as React.ComponentProps<"div">)} />
    </>
  );
};

export const DesktopSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<typeof motion.div>) => {
  const { animate, hovered, setHovered } = useSidebar();
  
  return (
    <>
      <motion.div
        className={cn(
          "h-full px-4 py-4 hidden lg:flex lg:flex-col bg-white dark:bg-slate-950 flex-shrink-0 border-r border-slate-200 dark:border-slate-800",
          className
        )}
        initial={{
          width: "70px",
        }}
        animate={{
          width: animate ? (hovered ? "260px" : "70px") : "260px",
        }}
        transition={{
          duration: 0.2,
          ease: "easeInOut",
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        {...props}
      >
        {children}
      </motion.div>
    </>
  );
};

export const MobileSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) => {
  const { open, setOpen } = useSidebar();
  
  return (
    <>
      {/* Mobile overlay menu - no header bar, triggered from Header component */}
      <AnimatePresence>
        {open && (
            <motion.div
              initial={{ x: "-100%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "-100%", opacity: 0 }}
              transition={{
                duration: 0.3,
                ease: "easeInOut",
              }}
              className={cn(
                "lg:hidden fixed h-full w-full inset-0 bg-white dark:bg-slate-950 p-4 z-[100] flex flex-col justify-between",
                className
              )}
            >
              <div
                className="absolute right-4 top-4 z-50 text-slate-800 dark:text-slate-200"
                onClick={() => setOpen(!open)}
              >
                <Icon icon="solar:close-circle-linear" className="text-2xl" />
              </div>
              {children}
            </motion.div>
          )}
      </AnimatePresence>
    </>
  );
};

export const SidebarLink = ({
  link,
  className,
  isActive,
  ...props
}: {
  link: Links;
  className?: string;
  isActive?: boolean;
  props?: LinkProps;
}) => {
  const { open, animate, setOpen, hovered } = useSidebar();
  const isExpanded = hovered || open; // Use hovered for desktop, open for mobile

  return (
    <Link
      href={link.href}
      onClick={() => setOpen(false)} // Close mobile menu on navigation
      className={cn(
        "flex items-center justify-start gap-3 group/sidebar py-2 rounded-lg transition-all",
        isActive
          ? "border border-slate-200 dark:border-slate-800 bg-slate-100 dark:bg-slate-900/50 text-slate-900 dark:text-white shadow-sm px-3"
          : "border border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 hover:text-slate-900 dark:hover:text-slate-200 px-3",
        className
      )}
      {...props}
    >
      <div
        className={cn(
          "text-lg",
          isActive
            ? "text-indigo-600 dark:text-indigo-400"
            : "text-slate-500 group-hover/sidebar:text-slate-700 dark:group-hover/sidebar:text-slate-300"
        )}
      >
        {isActive && link.activeIcon ? link.activeIcon : link.icon}
      </div>

      <motion.span
        animate={{
          display: animate ? (isExpanded ? "inline-block" : "none") : "inline-block",
          opacity: animate ? (isExpanded ? 1 : 0) : 1,
        }}
        transition={{
          duration: 0.2,
          ease: "easeInOut",
        }}
        className="text-sm font-medium whitespace-pre"
      >
        {link.label}
      </motion.span>
    </Link>
  );
};
