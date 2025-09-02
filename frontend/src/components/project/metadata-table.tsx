"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/app/api/client";
import { MetadataRow } from "@/lib/types";
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Button } from "@/components/ui/button";

/**
 * Table component to display all extracted metadata for papers in a project.
 * Uses react-table for headless table logic and applies a basic Tailwind
 * style. Includes a button to download the metadata as CSV via the
 * backend endpoint.
 */
export default function MetadataTable({ projectId }: { projectId: string }) {
  const { data } = useQuery({
    queryKey: ["table", projectId],
    queryFn: async () => {
      return (
        await api.get<MetadataRow[]>(
          `/api/projects/${projectId}/metadata/table`
        )
      ).data;
    },
    enabled: !!projectId,
  });

  const columns: ColumnDef<MetadataRow>[] = [
    { accessorKey: "title", header: "Title" },
    { accessorKey: "conference", header: "Conf" },
    { accessorKey: "year", header: "Year" },
    { accessorKey: "domain", header: "Domain" },
    { accessorKey: "link", header: "Link" },
    { accessorKey: "tags", header: "Tags" },
    { accessorKey: "ready_to_publish", header: "Ready" },
    { accessorKey: "script_lines", header: "Script" },
  ];

  const table = useReactTable({
    data: data ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const downloadCSV = async () => {
    const res = await api.get(
      `/api/projects/${projectId}/metadata/csv`,
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `project_${projectId}_metadata.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="border border-gray-200 rounded-md p-3">
      <div className="mb-2 flex justify-end">
        <Button size="sm" onClick={downloadCSV}>
          Download CSV
        </Button>
      </div>
      <div className="overflow-auto">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-2 py-1 text-left font-semibold"
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b hover:bg-gray-50">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-2 py-1">
                    {flexRender(
                      cell.column.columnDef.cell,
                      cell.getContext()
                    )}
                  </td>
                ))}
              </tr>
            ))}
            {data && data.length === 0 && (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-2 py-1 text-center text-sm text-gray-500"
                >
                  No metadata available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}