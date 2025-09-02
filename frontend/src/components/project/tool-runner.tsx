"use client";

import { Paper } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/app/api/client";
import { useState } from "react";

export default function ToolRunner({
  paper,
  projectId,
}: {
  paper: Paper | null;
  projectId: string;
}) {
  const [status, setStatus] =
    useState<"idle" | "running" | "done" | "error">("idle");
  const [message, setMessage] = useState<string>("");

  const run = (tool: "summarize" | "podcast") =>
    useMutation({
      mutationFn: async () => {
        const url = `/api/projects/${projectId}/papers/${paper!.id}/tools/${tool}`;
        return (await api.post(url)).data as {
          status: string;
          message?: string;
        };
      },
      onMutate: () => {
        setStatus("running");
        setMessage("");
      },
      onSuccess: (res) => {
        setStatus("done");
        setMessage(res?.message || "");
      },
      onError: (e: any) => {
        setStatus("error");
        setMessage(e?.response?.data?.detail || "Failed");
      },
    });

  const summarize = run("summarize");
  const podcast = run("podcast");

  if (!paper) return null;

  const busy = status === "running" || summarize.isPending || podcast.isPending;

  return (
    <div className="space-y-3">
      <div className="text-sm font-medium">Tools</div>
      <div className="flex gap-2">
        <Button onClick={() => summarize.mutate()} disabled={busy}>
          Summarize
        </Button>
        <Button onClick={() => podcast.mutate()} disabled={busy}>
          Podcast
        </Button>
      </div>
      {status !== "idle" && (
        <div className="text-sm">
          Status:
          <Badge variant="secondary" className="ml-2">
            {status}
          </Badge>
          {message && <div className="text-xs text-gray-500 mt-1">{message}</div>}
        </div>
      )}
    </div>
  );
}
