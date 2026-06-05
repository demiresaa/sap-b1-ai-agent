"use client";

import { useRouter } from "next/navigation";

import { StatusBadge } from "@/components/ui/Badge";
import { formatBytes, formatDateTime } from "@/lib/format";
import { DocumentKind, DocumentSummary } from "@/lib/types";

interface Props {
  docs: DocumentSummary[];
  filterKind?: DocumentKind;
  emptyText?: string;
}

export function DocumentTable({ docs, filterKind, emptyText = "Kayıt yok." }: Props) {
  const router = useRouter();
  const filtered = filterKind ? docs.filter((d) => d.kind === filterKind) : docs;

  if (filtered.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-200 p-4 text-center text-xs text-slate-400">
        {emptyText}
      </div>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead className="bg-slate-100 text-left text-xs text-slate-600">
        <tr>
          <th className="px-3 py-2 font-medium">Dosya / Konu</th>
          <th className="px-3 py-2 font-medium">Kaynak</th>
          <th className="px-3 py-2 font-medium">Durum</th>
          <th className="px-3 py-2 font-medium">Tarih</th>
          <th className="px-3 py-2 font-medium text-right">Boyut</th>
        </tr>
      </thead>
      <tbody>
        {filtered.map((doc) => (
          <tr
            key={doc.id}
            onClick={() => router.push(`/documents/${doc.id}`)}
            className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
          >
            <td className="max-w-md truncate px-3 py-2 text-slate-800">
              {doc.original_filename || doc.source_subject || "(adsız)"}
            </td>
            <td className="px-3 py-2 text-xs text-slate-500">
              {doc.source === "email" ? `📧 ${doc.source_email ?? ""}` : "📄 Upload"}
            </td>
            <td className="px-3 py-2">
              <StatusBadge status={doc.status} />
            </td>
            <td className="px-3 py-2 text-xs text-slate-500">{formatDateTime(doc.created_at)}</td>
            <td className="px-3 py-2 text-right text-xs text-slate-500">
              {formatBytes(doc.file_size_bytes)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
