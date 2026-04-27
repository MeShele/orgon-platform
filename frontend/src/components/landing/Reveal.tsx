"use client";

/**
 * Reveal — scroll-triggered fade-up wrapper.
 * Fires once when the element enters the viewport. Respects
 * prefers-reduced-motion: in that case it renders content immediately.
 */

import { motion, useReducedMotion, type Variants } from "framer-motion";
import { type ReactNode, forwardRef } from "react";

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

interface RevealItemProps {
  children: ReactNode;
  y?: number;
  className?: string;
  as?: "div" | "li" | "article";
}

/**
 * Item — child of a Reveal-with-stagger. Inherits parent stagger timing.
 * forwardRef so callers (e.g. AnimatedBeam) can attach a DOM ref.
 */
export const RevealItem = forwardRef<HTMLElement, RevealItemProps>(
  function RevealItem({ children, y = 16, className, as = "div" }, ref) {
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
      <Tag ref={ref as never} variants={variants} className={className}>
        {children}
      </Tag>
    );
  },
);
