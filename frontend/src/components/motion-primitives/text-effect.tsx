// Motion Primitives · TextEffect
// Source: https://motion-primitives.com/docs/text-effect
// Splits text into per-word motion children with a blur+lift entrance.

"use client";

import { motion, type Variants, useReducedMotion } from "framer-motion";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TextEffectProps {
  children: string;
  per?: "word" | "char";
  as?: "h1" | "h2" | "h3" | "h4" | "p" | "span" | "div";
  className?: string;
  delay?: number;
  duration?: number;
  /** Trigger on viewport entry instead of mount. */
  onScroll?: boolean;
}

const containerVariants: Variants = {
  hidden: {},
  visible: ({ stagger, delay }: { stagger: number; delay: number }) => ({
    transition: {
      staggerChildren: stagger,
      delayChildren: delay,
    },
  }),
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 12, filter: "blur(8px)" },
  visible: ({ duration }: { duration: number }) => ({
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: { duration, ease: [0.22, 1, 0.36, 1] as const },
  }),
};

export function TextEffect({
  children,
  per = "word",
  as = "p",
  className,
  delay = 0,
  duration = 0.5,
  onScroll = false,
}: TextEffectProps) {
  const reduce = useReducedMotion();
  const Tag = motion[as] as typeof motion.div;

  const segments = per === "word" ? children.split(/(\s+)/) : Array.from(children);
  const stagger = per === "word" ? 0.06 : 0.018;

  const triggerProps = onScroll
    ? { initial: "hidden", whileInView: "visible", viewport: { once: true, margin: "-60px" } }
    : { initial: "hidden", animate: "visible" };

  if (reduce) {
    return <Tag className={className}>{children}</Tag>;
  }

  return (
    <Tag
      {...triggerProps}
      variants={containerVariants}
      custom={{ stagger, delay }}
      className={cn(className)}
    >
      {segments.map((seg, i) =>
        seg.match(/^\s+$/) ? (
          <span key={i}>{seg}</span>
        ) : (
          <motion.span
            key={i}
            variants={itemVariants}
            custom={{ duration }}
            className="inline-block"
          >
            {seg}
          </motion.span>
        ),
      )}
    </Tag>
  );
}
