"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/app/api/client";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle
} from "@/components/ui/dialog";

import { useState } from "react";

export default function DeleteProjectButton({ projectId, onDeleted }: {
  projectId: string;
  onDeleted?: () => void;
}) {
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const del = useMutation({
    mutationFn: async () => {
      await api.delete(`/api/projects/${projectId}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setOpen(false);
      onDeleted?.();
      // If we’re already inside the project page, go home
      router.push("/");
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger>
        <Button variant="destructive">Delete</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete project?</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 text-sm">
          <p>This will remove the project directory and all files.</p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => setOpen(false)}
              disabled={del.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={() => del.mutate()}
              disabled={del.isPending}
            >
              {del.isPending ? "Deleting..." : "Confirm Delete"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
