"use client";

// Dialog primitives — Radix UI Dialog + Framer Motion for entrance.
// Visual style follows Crimson Ledger v2 (paper card, ink border).

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { Icon } from "@/lib/icons";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;

interface DialogContentProps
  extends React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> {
  size?: "sm" | "md" | "lg";
  showClose?: boolean;
  /** Provide for screen-readers when no DialogTitle is rendered. */
  ariaLabel?: string;
}

const SIZE: Record<NonNullable<DialogContentProps["size"]>, string> = {
  sm: "max-w-md",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(({ className, children, size = "md", showClose = true, ariaLabel, ...props }, ref) => {
  const reduce = useReducedMotion();

  return (
    <DialogPrimitive.Portal forceMount>
      <AnimatePresence>
        <DialogPrimitive.Overlay asChild forceMount>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="fixed inset-0 z-50 bg-foreground/40 backdrop-blur-[2px]"
          />
        </DialogPrimitive.Overlay>

        <DialogPrimitive.Content
          ref={ref}
          forceMount
          aria-label={ariaLabel}
          className={cn(
            "fixed left-[50%] top-[50%] z-50 w-full -translate-x-1/2 -translate-y-1/2",
            "outline-none",
            SIZE[size],
            className,
          )}
          {...props}
          asChild
        >
          <motion.div
            initial={reduce ? { opacity: 1 } : { opacity: 0, scale: 0.97, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={reduce ? { opacity: 0 } : { opacity: 0, scale: 0.97, y: 4 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] as const }}
            className="bg-card text-foreground border border-border shadow-xl"
          >
            {children}
            {showClose && (
              <DialogPrimitive.Close
                className="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:outline-2 focus-visible:outline-primary"
                aria-label="Close"
              >
                <Icon icon="solar:close-circle-linear" className="text-lg" />
              </DialogPrimitive.Close>
            )}
          </motion.div>
        </DialogPrimitive.Content>
      </AnimatePresence>
    </DialogPrimitive.Portal>
  );
});
DialogContent.displayName = "DialogContent";

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col gap-1 px-5 py-4 border-b border-border", className)}
    {...props}
  />
);
DialogHeader.displayName = "DialogHeader";

const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex justify-end gap-2 px-5 py-4 border-t border-border bg-muted/40", className)}
    {...props}
  />
);
DialogFooter.displayName = "DialogFooter";

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn("text-[15px] font-medium tracking-tight text-foreground", className)}
    {...props}
  />
));
DialogTitle.displayName = "DialogTitle";

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-[13px] text-muted-foreground", className)}
    {...props}
  />
));
DialogDescription.displayName = "DialogDescription";

export {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
};
