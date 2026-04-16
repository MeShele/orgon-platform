"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface AnimatedInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  icon?: React.ReactNode;
  onIconClick?: () => void;
}

export const AnimatedInput = React.forwardRef<
  HTMLInputElement,
  AnimatedInputProps
>(
  (
    {
      className,
      label,
      helperText,
      error,
      icon,
      onIconClick,
      type = "text",
      ...props
    },
    ref
  ) => {
    const [isFocused, setIsFocused] = useState(false);
    const [hasValue, setHasValue] = useState(
      props.value !== undefined && props.value !== ""
    );

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true);
      props.onFocus?.(e);
    };

    const handleBlur = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(false);
      setHasValue(e.target.value !== "");
      props.onBlur?.(e);
    };

    const showFloatingLabel = isFocused || hasValue;

    return (
      <div className="relative w-full">
        {/* Animated Background Glow */}
        {isFocused && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 -z-10 rounded-xl bg-gradient-to-r from-blue-500/20 to-purple-500/20 blur-xl"
          />
        )}

        {/* Input Container */}
        <div className="relative">
          <input
            ref={ref}
            type={type}
            onFocus={handleFocus}
            onBlur={handleBlur}
            className={cn(
              "peer w-full rounded-xl border bg-slate-900/40 px-4 pb-2 pt-6 text-sm text-white transition-all duration-300",
              "placeholder-transparent",
              "focus:outline-none focus:ring-2",
              error
                ? "border-red-500/50 focus:border-red-500 focus:ring-red-500/20"
                : "border-slate-700 focus:border-blue-500 focus:ring-blue-500/20",
              icon && "pr-10",
              className
            )}
            {...props}
          />

          {/* Floating Label */}
          {label && (
            <motion.label
              initial={false}
              animate={{
                y: showFloatingLabel ? 0 : 8,
                scale: showFloatingLabel ? 0.85 : 1,
                color: isFocused
                  ? error
                    ? "rgb(239 68 68)"
                    : "rgb(59 130 246)"
                  : "rgb(148 163 184)",
              }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="absolute left-4 top-2 origin-left pointer-events-none font-medium"
            >
              {label}
            </motion.label>
          )}

          {/* Icon */}
          {icon && (
            <div
              className={cn(
                "absolute right-3 top-1/2 -translate-y-1/2 text-slate-400",
                onIconClick && "cursor-pointer hover:text-slate-300"
              )}
              onClick={onIconClick}
            >
              {icon}
            </div>
          )}
        </div>

        {/* Helper Text / Error */}
        {(helperText || error) && (
          <motion.p
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "mt-1.5 text-xs",
              error ? "text-red-400" : "text-slate-400"
            )}
          >
            {error || helperText}
          </motion.p>
        )}
      </div>
    );
  }
);

AnimatedInput.displayName = "AnimatedInput";
