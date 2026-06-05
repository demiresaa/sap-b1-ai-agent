"use client";

import { FileText, Mail } from "lucide-react";
import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/ui/Badge";
import { formatBytes, formatDateTime } from "@/lib/format";
import { DocumentSummary } from "@/lib/types";

export function DocumentCard({ doc }: { doc: DocumentSummary }) {
  const router = useRouter();
  const Icon = doc.source === "email" ? Mail : FileText;
  return (
    <button
      onClick={() => router.push(`/documents/${doc.id}`)}
      className="w-full rounded-md border border-slate-200 bg-white p-2.5 text-left text-xs shadow-sm transition hover:border-blue-300 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-1.5">
          <Icon className="h-3.5 w-3.5 shrink-0 text-slate-400" />
          <span className="truncate font-medium text-slate-700">
            {doc.original_filename || doc.source_subject || "(adsız)"}
          </span>
        </div>
        <StatusBadge status={doc.status} />
      </div>
      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
        <span>{formatDateTime(doc.created_at)}</span>
        <span>{formatBytes(doc.file_size_bytes)}</span>
      </div>
      {doc.error_message && (
        <div className="mt-2 truncate rounded bg-red-50 px-1.5 py-1 text-[10px] text-red-700">
          {doc.error_message}
        </div>
      )}
    </button>
  );
}
