/**
 * Types shared between the frontend and backend. These mirror the shape
 * of objects returned by the FastAPI service. Keeping them in one
 * location makes it easier to update fields later.
 */
export type ToolKind =
  | "summarize"
  | "podcast"
  | "recommend"
  | "latex"
  | "import_arxiv"
  | "chat";

export interface Project {
  id: string;
  name: string;
  description?: string;
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface Paper {
  id: string;
  projectId: string;
  title?: string;
  filename: string;
  originalName: string;
  size: number;
  mime: string;
  createdAt: string;
  updatedAt: string;
}

export interface MetadataRow {
  paperId: string;
  conference: string;
  year: number;
  link: string;
  domain: string;
  title: string;
  summary: string;
  tags: string;
  date_added: string;
  ready_to_publish: boolean;
  script_lines: number;
}

export interface PodcastAsset {
  id: string;
  paperId: string;
  mp3Url: string;
  durationSec: number;
  createdAt: string;
}

export interface Job {
  id: string;
  paperId: string;
  tool: ToolKind;
  status: "queued" | "running" | "done" | "error";
  message?: string;
  createdAt: string;
  updatedAt: string;
  output?: any;
}