"use client";

import { Paper, MetadataRow } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/app/api/client";

export default function SummaryPanel({
  paper,
  projectId,
}: {
  paper: Paper | null;
  projectId: string;
}) {
  const { data } = useQuery({
    queryKey: ["metadata", projectId, paper?.id],
    queryFn: async () => {
      if (!paper) return undefined;
      return (
        await api.get<MetadataRow>(
          `/api/projects/${projectId}/papers/${paper.id}/metadata`
        )
      ).data;
    },
    enabled: !!paper?.id,
  });

  if (!paper) {
    return <div className="text-sm text-gray-500">Select a paper.</div>;
  }
  if (!data) {
    return (
      <div className="text-sm text-gray-500">
        No summary yet. Run Summarize.
      </div>
    );
  }
  return (
    <div className="border border-gray-200 rounded-md p-4 space-y-2">
      <div className="text-lg font-medium truncate">{data.title}</div>
      <div className="text-sm text-gray-500">
        {data.conference} • {data.year} • {data.domain}
      </div>
      <p className="text-sm leading-relaxed whitespace-pre-wrap">
        {data.summary}
      </p>
      <div className="text-xs text-gray-500">Tags: {data.tags}</div>
    </div>
  );
}
