"use client";

/**
 * TiltCard — wraps content with a subtle 3D rotation driven by cursor
 * position. Max ±6° on each axis; snaps back via spring on leave.
 * Uses only `transform` and respects prefers-reduced-motion.
 */

import { motion, useMotionValue, useSpring, useTransform, useReducedMotion } from "framer-motion";
import { type ReactNode, useRef } from "react";
import { cn } from "@/lib/utils";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** Max rotation degrees on each axis (default 6) */
  max?: number;
  /** Optional translateZ to lift the card on hover (px) */
  lift?: number;
}

export function TiltCard({ children, className, max = 6, lift = 4 }: TiltCardProps) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);

  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const smx = useSpring(mx, { stiffness: 180, damping: 16, mass: 0.4 });
  const smy = useSpring(my, { stiffness: 180, damping: 16, mass: 0.4 });
  const rotateY = useTransform(smx, [-0.5, 0.5], [-max, max]);
  const rotateX = useTransform(smy, [-0.5, 0.5], [max, -max]);
  const z = useMotionValue(0);
  const sz = useSpring(z, { stiffness: 200, damping: 18 });

  function onMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reduce || !ref.current) return;
    const r = ref.current.getBoundingClientRect();
    mx.set((e.clientX - r.left) / r.width - 0.5);
    my.set((e.clientY - r.top) / r.height - 0.5);
    z.set(lift);
  }
  function onLeave() {
    mx.set(0); my.set(0); z.set(0);
  }

  return (
    <motion.div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      style={{ rotateX, rotateY, z: sz, transformPerspective: 1000 }}
      className={cn("will-change-transform", className)}
    >
      {children}
    </motion.div>
  );
}
