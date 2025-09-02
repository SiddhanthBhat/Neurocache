"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function TopBar() {
  const pathname = usePathname();
  const inProject = /^\/projects\/[^/]+$/.test(pathname || "");

  return (
    <div className="sticky top-0 z-40 border-b border-gray-800 bg-[#2a2a2e] backdrop-blur">
      <div className="container mx-auto px-4 h-12 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/" className="font-semibold text-gray-200">Neurocache</Link>
          {inProject && (
            <>
              <span className="text-gray-200">/</span>
              <Link href="/" className="text-sm text-blue-600 underline">All Projects</Link>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <a
            href="https://arxiv.org/"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-gray-200 hover:underline"
          >
            arXiv
          </a>
          <a
            href="https://scholar.google.com/"
            target="_blank"
            rel="noreferrer"
            className="text-sm text-gray-200 hover:underline"
          >
            Scholar
          </a>
        </div>
      </div>
    </div>
  );
}
