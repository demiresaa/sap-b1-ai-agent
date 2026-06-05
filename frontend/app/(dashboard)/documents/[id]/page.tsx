"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { DocumentForm } from "@/components/documents/DocumentForm";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { MessageStrip } from "@/components/ui/MessageStrip";
import { useToast } from "@/components/ui/Toast";
import { fmt } from "@/lib/format";
import { useDocument, useReprocessDocument } from "@/lib/queries";
import { STATUS_HINT, STATUS_LABEL } from "@/lib/types";

const STATUS_TONE = {
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
} as const;

const KIND_LABEL: Record<string, string> = {
  quotation: "Teklif",
  sales_order: "Satış Siparişi",
  unknown: "Bilinmiyor",
};

export default function DocumentDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const toast = useToast();
  const { data: doc, isLoading, isError, error } = useDocument(params.id);
  const reprocess = useReprocessDocument();

  async function runAi() {
    if (!doc) return;
    try {
      await reprocess.mutateAsync(doc.id);
      toast.push({
        icon: <Icon.sparkle size={16} />,
        duration: 3500,
        message: <span>AI başlatıldı. Durum kısa sürede güncellenecek.</span>,
      });
    } catch (err) {
      toast.push({
        icon: <Icon.warning size={16} />,
        duration: 5000,
        message: <span>AI tetiklenemedi: {(err as Error).message}</span>,
      });
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-[13px] text-ink-500">
        <Icon.flow size={18} className="animate-spin mr-2 text-accent" />
        Yükleniyor…
      </div>
    );
  }

  if (isError || !doc) {
    return (
      <div className="px-6 py-8 max-w-[640px]">
        <MessageStrip tone="danger" title="Doküman bulunamadı">
          {(error as Error)?.message ?? "Bu doküman mevcut değil veya erişim izniniz yok."}
        </MessageStrip>
        <Button variant="default" className="mt-4" icon={<Icon.chevL size={14} />} onClick={() => router.push("/pipeline")}>
          Pipeline&apos;a dön
        </Button>
      </div>
    );
  }

  const tone = STATUS_TONE[doc.status] ?? "neutral";
  const kindLabel = KIND_LABEL[doc.kind] ?? doc.kind;
  const docName = doc.original_filename ?? doc.source_email ?? doc.id;
  const confidence = doc.extracted?.confidence?.overall;

  return (
    <div className="flex-1 flex flex-col overflow-hidden fade-in">
      <PageHeader
        eyebrow={
          <Breadcrumb
            items={[
              { label: "Operasyon" },
              { label: "Pipeline", onClick: () => router.push("/pipeline") },
              { label: docName },
            ]}
          />
        }
        title={
          <span className="flex items-center gap-3 flex-wrap">
            <span>
              {kindLabel}{" "}
              <span className="num text-ink-600 text-[17px]">
                {doc.id.slice(0, 8)}…
              </span>
            </span>
            <Badge tone={tone} dot>
              {STATUS_LABEL[doc.status]}
            </Badge>
            <Badge tone="accent" size="sm">
              <Icon.sparkle size={10} className="mr-0.5" />
              AI tarafından oluşturuldu
            </Badge>
          </span>
        }
        subtitle={
          <span className="flex items-center gap-3 text-[13px] text-ink-500 flex-wrap">
            <span className="truncate max-w-[280px]">{docName}</span>
            <span className="text-ink-300">·</span>
            <span className="num">{fmt.dateTime(doc.created_at)}</span>
            {confidence != null && !isNaN(Number(confidence)) && (
              <>
                <span className="text-ink-300">·</span>
                <span>
                  Guven:{" "}
                  <span className={`num font-medium ${Number(confidence) >= 0.85 ? "text-accent" : Number(confidence) >= 0.6 ? "text-warn" : "text-danger"}`}>
                    {Math.round(Number(confidence) * 100)}%
                  </span>
                </span>
              </>
            )}
          </span>
        }
        actions={
          <>
            {doc.status === "received" ? (
              <Button
                variant="primary"
                icon={<Icon.sparkle size={14} />}
                loading={reprocess.isPending}
                onClick={runAi}
              >
                AI ile Teklif Hazırla
              </Button>
            ) : doc.status === "error" || doc.status === "rejected" ? (
              <Button
                variant="default"
                icon={<Icon.refresh size={14} />}
                loading={reprocess.isPending}
                onClick={runAi}
              >
                Tekrar Dene
              </Button>
            ) : (
              <Button
                variant="ghost"
                icon={<Icon.refresh size={14} />}
                loading={reprocess.isPending}
                onClick={runAi}
              >
                AI&apos;yı tekrar çalıştır
              </Button>
            )}
          </>
        }
      />

      <div className="px-6 pt-4">
        <MessageStrip
          tone={
            doc.status === "error" || doc.status === "rejected" || doc.status === "customer_rejected"
              ? "danger"
              : doc.status === "edited_after_acceptance"
                ? "warn"
                : doc.status === "submitted" || doc.status === "customer_accepted"
                  ? "accent"
                  : "info"
          }
          title={STATUS_LABEL[doc.status]}
        >
          {STATUS_HINT[doc.status]}
        </MessageStrip>
      </div>

      {doc.error_message && (
        <div className="px-6 pt-4">
          <MessageStrip tone="danger" title="İşlem hatası">
            {doc.error_message}
          </MessageStrip>
        </div>
      )}

      {/* DocumentForm — mevcut iş mantığını korur */}
      <div className="flex-1 overflow-y-auto thin-scroll px-6 py-5">
        <DocumentForm document={doc} />
      </div>
    </div>
  );
}
