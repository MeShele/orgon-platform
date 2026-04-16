"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface ButtonHoverProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  loading?: boolean;
  fullWidth?: boolean;
}

const variantClasses = {
  primary:
    "bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40",
  secondary:
    "bg-slate-700 text-white hover:bg-slate-600 dark:bg-slate-800 dark:hover:bg-slate-700 shadow-lg shadow-slate-500/10 hover:shadow-slate-500/20",
  danger:
    "bg-red-600 text-white hover:bg-red-700 dark:bg-red-500 dark:hover:bg-red-600 shadow-lg shadow-red-500/20 hover:shadow-red-500/40",
  ghost:
    "bg-transparent text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700",
};

const sizeClasses = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export const ButtonHover = React.forwardRef<
  HTMLButtonElement,
  ButtonHoverProps
>(
  (
    {
      children,
      className,
      variant = "primary",
      size = "md",
      icon,
      iconPosition = "left",
      loading = false,
      fullWidth = false,
      disabled,
      onClick,
      type,
      ...restProps
    },
    ref
  ) => {
    return (
      <motion.button
        ref={ref}
        whileHover={{
          scale: disabled || loading ? 1 : 1.02,
          y: disabled || loading ? 0 : -2,
        }}
        whileTap={{ scale: disabled || loading ? 1 : 0.98 }}
        transition={{
          type: "spring",
          stiffness: 400,
          damping: 17,
        }}
        className={cn(
          "relative inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-200",
          "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-slate-900",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          fullWidth && "w-full",
          className
        )}
        disabled={disabled || loading}
        onClick={onClick}
        // @ts-ignore - type prop conflict with motion
        type={type}
      >
        {loading && (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: "linear",
            }}
            className="absolute inset-0 flex items-center justify-center"
          >
            <div className="h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
          </motion.div>
        )}

        <span
          className={cn(
            "flex items-center gap-2",
            loading && "opacity-0"
          )}
        >
          {icon && iconPosition === "left" && (
            <motion.span
              whileHover={{ rotate: 5 }}
              transition={{ duration: 0.2 }}
            >
              {icon}
            </motion.span>
          )}
          {children}
          {icon && iconPosition === "right" && (
            <motion.span
              whileHover={{ rotate: -5 }}
              transition={{ duration: 0.2 }}
            >
              {icon}
            </motion.span>
          )}
        </span>
      </motion.button>
    );
  }
);

ButtonHover.displayName = "ButtonHover";
