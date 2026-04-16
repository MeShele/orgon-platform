"use client";

import React from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface AnimatedIconProps {
  icon: React.ReactNode;
  animation?:
    | "spin"
    | "bounce"
    | "shake"
    | "pulse"
    | "heartbeat"
    | "wiggle"
    | "none";
  trigger?: "hover" | "always" | "click";
  className?: string;
  onClick?: () => void;
}

const animations = {
  spin: {
    animate: { rotate: 360 },
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: "linear",
    },
  },
  bounce: {
    animate: { y: [0, -10, 0] },
    transition: {
      duration: 0.6,
      repeat: Infinity,
      repeatDelay: 1,
    },
  },
  shake: {
    animate: { x: [-5, 5, -5, 5, 0] },
    transition: {
      duration: 0.5,
    },
  },
  pulse: {
    animate: { scale: [1, 1.2, 1] },
    transition: {
      duration: 1,
      repeat: Infinity,
    },
  },
  heartbeat: {
    animate: { scale: [1, 1.3, 1, 1.3, 1] },
    transition: {
      duration: 1,
      repeat: Infinity,
      repeatDelay: 2,
    },
  },
  wiggle: {
    animate: { rotate: [-10, 10, -10, 10, 0] },
    transition: {
      duration: 0.5,
    },
  },
  none: {
    animate: {},
    transition: {},
  },
};

export const AnimatedIcon: React.FC<AnimatedIconProps> = ({
  icon,
  animation = "none",
  trigger = "always",
  className,
  onClick,
}) => {
  const [isHovered, setIsHovered] = React.useState(false);
  const [isClicked, setIsClicked] = React.useState(false);

  const shouldAnimate =
    trigger === "always" ||
    (trigger === "hover" && isHovered) ||
    (trigger === "click" && isClicked);

  const handleClick = () => {
    if (trigger === "click") {
      setIsClicked(true);
      setTimeout(() => setIsClicked(false), 500);
    }
    onClick?.();
  };

  const animationProps = shouldAnimate
    ? animations[animation]
    : { animate: {}, transition: {} };

  return (
    <motion.div
      className={cn("inline-flex items-center justify-center", className)}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      onClick={handleClick}
      {...animationProps}
    >
      {icon}
    </motion.div>
  );
};
