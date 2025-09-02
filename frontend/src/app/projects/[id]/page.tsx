"use client";

import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "@/app/api/client";
import { Project, Paper } from "@/lib/types";
import PDFUploader from "@/components/project/pdf-uploader";
import PDFList from "@/components/project/pdf-list";
import PDFViewer from "@/components/project/pdf-viewer";
import ProjectSummaries from "@/components/project/project-summaries";
import ProjectPodcasts from "@/components/project/project-podcasts";
import MetadataTable from "@/components/project/metadata-table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import TopBar from "@/components/nav/topbar";
import { Button } from "@/components/ui/button";

export default function ProjectPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id as string;
  const qc = useQueryClient();

  const { data: project } = useQuery({
    queryKey: ["project", projectId],
    queryFn: async () =>
      (await api.get<Project>(`/api/projects/${projectId}`)).data,
    enabled: !!projectId,
  });

  const { data: papers } = useQuery({
    queryKey: ["papers", projectId],
    queryFn: async () =>
      (await api.get<Paper[]>(`/api/projects/${projectId}/papers`)).data,
    enabled: !!projectId,
  });

  // Focused paper for viewing
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const activePaper = useMemo(
    () => papers?.find((p) => p.id === selectedPaperId) || papers?.[0] || null,
    [papers, selectedPaperId]
  );

  // Multi-select for batch actions
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const toggle = (id: string) =>
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );

  // Batch mutations
  const summarizeBatch = useMutation({
    mutationFn: async (ids: string[]) =>
      (await api.post(`/api/projects/${projectId}/papers/tools/summarize`, { paperIds: ids })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-summaries", projectId] });
      qc.invalidateQueries({ queryKey: ["metadata", projectId] }); // in case any single summary view is open
    },
  });

  const podcastBatch = useMutation({
    mutationFn: async (ids: string[]) =>
      (await api.post(`/api/projects/${projectId}/papers/tools/podcast`, { paperIds: ids })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-podcasts", projectId] });
    },
  });

  const canBatch = selectedIds.length > 0;

  return (
    <>
      <TopBar />
      <div className="container mx-auto px-4 py-6">
        {/* Header */}
        <div className="mb-4">
          <h1 className="text-xl font-semibold truncate">
            {project?.name || "Project"}
          </h1>
          {project?.description && (
            <p className="text-sm text-gray-500 max-w-prose">{project.description}</p>
          )}
        </div>

        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          {/* Sidebar */}
          <div className="space-y-4">
            <PDFUploader projectId={projectId} />
            <Separator />
            {/* Batch action toolbar */}
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                onClick={() => summarizeBatch.mutate(selectedIds)}
                disabled={!canBatch || summarizeBatch.isPending}
                title={canBatch ? "Summarize selected" : "Select files first"}
              >
                {summarizeBatch.isPending ? "Summarizing..." : "Summarize selected"}
              </Button>
              <Button
                size="sm"
                onClick={() => podcastBatch.mutate(selectedIds)}
                disabled={!canBatch || podcastBatch.isPending}
                title={canBatch ? "Generate podcasts" : "Select files first"}
              >
                {podcastBatch.isPending ? "Generating..." : "Podcast selected"}
              </Button>
            </div>
            <PDFList
              papers={papers || []}
              selectedId={activePaper?.id || null}
              selectedIds={selectedIds}
              onSelect={(id) => setSelectedPaperId(id)}
              onToggle={toggle}
            />
          </div>

          {/* Main */}
          <div className="space-y-4">
            <Tabs defaultValue="files">
              <TabsList>
                <TabsTrigger value="files">Files</TabsTrigger>
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="podcasts">Podcasts</TabsTrigger>
                <TabsTrigger value="table">Table</TabsTrigger>
              </TabsList>

              {/* Files tab: only the PDF viewer (no duplicate selector on top) */}
              <TabsContent value="files" className="space-y-4">
                {activePaper ? (
                  <PDFViewer paper={activePaper} projectId={projectId} />
                ) : (
                  <div className="text-sm text-gray-500">Upload a PDF to begin.</div>
                )}
              </TabsContent>

              {/* Summary tab: all summarized papers */}
              <TabsContent value="summary">
                <ProjectSummaries projectId={projectId} />
              </TabsContent>

              {/* Podcasts tab: all podcasted papers */}
              <TabsContent value="podcasts">
                <ProjectPodcasts projectId={projectId} />
              </TabsContent>

              {/* Table tab unchanged */}
              <TabsContent value="table">
                <MetadataTable projectId={projectId} />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </>
  );
}
