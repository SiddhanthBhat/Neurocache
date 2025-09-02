"use client";

import React from "react";

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: string;
}

/**
 * A simple badge component. Useful for status indicators or labels. The
 * `variant` prop is accepted for API compatibility but currently has no
 * effect on styling.
 */
export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  function Badge({ className, variant, ...props }, ref) {
    return (
      <span
        ref={ref}
        className={
          [
            "inline-block",
            "rounded-md",
            "bg-gray-200",
            "px-2",
            "py-1",
            "text-xs",
            "font-semibold",
            className,
          ]
            .filter(Boolean)
            .join(" ")
        }
        {...props}
      />
    );
  }
);