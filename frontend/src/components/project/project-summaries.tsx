"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/app/api/client";

type SummaryItem = {
  paperId: string;
  title: string;
  summary: string;
  conference: string;
  year: number;
  domain: string;
  tags: string;
  pdfUrl: string;
};

export default function ProjectSummaries({ projectId }: { projectId: string }) {
  const { data } = useQuery({
    queryKey: ["project-summaries", projectId],
    queryFn: async () =>
      (await api.get<SummaryItem[]>(`/api/projects/${projectId}/summaries`)).data,
    enabled: !!projectId,
  });

  if (!data || data.length === 0) {
    return <div className="text-sm text-gray-500">No summaries yet. Select files and run Summarize.</div>;
  }

  return (
    <div className="space-y-3">
      {data.map((item) => (
        <div key={item.paperId} className="border border-gray-200 rounded-md p-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-sm font-semibold truncate">{item.title}</div>
              <div className="text-xs text-gray-500">
                {item.conference} • {item.year} • {item.domain}
              </div>
            </div>
            <a
              href={`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}${item.pdfUrl}`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-blue-600 underline whitespace-nowrap"
            >
              Open PDF
            </a>
          </div>
          <p className="text-sm mt-2 whitespace-pre-wrap">{item.summary}</p>
          {item.tags && (
            <div className="text-[11px] text-gray-500 mt-1">Tags: {item.tags}</div>
          )}
        </div>
      ))}
    </div>
  );
}
