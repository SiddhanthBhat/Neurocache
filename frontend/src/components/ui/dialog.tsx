"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

interface DialogContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DialogContext = createContext<DialogContextValue | undefined>(undefined);

/**
 * Provides dialog state to its children. If the `open` prop is
 * controlled, the dialog will reflect external state. Otherwise it
 * manages its own state internally. The `onOpenChange` callback fires
 * whenever the open state changes.
 */
export function Dialog({
  open,
  onOpenChange,
  children,
}: {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}) {
  const [internalOpen, setInternalOpen] = useState(open ?? false);

  // Sync internal state when controlled open prop changes
  useEffect(() => {
    if (open !== undefined) setInternalOpen(open);
  }, [open]);

  const setOpen = (next: boolean) => {
    setInternalOpen(next);
    onOpenChange?.(next);
  };

  return (
    <DialogContext.Provider value={{ open: internalOpen, setOpen }}>
      {children}
    </DialogContext.Provider>
  );
}

/**
 * Button or element that opens the dialog when clicked. Relies on
 * DialogContext to access the `setOpen` function.
 */
export const DialogTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(function DialogTrigger({ children, onClick, ...props }, ref) {
  const context = useContext(DialogContext);
  if (!context) throw new Error("DialogTrigger must be used within Dialog");
  return (
    <button
      ref={ref}
      onClick={(e) => {
        context.setOpen(true);
        onClick?.(e);
      }}
      {...props}
    >
      {children}
    </button>
  );
});

/**
 * The dialog content. It only renders its children when the dialog is
 * open. Clicking on the backdrop closes the dialog.
 */
export const DialogContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(function DialogContent({ children, className, ...props }, ref) {
  const context = useContext(DialogContext);
  if (!context) throw new Error("DialogContent must be used within Dialog");
  if (!context.open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={() => context.setOpen(false)}
    >
      <div
        ref={ref}
        className={
          [
            "bg-white",
            "rounded-md",
            "shadow-lg",
            "p-4",
            "max-w-md",
            "w-full",
            className,
          ]
            .filter(Boolean)
            .join(" ")
        }
        onClick={(e) => e.stopPropagation()}
        {...props}
      >
        {children}
      </div>
    </div>
  );
});

/**
 * Header wrapper for dialog content. Adds margin below its children.
 */
export function DialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="mb-3">{children}</div>;
}

/**
 * Styled title element for dialogs. Uses an h2 for semantic correctness.
 */
export function DialogTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-semibold">{children}</h2>;
}