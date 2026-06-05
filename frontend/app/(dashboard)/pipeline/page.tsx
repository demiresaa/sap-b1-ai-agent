"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { UploadButton } from "@/components/documents/UploadButton";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Checkbox";
import { Icon } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { Kpi } from "@/components/ui/Kpi";
import { Select } from "@/components/ui/Select";
import { Tabs, type TabItem } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/Toast";
import { fmt } from "@/lib/format";
import { useDeleteDocuments, useDocuments, useReprocessDocument } from "@/lib/queries";
import { DocumentSource, DocumentStatus, STATUS_LABEL } from "@/lib/types";
import { cn } from "@/lib/cn";

const STATUS_TONE: Record<DocumentStatus, Tone> = {
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

const SOURCE_ICON: Record<DocumentSource, React.ReactNode> = {
  email: <Icon.mail size={12} />,
  upload: <Icon.pdf size={12} />,
  api: <Icon.ext size={12} />,
};

const SOURCE_LABEL: Record<DocumentSource, string> = {
  email: "E-posta",
  upload: "PDF",
  api: "API",
};

const KIND_LABEL: Record<string, string> = {
  quotation: "Teklif",
  sales_order: "Sat. Sip.",
  unknown: "?",
};

const TABS: TabItem[] = [
  { value: "all", label: "Tümü" },
  { value: "reading", label: "İşleniyor" },
  { value: "ready", label: "Hazır" },
  { value: "submitted", label: "Gönderildi" },
  { value: "error", label: "Hata" },
];

export default function PipelinePage() {
  const qc = useQueryClient();
  const toast = useToast();
  const reprocess = useReprocessDocument();
  const deleteDocs = useDeleteDocuments();
  const { data: docs = [], isLoading } = useDocuments();

  async function handleDelete() {
    const ids = Array.from(selected);
    if (ids.length === 0) return;
    const confirmed = window.confirm(
      `${ids.length} belge kalıcı olarak silinecek. Devam edilsin mi?`,
    );
    if (!confirmed) return;
    try {
      const res = await deleteDocs.mutateAsync(ids);
      setSelected(new Set());
      toast.push({
        icon: res.failed > 0 ? <Icon.warning size={16} /> : <Icon.check2 size={16} />,
        duration: 4000,
        message: (
          <span>
            {res.failed > 0
              ? `${res.total - res.failed} silindi, ${res.failed} hata.`
              : `${res.total} belge silindi.`}
          </span>
        ),
      });
    } catch (err) {
      toast.push({
        icon: <Icon.warning size={16} />,
        duration: 5000,
        message: <span>Silme başarısız: {(err as Error).message}</span>,
      });
    }
  }
  const [filterTab, setFilterTab] = useState("all");
  const [filterSource, setFilterSource] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busyId, setBusyId] = useState<string | null>(null);

  async function triggerProcess(docId: string, fileName: string) {
    try {
      setBusyId(docId);
      await reprocess.mutateAsync(docId);
      toast.push({
        icon: <Icon.sparkle size={16} />,
        duration: 3500,
        message: (
          <span>
            <strong>{fileName}</strong> için AI başlatıldı. Durum kısa sürede güncellenecek.
          </span>
        ),
      });
      qc.invalidateQueries({ queryKey: ["documents"] });
    } catch (err) {
      toast.push({
        icon: <Icon.warning size={16} />,
        duration: 5000,
        message: <span>AI tetiklenemedi: {(err as Error).message}</span>,
      });
    } finally {
      setBusyId(null);
    }
  }

  const filtered = useMemo(() => {
    let rows = [...docs];
    if (filterTab !== "all") {
      if (filterTab === "ready") {
        rows = rows.filter((r) => r.status === "ready");
      } else if (filterTab === "reading") {
        rows = rows.filter((r) => r.status === "reading" || r.status === "matching");
      } else if (filterTab === "submitted") {
        rows = rows.filter((r) => r.status === "submitted" || r.status === "submitting");
      } else if (filterTab === "error") {
        rows = rows.filter((r) => r.status === "error" || r.status === "rejected");
      }
    }
    if (filterSource) rows = rows.filter((r) => r.source === filterSource);
    if (query) {
      const q = query.toLowerCase();
      rows = rows.filter(
        (r) =>
          r.id.toLowerCase().includes(q) ||
          (r.original_filename?.toLowerCase().includes(q) ?? false) ||
          (r.source_email?.toLowerCase().includes(q) ?? false),
      );
    }
    return rows;
  }, [docs, filterTab, filterSource, query]);

  const toggle = (id: string) => {
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const toggleAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map((r) => r.id)));
  };

  const tabsWithCount: TabItem[] = TABS.map((t) => ({
    ...t,
    count:
      t.value === "all"
        ? docs.length
        : t.value === "ready"
          ? docs.filter((d) => d.status === "ready").length
          : t.value === "reading"
            ? docs.filter((d) => d.status === "reading" || d.status === "matching").length
            : t.value === "submitted"
              ? docs.filter((d) => d.status === "submitted" || d.status === "submitting").length
              : docs.filter((d) => d.status === "error" || d.status === "rejected").length,
  }));

  return (
    <div className="flex-1 overflow-y-auto thin-scroll fade-in">
      <PageHeader
        eyebrow={
          <Breadcrumb items={[{ label: "Operasyon" }, { label: "Pipeline" }]} />
        }
        title="Pipeline"
        subtitle="Gelen dokümanlar ve ajan iş akışının canlı görünümü."
        actions={
          <>
            <Button
              icon={<Icon.refresh size={14} />}
              variant="ghost"
              onClick={() => qc.invalidateQueries({ queryKey: ["documents"] })}
            >
              Yenile
            </Button>
            <UploadButton />
          </>
        }
      />

      <div className="px-6 py-5 space-y-5">
        {/* KPI satırı */}
        <div className="grid grid-cols-4 gap-3">
          <Kpi
            label="Bekleyen"
            value={docs.filter((d) => d.status === "received").length}
            tone="ink"
            sub="Henüz işlenmedi"
            icon={<Icon.inbox size={14} />}
          />
          <Kpi
            label="İşleniyor"
            value={docs.filter((d) => d.status === "reading" || d.status === "matching").length}
            tone="info"
            sub="Aktif ajan var"
            icon={<Icon.flow size={14} />}
          />
          <Kpi
            label="Hazır"
            value={docs.filter((d) => d.status === "ready").length}
            tone="warn"
            sub="Operatör kontrolü"
            icon={<Icon.shield size={14} />}
          />
          <Kpi
            label="Bugün gönderildi"
            value={
              docs.filter(
                (d) =>
                  d.status === "submitted" &&
                  new Date(d.updated_at).toDateString() === new Date().toDateString(),
              ).length
            }
            tone="accent"
            sub="SAP'a yazıldı"
            icon={<Icon.check2 size={14} />}
          />
        </div>

        {/* Filtre şeridi */}
        <div className="bg-surface border border-ink-200 rounded-lg shadow-card">
          <Tabs tabs={tabsWithCount} value={filterTab} onChange={setFilterTab} className="px-3" />
          <div className="px-3 py-2.5 flex items-center gap-2 flex-wrap">
            <Input
              icon={<Icon.search size={14} />}
              placeholder="Doküman no veya dosya adı…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-[280px]"
            />
            <Select
              value={filterSource}
              onChange={setFilterSource}
              options={[
                { value: "email", label: "E-posta" },
                { value: "upload", label: "PDF" },
                { value: "api", label: "API" },
              ]}
              placeholder="Tüm kaynaklar"
              icon={<Icon.inbox size={13} />}
              className="w-[150px]"
            />
            <div className="flex-1" />
            {selected.size > 0 ? (
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-2 px-2.5 h-8 rounded-md bg-ink-900 text-white text-[12.5px]">
                  <span className="num">{selected.size}</span> seçili
                  <button
                    className="hover:text-accent-100 ml-2"
                    onClick={() => setSelected(new Set())}
                  >
                    Temizle
                  </button>
                </div>
                <Button
                  size="sm"
                  variant="danger"
                  icon={<Icon.trash size={13} />}
                  loading={deleteDocs.isPending}
                  onClick={handleDelete}
                >
                  Sil
                </Button>
              </div>
            ) : (
              <span className="text-[11.5px] text-ink-500 num">{filtered.length} kayıt</span>
            )}
          </div>
        </div>

        {/* Tablo */}
        <div className="bg-surface border border-ink-200 rounded-lg shadow-card overflow-hidden">
          <table className="w-full text-[13px]">
            <thead className="bg-ink-50 text-ink-500 text-[11.5px] uppercase tracking-wider">
              <tr>
                <th className="w-[40px] px-3 py-2.5">
                  <Checkbox
                    checked={filtered.length > 0 && selected.size === filtered.length}
                    onChange={toggleAll}
                  />
                </th>
                <th className="text-left px-2 py-2.5 font-medium">Doküman</th>
                <th className="text-left px-2 py-2.5 font-medium">Kaynak</th>
                <th className="text-left px-2 py-2.5 font-medium">Tip</th>
                <th className="text-left px-2 py-2.5 font-medium">Durum</th>
                <th className="text-left px-2 py-2.5 font-medium">Tarih</th>
                <th className="text-right px-2 py-2.5 font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-[13px] text-ink-500">
                    <Icon.flow size={20} className="mx-auto mb-2 animate-spin text-accent" />
                    Yükleniyor…
                  </td>
                </tr>
              )}
              {!isLoading &&
                filtered.map((row) => {
                  const isSel = selected.has(row.id);
                  const tone = STATUS_TONE[row.status];
                  const srcIcon = SOURCE_ICON[row.source];
                  const srcLabel = SOURCE_LABEL[row.source];
                  const kindLabel = KIND_LABEL[row.kind] ?? row.kind;
                  const docName = row.original_filename ?? row.source_email ?? row.id;
                  const isClickable =
                    row.status !== "received" &&
                    row.status !== "reading" &&
                    row.status !== "matching" &&
                    row.status !== "error" &&
                    row.status !== "rejected";

                  return (
                    <tr
                      key={row.id}
                      className={cn(
                        "group hair-t transition-colors",
                        isSel ? "bg-accent-50" : "hover:bg-ink-50/60",
                      )}
                    >
                      <td
                        className="px-3 py-2.5"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggle(row.id);
                        }}
                      >
                        <Checkbox checked={isSel} onChange={() => toggle(row.id)} />
                      </td>
                      <td className="px-2 py-2.5">
                        <div className="flex items-center gap-2">
                          <span
                            className="inline-flex items-center justify-center w-6 h-6 rounded-md bg-ink-100 text-ink-500"
                            title={srcLabel}
                          >
                            {srcIcon}
                          </span>
                          {isClickable ? (
                            <Link
                              href={`/documents/${row.id}`}
                              className="num text-[12.5px] font-medium text-ink-900 hover:text-accent truncate max-w-[180px]"
                              title={docName}
                            >
                              {docName}
                            </Link>
                          ) : (
                            <span
                              className="num text-[12.5px] font-medium text-ink-500 truncate max-w-[180px] cursor-default"
                              title={docName}
                            >
                              {docName}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-2 py-2.5 text-ink-700">{srcLabel}</td>
                      <td className="px-2 py-2.5 text-ink-700">{kindLabel}</td>
                      <td className="px-2 py-2.5">
                        <Badge tone={tone} dot size="sm">
                          {STATUS_LABEL[row.status]}
                        </Badge>
                      </td>
                      <td className="px-2 py-2.5 text-ink-500 num text-[12px]">
                        {fmt.dateTime(row.created_at)}
                      </td>
                      <td
                        className="px-2 py-2.5 text-right whitespace-nowrap"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {row.status === "received" && (
                          <Button
                            size="sm"
                            variant="primary"
                            loading={busyId === row.id}
                            icon={<Icon.sparkle size={13} />}
                            onClick={() =>
                              triggerProcess(row.id, docName)
                            }
                          >
                            AI ile Teklif Hazırla
                          </Button>
                        )}
                        {(row.status === "reading" || row.status === "matching") && (
                          <span className="inline-flex items-center gap-1.5 text-[12px] text-info">
                            <Icon.flow size={13} className="animate-spin" />
                            İşleniyor…
                          </span>
                        )}
                        {(row.status === "error" || row.status === "rejected") && (
                          <Button
                            size="sm"
                            variant="ghost"
                            loading={busyId === row.id}
                            icon={<Icon.refresh size={13} />}
                            onClick={() =>
                              triggerProcess(row.id, docName)
                            }
                          >
                            Tekrar Dene
                          </Button>
                        )}
                        {row.status !== "received" &&
                          row.status !== "reading" &&
                          row.status !== "matching" &&
                          row.status !== "error" &&
                          row.status !== "rejected" && (
                            <Link href={`/documents/${row.id}`}>
                              <Button size="sm" variant="ghost" icon={<Icon.chevR size={13} />}>
                                Detay
                              </Button>
                            </Link>
                          )}
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>

          {!isLoading && filtered.length === 0 && (
            <div className="px-6 py-16 text-center text-ink-500">
              <div className="mx-auto w-12 h-12 rounded-full bg-ink-100 inline-flex items-center justify-center mb-3">
                <Icon.inbox size={20} />
              </div>
              <div className="text-[14px] text-ink-700 font-medium">
                Eşleşen doküman bulunamadı
              </div>
              <div className="text-[12.5px] mt-1">Filtreleri sıfırlamayı deneyin.</div>
            </div>
          )}
        </div>

        <div className="text-[11.5px] text-ink-500 flex items-center gap-3 pt-1">
          {docs.some((d) => d.status === "reading" || d.status === "matching" || d.status === "submitting") ? (
            <span className="inline-flex items-center gap-1.5">
              <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-accent pulse-dot" />
              Aktif iş var — durum otomatik güncelleniyor
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 text-ink-400">
              Otomatik yenileme kapalı — sağ üstteki “Yenile” ile elle yenileyin
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
