"use client";

import React from "react";

export function Separator({ className }: { className?: string }) {
  return (
    <hr
      className={
        ["border-t border-gray-200", className].filter(Boolean).join(" ")
      }
    />
  );
}