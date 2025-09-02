"use client";

import { Paper, PodcastAsset } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/app/api/client";

export default function PodcastPanel({
  paper,
  projectId,
}: {
  paper: Paper | null;
  projectId: string;
}) {
  const { data: podcasts } = useQuery({
    queryKey: ["podcasts", projectId, paper?.id],
    queryFn: async () => {
      if (!paper) return [] as PodcastAsset[];
      return (
        await api.get<PodcastAsset[]>(
          `/api/projects/${projectId}/papers/${paper.id}/podcasts`
        )
      ).data;
    },
    enabled: !!paper?.id,
  });

  if (!paper) {
    return <div className="text-sm text-gray-500">Select a paper.</div>;
  }
  if (!podcasts || podcasts.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        No podcasts yet. Run Podcast.
      </div>
    );
  }

  const latest = podcasts[0];
  const src = latest.mp3Url.startsWith("http")
    ? latest.mp3Url
    : `${process.env.NEXT_PUBLIC_BACKEND_URL || ""}${latest.mp3Url}`;

  return (
    <div className="space-y-2">
      <audio controls src={src} className="w-full" />
      <div className="text-xs text-gray-500">
        Duration: {latest.durationSec.toFixed(2)}s
      </div>
    </div>
  );
}
