"use client";

import { Paper } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useMemo } from "react";

export default function PDFList({
  papers,
  selectedId,
  selectedIds,
  onSelect,
  onToggle,
}: {
  papers: Paper[];
  selectedId: string | null;
  selectedIds: string[];                 // multi-select state
  onSelect: (id: string) => void;        // focus one paper to view
  onToggle: (id: string) => void;        // add/remove from batch selection
}) {
  const set = useMemo(() => new Set(selectedIds), [selectedIds]);

  return (
    <div className="space-y-2">
      <div className="text-sm font-medium">Files</div>
      <div className="max-h-[60vh] overflow-auto space-y-1 pr-1">
        {papers.map((paper) => {
          const active = selectedId === paper.id;
          const checked = set.has(paper.id);
          return (
            <div
              key={paper.id}
              className={cn(
                "rounded-md p-2 border border-transparent hover:bg-gray-50",
                active && "bg-gray-100 border-gray-200"
              )}
            >
              <label className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(paper.id)}
                  className="mt-1"
                />
                <button
                  className="text-left flex-1"
                  onClick={() => onSelect(paper.id)}
                  title={paper.originalName}
                >
                  <div className="text-sm font-medium truncate">
                    {paper.originalName}
                  </div>
                  <div className="text-[11px] text-gray-500">
                    {(paper.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </button>
              </label>
            </div>
          );
        })}
        {papers.length === 0 && (
          <div className="text-xs text-gray-500">No files uploaded yet.</div>
        )}
      </div>
    </div>
  );
}
