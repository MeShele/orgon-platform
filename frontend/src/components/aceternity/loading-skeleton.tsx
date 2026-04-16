"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface SkeletonProps {
  className?: string;
  variant?: "text" | "circular" | "rectangular" | "rounded";
  animation?: "pulse" | "shimmer" | "wave";
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = "text",
  animation = "shimmer",
  width,
  height,
}) => {
  const baseClasses = "bg-slate-700/50 dark:bg-slate-800/50";

  const variantClasses = {
    text: "rounded h-4",
    circular: "rounded-full",
    rectangular: "rounded-none",
    rounded: "rounded-xl",
  };

  const renderAnimation = () => {
    switch (animation) {
      case "pulse":
        return (
          <motion.div
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            className={cn(
              baseClasses,
              variantClasses[variant],
              className
            )}
            style={{ width, height }}
          />
        );

      case "shimmer":
        return (
          <div
            className={cn(
              "relative overflow-hidden",
              baseClasses,
              variantClasses[variant],
              className
            )}
            style={{ width, height }}
          >
            <motion.div
              animate={{ x: ["-100%", "100%"] }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"
              style={{
                transform: "skewX(-20deg)",
              }}
            />
          </div>
        );

      case "wave":
        return (
          <div
            className={cn(
              "relative overflow-hidden",
              baseClasses,
              variantClasses[variant],
              className
            )}
            style={{ width, height }}
          >
            <motion.div
              animate={{
                x: ["-100%", "100%"],
                scaleY: [1, 1.2, 1],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              className="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500/20 to-transparent"
            />
          </div>
        );

      default:
        return null;
    }
  };

  return renderAnimation();
};

// Preset skeleton components
export const SkeletonText: React.FC<{ lines?: number; className?: string }> = ({
  lines = 3,
  className,
}) => (
  <div className={cn("space-y-2", className)}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton
        key={i}
        variant="text"
        width={i === lines - 1 ? "60%" : "100%"}
      />
    ))}
  </div>
);

export const SkeletonCard: React.FC<{ className?: string }> = ({
  className,
}) => (
  <div className={cn("rounded-2xl border border-slate-700 p-6 space-y-4", className)}>
    <div className="flex items-center gap-4">
      <Skeleton variant="circular" width={48} height={48} />
      <div className="flex-1 space-y-2">
        <Skeleton variant="text" width="60%" />
        <Skeleton variant="text" width="40%" />
      </div>
    </div>
    <SkeletonText lines={3} />
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number; className?: string }> = ({
  rows = 5,
  className,
}) => (
  <div className={cn("space-y-3", className)}>
    {/* Header */}
    <div className="grid grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} variant="text" height={20} />
      ))}
    </div>
    {/* Rows */}
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, j) => (
          <Skeleton key={j} variant="text" height={16} />
        ))}
      </div>
    ))}
  </div>
);
