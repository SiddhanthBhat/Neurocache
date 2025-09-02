"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/app/api/client";

type PodcastRow = {
  paperId: string;
  title: string;
  mp3Url: string;   // can be a path like /api/podcasts/global/...
  pdfUrl: string;   // can be a path like /api/projects/.../file
};

function toAbsolute(u: string): string {
  if (!u) return u;
  if (u.startsWith("http://") || u.startsWith("https://")) return u;
  const base =
    process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/+$/, "") ||
    "http://localhost:8000"; // safe fallback
  if (u.startsWith("/")) return `${base}${u}`;
  return `${base}/${u}`;
}

export default function ProjectPodcasts({ projectId }: { projectId: string }) {
  const { data } = useQuery({
    queryKey: ["project-podcasts", projectId],
    queryFn: async () =>
      (await api.get<PodcastRow[]>(`/api/projects/${projectId}/podcasts`)).data,
    enabled: !!projectId,
  });

  if (!data || data.length === 0) {
    return <div className="text-sm text-gray-500">No podcasts yet. Select files and run Podcast.</div>;
  }

  return (
    <div className="space-y-4">
      {data.map((row) => {
        const mp3 = toAbsolute(row.mp3Url);
        const pdf = toAbsolute(row.pdfUrl);
        return (
          <div key={row.title + row.mp3Url} className="border border-gray-200 rounded-md p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-semibold truncate">{row.title}</div>
                {row.pdfUrl && (
                  <a href={pdf} target="_blank" rel="noreferrer" className="text-xs text-blue-600 underline">
                    Open PDF
                  </a>
                )}
              </div>
              <a href={mp3} target="_blank" rel="noreferrer" className="text-[11px] text-blue-600 underline">
                Open MP3
              </a>
            </div>
            <div className="mt-2">
              <audio controls src={mp3} className="w-full" />
            </div>
            <div className="text-[10px] text-gray-400 mt-1 break-all">src: {mp3}</div>
          </div>
        );
      })}
    </div>
  );
}
