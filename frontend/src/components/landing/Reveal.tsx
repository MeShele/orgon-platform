"use client";

/**
 * Reveal — scroll-triggered fade-up wrapper.
 * Fires once when the element enters the viewport. Respects
 * prefers-reduced-motion: in that case it renders content immediately.
 */

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { type ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  /** delay in seconds before this item animates */
  delay?: number;
  /** y-offset to start from (px) */
  y?: number;
  /** override duration (s) */
  duration?: number;
  /** stagger child <Reveal> by this much (apply on parent) */
  stagger?: number;
  className?: string;
  as?: "div" | "section" | "article" | "li" | "ul" | "ol";
}

export function Reveal({
  children,
  delay = 0,
  y = 20,
  duration = 0.6,
  stagger,
  className,
  as = "div",
}: RevealProps) {
  const reduce = useReducedMotion();
  const Tag = motion[as] as typeof motion.div;

  const variants: Variants = reduce
    ? { hidden: { opacity: 1, y: 0 }, visible: { opacity: 1, y: 0 } }
    : {
        hidden: { opacity: 0, y },
        visible: {
          opacity: 1,
          y: 0,
          transition: {
            duration,
            ease: [0.22, 1, 0.36, 1],
            delay,
            ...(stagger ? { staggerChildren: stagger, delayChildren: delay } : {}),
          },
        },
      };

  return (
    <Tag
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-80px" }}
      variants={variants}
      className={className}
    >
      {children}
    </Tag>
  );
}

/**
 * Item — child of a Reveal-with-stagger. Inherits parent stagger timing.
 * Use for grids/lists where children should pop in sequentially.
 */
export function RevealItem({
  children,
  y = 16,
  className,
  as = "div",
}: {
  children: ReactNode;
  y?: number;
  className?: string;
  as?: "div" | "li" | "article";
}) {
  const reduce = useReducedMotion();
  const Tag = motion[as] as typeof motion.div;

  const variants: Variants = reduce
    ? { hidden: { opacity: 1, y: 0 }, visible: { opacity: 1, y: 0 } }
    : {
        hidden: { opacity: 0, y },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
        },
      };

  return (
    <Tag variants={variants} className={className}>
      {children}
    </Tag>
  );
}
