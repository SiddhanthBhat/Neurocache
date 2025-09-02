"use client";

import React, { createContext, useContext, useState } from "react";

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined);

/**
 * Root component for tabs. Accepts a default value and provides state
 * context to child triggers and content. Use one Tabs per tab set.
 */
export function Tabs({
  defaultValue,
  children,
}: {
  defaultValue: string;
  children: React.ReactNode;
}) {
  const [value, setValue] = useState(defaultValue);
  return (
    <TabsContext.Provider value={{ value, setValue }}>
      {children}
    </TabsContext.Provider>
  );
}

/**
 * Wrapper for grouping tab triggers. Does not apply any styling.
 */
export function TabsList({ children }: { children: React.ReactNode }) {
  return <div className="flex gap-2 border-b border-gray-200 mb-2">{children}</div>;
}

/**
 * Button that switches the current tab when clicked. Applies a bottom
 * border when active.
 */
export function TabsTrigger({
  value,
  children,
}: {
  value: string;
  children: React.ReactNode;
}) {
  const context = useContext(TabsContext);
  if (!context) throw new Error("TabsTrigger must be used within Tabs");
  const isActive = context.value === value;
  return (
    <button
      onClick={() => context.setValue(value)}
      className={
        [
          "px-3 py-1",
          "text-sm",
          "font-medium",
          isActive ? "border-b-2 border-blue-600" : "border-b-2 border-transparent",
        ].join(" ")
      }
    >
      {children}
    </button>
  );
}

/**
 * Renders its children only when the tab value matches the current value.
 */
export function TabsContent({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const context = useContext(TabsContext);
  if (!context) throw new Error("TabsContent must be used within Tabs");
  if (context.value !== value) return null;
  return <div className={className}>{children}</div>;
}