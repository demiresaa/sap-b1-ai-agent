"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { UploadButton } from "@/components/documents/UploadButton";
import { Badge } from "@/components/ui/Badge";
import { Icon } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { Tabs } from "@/components/ui/Tabs";
import { fmt, formatBytes } from "@/lib/format";
import { useDocuments } from "@/lib/queries";
import { DocumentStatus, STATUS_LABEL } from "@/lib/types";

const STATUS_TONE: Record<DocumentStatus, "neutral" | "info" | "accent" | "warn" | "danger"> = {
  received: "neutral",
  reading: "info",
  matching: "info",
  ready: "accent",
  pdf_generated: "info",
  customer_accepted: "accent",
  customer_rejected: "danger",
  edited_after_acceptance: "warn",
  submitting: "info",
  submitted: "accent",
  converting_to_order: "info",
  order_submitted: "accent",
  error: "danger",
  rejected: "danger",
};

export default function QuotesPage() {
  const { data: allDocs = [], isLoading } = useDocuments();
  const docs = useMemo(() => allDocs.filter((d) => d.kind === "quotation"), [allDocs]);
  const [tab, setTab] = useState("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    let rows = [...docs];
    if (tab !== "all") rows = rows.filter((d) => d.status === tab);
    if (query) {
      const q = query.toLowerCase();
      rows = rows.filter(
        (d) =>
          d.id.toLowerCase().includes(q) ||
          (d.original_filename?.toLowerCase().includes(q) ?? false) ||
          (d.source_email?.toLowerCase().includes(q) ?? false),
      );
    }
    return rows;
  }, [docs, tab, query]);

  const tabs = [
    { value: "all", label: "Tümü", count: docs.length },
    { value: "ready", label: "Hazır", count: docs.filter((d) => d.status === "ready").length },
    { value: "submitted", label: "Gönderildi", count: docs.filter((d) => d.status === "submitted").length },
    { value: "error", label: "Hata", count: docs.filter((d) => d.status === "error").length },
  ];

  return (
    <div className="flex-1 overflow-y-auto thin-scroll fade-in">
      <PageHeader
        eyebrow={<Breadcrumb items={[{ label: "Operasyon" }, { label: "Teklifler" }]} />}
        title="Teklifler"
        subtitle="AI tarafından işlenen tüm teklif belgeleri."
        actions={<UploadButton />}
      />

      <div className="px-6 py-5 space-y-4">
        <div className="bg-surface border border-ink-200 rounded-lg shadow-card">
          <div className="flex items-center gap-3 px-3 py-2.5 hair-b flex-wrap">
            <Tabs tabs={tabs} value={tab} onChange={setTab} className="border-none h-auto" />
            <div className="flex-1" />
            <Input
              icon={<Icon.search size={14} />}
              placeholder="Ara…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-[220px]"
            />
            <span className="text-[11.5px] text-ink-500 num">{filtered.length} kayıt</span>
          </div>

          <table className="w-full text-[13px]">
            <thead className="bg-ink-50 text-ink-500 text-[11.5px] uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Dosya / Konu</th>
                <th className="text-left px-2 py-2.5 font-medium">Kaynak</th>
                <th className="text-left px-2 py-2.5 font-medium">Durum</th>
                <th className="text-left px-2 py-2.5 font-medium">Tarih</th>
                <th className="text-right px-4 py-2.5 font-medium">Boyut</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-[13px] text-ink-500">
                    Yükleniyor…
                  </td>
                </tr>
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-[13px] text-ink-500">
                    {docs.length === 0 ? "Henüz teklif belgesi yok." : "Eşleşen kayıt bulunamadı."}
                  </td>
                </tr>
              )}
              {filtered.map((doc) => (
                <tr key={doc.id} className="hair-t group hover:bg-ink-50/60 transition-colors">
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/documents/${doc.id}`}
                      className="text-ink-900 hover:text-accent font-medium truncate block max-w-[320px]"
                    >
                      {doc.original_filename || doc.source_subject || "(adsız)"}
                    </Link>
                  </td>
                  <td className="px-2 py-2.5 text-ink-500">
                    <span className="inline-flex items-center gap-1.5">
                      {doc.source === "email" ? (
                        <><Icon.mail size={12} /> <span className="truncate max-w-[140px]">{doc.source_email ?? "E-posta"}</span></>
                      ) : (
                        <><Icon.pdf size={12} /> PDF</>
                      )}
                    </span>
                  </td>
                  <td className="px-2 py-2.5">
                    <Badge tone={STATUS_TONE[doc.status]} dot size="sm">
                      {STATUS_LABEL[doc.status]}
                    </Badge>
                  </td>
                  <td className="px-2 py-2.5 text-ink-500 num text-[12px]">
                    {fmt.dateTime(doc.created_at)}
                  </td>
                  <td className="px-4 py-2.5 text-right text-ink-500 num text-[12px]">
                    {formatBytes(doc.file_size_bytes)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
