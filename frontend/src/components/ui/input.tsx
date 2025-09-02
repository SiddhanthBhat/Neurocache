"use client";

import React from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

/**
 * A basic input component with Tailwind styling. It forwards all props
 * to the native input element. The ref allows usage in forms and
 * external state.
 */
export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  function Input({ className, ...props }, ref) {
    return (
      <input
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