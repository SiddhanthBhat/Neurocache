"use client";

import React from "react";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

/**
 * A basic textarea component with Tailwind styling. Forwards all props
 * to the underlying textarea element. Useful for multi-line input.
 */
export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea({ className, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={
          [
            "w-full",
            "border",
            "border-gray-300",
            "rounded-md",
            "p-2",
            "focus:outline-none",
            "focus:ring",
            "focus:border-blue-500",
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