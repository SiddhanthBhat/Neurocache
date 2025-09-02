# Zotero Plus Frontend

This directory contains a Next.js application scaffolded to work with the
Python backend of your research assistant. It implements the user flows
outlined in the specification:

* List projects and create new ones
* Upload PDF files into each project
* View PDFs in-browser
* Trigger backend jobs to extract metadata and generate podcasts
* Display summaries and podcasts per PDF
* Show a table of extracted metadata for all files in a project and allow
  CSV export

## Getting started

Install dependencies and run the development server:

```bash
cd frontend
npm install
cp .env.example .env.local # or create your own .env.local
npm run dev
```

Create a `.env.local` at the project root (within `frontend/`) and set
`NEXT_PUBLIC_BACKEND_URL` to the URL of your FastAPI server. For example:

```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## UI components

This scaffold imports UI components from the [shadcn/ui](https://ui.shadcn.com/) library
(`@/components/ui/button`, `@/components/ui/dialog`, etc.). You need to
generate these components in your project before the code will compile.

You can add the required components using the shadcn CLI (run from
within `frontend`):

```bash
npx shadcn@latest init
npx shadcn@latest add button dialog input textarea badge tabs separator table
```

Feel free to customize the components or replace them with your own. The
imports in this scaffold assume a standard shadcn setup with the
components placed under `src/components/ui`.

## Notes

This frontend does not include any of the heavy lifting — PDF parsing,
TTS generation, or Gemini summarization. Those remain in your Python
backend. The pages call REST endpoints exposed by FastAPI to perform
these tasks.

You are free to extend this scaffold as you add features such as
reference recommendations, LaTeX editing, arXiv integration and
project-specific chatbots. See the TypeScript types in `src/lib/types.ts`
for guidance on the expected shape of API responses.