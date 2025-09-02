"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";
import { Project } from "@/lib/types";
import CreateProjectDialog from "@/components/project/create-project-dialog";
import TopBar from "@/components/nav/topbar";
import DeleteProjectButton from "@/components/project/delete-project-button";

export default function ProjectsPage() {
  const { data } = useQuery({
    queryKey: ["projects"],
    queryFn: async () => (await api.get<Project[]>("/api/projects")).data,
  });

  return (
    <>
    <TopBar />
    <div className="container mx-auto px-4 py-8">
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <CreateProjectDialog />
      </div>

      {data && data.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.map((project) => (
          <div key={project.id} className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <Link href={`/projects/${project.id}`}>
                  <div className="text-lg font-medium truncate hover:underline">
                    {project.name}
                  </div>
                </Link>
                {project.description && (
                  <p className="text-sm text-gray-500 line-clamp-2">
                    {project.description}
                  </p>
                )}
              </div>
              <DeleteProjectButton projectId={project.id} />
            </div>
          </div>
        ))}
        </div>
      ) : (
        <p className="text-gray-500">No projects yet. Create one to get started.</p>
      )}
    </div>
     </div>
  </>
  );
}
