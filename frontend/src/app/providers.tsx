"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";

/**
 * Provides a react-query client for the entire app. Instantiates a single
 * QueryClient on mount and reuses it for all children. This avoids re-
 * creating a new client on every render which would reset caches.
 */
export default function Providers({ children }: { children: ReactNode }) {
  // Lazily create the QueryClient so it's only created once per client.
  const [client] = useState(() => new QueryClient());
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}