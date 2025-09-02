"use client";

import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: string;
  size?: string;
}

/**
 * A minimal button component. It applies some basic Tailwind styles and
 * forwards all props to the underlying button. The `variant` and
 * `size` props are accepted for API compatibility but currently have
 * no effect.
 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ className, variant, size, ...props }, ref) {
    return (
      <button
        ref={ref}
        className={
          [
            "inline-flex items-center justify-center",
            "px-4 py-2",
            "rounded-md",
            "bg-blue-600",
            "text-white",
            "hover:bg-blue-700",
            "disabled:opacity-50",
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