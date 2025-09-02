"use client";

import { useMemo } from "react";
import type { Paper } from "@/lib/types";
import { Button } from "@/components/ui/button";

function toAbsolute(u: string): string {
  if (!u) return u;
  if (u.startsWith("http://") || u.startsWith("https://")) return u;
  const base =
    process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
    "http://localhost:8000";
  if (u.startsWith("/")) return `${base}${u}`;
  return `${base}/${u}`;
}

export default function PDFViewer({
  paper,
  projectId,
}: {
  paper: Paper | null;
  projectId: string;
}) {
  if (!paper) return null;

  const rel = `/api/projects/${projectId}/papers/${paper.id}/file`;
  const url = useMemo(() => toAbsolute(rel), [rel]);

  const download = () => {
    const a = document.createElement("a");
    a.href = url;
    a.download = paper.originalName || "paper.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  return (
    <div className="border border-gray-200 rounded-md">
      <div className="flex items-center justify-between p-2 border-b border-gray-200">
        <div className="text-sm font-medium truncate">{paper.originalName}</div>
        <div className="flex gap-2">
          <Button size="sm" onClick={download}>Download</Button>
          <a href={url} target="_blank" rel="noreferrer" className="text-sm underline text-blue-600">
            Open in new tab
          </a>
        </div>
      </div>
      <iframe key={paper.id} src={`${url}#view=FitH`} className="w-full" style={{ height: "80vh" }} title="PDF" />
      <div className="px-2 py-1 text-[10px] text-gray-400 break-all">pdf src: {url}</div>
    </div>
  );
}
