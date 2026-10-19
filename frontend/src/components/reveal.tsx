"use client";

import { motion, type HTMLMotionProps } from "framer-motion";

/** Viewport-triggered fade-up. Uses IntersectionObserver under the hood
 *  (Framer's whileInView) — never a scroll listener. */
export function Reveal({
  children,
  delay = 0,
  className,
  ...props
}: HTMLMotionProps<"div"> & { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16, filter: "blur(6px)" }}
      whileInView={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.7, ease: [0.32, 0.72, 0, 1], delay }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}
