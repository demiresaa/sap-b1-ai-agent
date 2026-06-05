"use client";

import { Download, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ConfidenceBadge } from "@/components/ui/Badge";
import { FieldLabel, FieldState, Input } from "@/components/ui/Input";
import { CustomerPicker } from "@/components/documents/CustomerPicker";
import { ItemPicker } from "@/components/documents/ItemPicker";
import { formatCurrency } from "@/lib/format";
import {
  useCustomerAccepted,
  useCustomerRejected,
  useDownloadQuotationPdf,
  useGenerateQuotationPdf,
  useUpdateExtractedData,
} from "@/lib/queries";
import { BusinessPartner, DocumentDetail, ExtractedDocument, ExtractedLine } from "@/lib/types";

interface Props {
  document: DocumentDetail;
}

const CONFIDENCE_THRESHOLD = 0.85;

export function DocumentForm({ document }: Props) {
  const initial = useMemo(
    () =>
      document.extracted?.payload ??
      ({
        customer: {},
        lines: [],
      } as ExtractedDocument),
    [document.extracted],
  );

  const [payload, setPayload] = useState<ExtractedDocument>(initial);
  const [dirty, setDirty] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [selectedBp, setSelectedBp] = useState<BusinessPartner | null>(null);

  const update = useUpdateExtractedData();
  const generatePdf = useGenerateQuotationPdf();
  const downloadPdf = useDownloadQuotationPdf();
  const accept = useCustomerAccepted();
  const reject = useCustomerRejected();

  function patch(partial: Partial<ExtractedDocument>) {
    setPayload((prev) => ({ ...prev, ...partial }));
    setDirty(true);
    setSavedMessage(null);
  }

  function patchLine(lineNo: number, partial: Partial<ExtractedLine>) {
    setPayload((prev) => ({
      ...prev,
      lines: prev.lines.map((l) => (l.line_no === lineNo ? { ...l, ...partial } : l)),
    }));
    setDirty(true);
    setSavedMessage(null);
  }

  function addLine() {
    const nextNo = (payload.lines[payload.lines.length - 1]?.line_no ?? 0) + 1;
    patch({
      lines: [
        ...payload.lines,
        {
          line_no: nextNo,
          description: "",
          quantity: 1,
          unit_price: 0,
        },
      ],
    });
  }

  function removeLine(lineNo: number) {
    patch({ lines: payload.lines.filter((l) => l.line_no !== lineNo) });
  }

  async function save() {
    await update.mutateAsync({ documentId: document.id, payload });
    setDirty(false);
    setSavedMessage("Kaydedildi");
  }

  function downloadJson() {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = window.document.createElement("a");
    a.href = url;
    a.download = `dokuman-${document.id.slice(0, 8)}.json`;
    window.document.body.appendChild(a);
    a.click();
    window.document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function onGeneratePdf() {
    if (dirty) await save();
    await generatePdf.mutateAsync(document.id);
    await downloadPdf.mutateAsync(document.id);
  }

  async function onDownloadPdf() {
    await downloadPdf.mutateAsync(document.id);
  }

  async function onCustomerAccepted() {
    await accept.mutateAsync(document.id);
  }

  async function onCustomerRejected() {
    await reject.mutateAsync({ documentId: document.id });
  }

  const confidence = document.extracted?.confidence ?? null;
  const total = payload.lines.reduce(
    (sum, l) => sum + (l.unit_price ?? 0) * (l.quantity ?? 0),
    0,
  );

  const customerState: FieldState = payload.customer.card_code ? "filled" : "empty";

  // Dry-run modunda SAP combobox'tan seçim olmadan da payload üretilebilir
  const hasLines = payload.lines.length > 0;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Belge Bilgileri</h3>
          <ConfidenceBadge score={confidence?.overall as number | undefined} />
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="space-y-1 md:col-span-2">
            <FieldLabel hint="AI önerisini onaylayın ya da değiştirin">Müşteri (BP)</FieldLabel>
            <CustomerPicker
              customer={payload.customer}
              onChange={(c, bp) => {
                // Para birimi müşteriden otomatik gelsin (eğer henüz girilmemişse)
                const newPayload: Partial<ExtractedDocument> = { customer: c };
                if (bp?.Currency && !payload.currency) {
                  newPayload.currency = bp.Currency;
                }
                patch(newPayload);
                setSelectedBp(bp ?? null);
              }}
              fieldState={customerState}
            />

            {/* Seçili müşteri bilgi kartı — SAP'tan gelen tüm alanlar */}
            {payload.customer.card_code && (
              <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5 text-[11.5px] space-y-2">
                {/* Kimlik */}
                <div className="grid grid-cols-2 gap-x-6 gap-y-0.5">
                  <BpField label="Müşteri Kodu" value={payload.customer.card_code} mono />
                  <BpField label="Vergi No" value={payload.customer.tax_id} />
                  <BpField label="Para Birimi" value={payload.customer.currency} bold />
                  <BpField label="KDV Grubu" value={payload.customer.vat_group} />
                  <BpField label="Fiyat Listesi" value={payload.customer.price_list_num != null ? `#${payload.customer.price_list_num}` : null} />
                  <BpField label="Ödeme Koşulları" value={payload.customer.payment_terms_code != null ? `#${payload.customer.payment_terms_code}` : null} />
                  {payload.customer.discount_pct != null && payload.customer.discount_pct > 0 && (
                    <BpField label="Varsayılan İskonto" value={`%${payload.customer.discount_pct}`} bold />
                  )}
                  {payload.customer.credit_limit != null && payload.customer.credit_limit > 0 && (
                    <BpField label="Kredi Limiti" value={`${payload.customer.credit_limit?.toLocaleString("tr-TR")} ${payload.customer.currency ?? ""}`} />
                  )}
                </div>
                {/* İletişim */}
                {(payload.customer.email || payload.customer.phone || payload.customer.phone2 || payload.customer.cellular || payload.customer.website) && (
                  <div className="border-t border-slate-200 pt-1.5 grid grid-cols-2 gap-x-6 gap-y-0.5">
                    <BpField label="E-posta" value={payload.customer.email} />
                    <BpField label="Telefon" value={payload.customer.phone} />
                    <BpField label="Tel 2" value={payload.customer.phone2} />
                    <BpField label="Cep" value={payload.customer.cellular} />
                    <BpField label="Website" value={payload.customer.website} />
                  </div>
                )}
                {/* Adres */}
                {(payload.customer.address || payload.customer.city || payload.customer.country) && (
                  <div className="border-t border-slate-200 pt-1.5 grid grid-cols-2 gap-x-6 gap-y-0.5">
                    <BpField label="Adres" value={payload.customer.address} />
                    <BpField label="Şehir" value={[payload.customer.city, payload.customer.zip_code].filter(Boolean).join(" ")} />
                    <BpField label="Ülke" value={payload.customer.country} />
                  </div>
                )}
                {/* Bakiyeler */}
                {(payload.customer.balance != null || payload.customer.orders_balance != null) && (
                  <div className="border-t border-slate-200 pt-1.5 grid grid-cols-2 gap-x-6 gap-y-0.5">
                    <BpField label="Cari Bakiye" value={payload.customer.balance != null ? payload.customer.balance.toLocaleString("tr-TR") : null} />
                    <BpField label="Açık Sipariş" value={payload.customer.orders_balance != null ? payload.customer.orders_balance.toLocaleString("tr-TR") : null} />
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="space-y-1">
            <FieldLabel>Belge Tarihi</FieldLabel>
            <Input
              type="date"
              fieldState={payload.doc_date ? "filled" : "empty"}
              value={payload.doc_date ?? ""}
              onChange={(e) => patch({ doc_date: e.target.value || null })}
            />
          </div>

          <div className="space-y-1">
            <FieldLabel>Vade / Teslim Tarihi</FieldLabel>
            <Input
              type="date"
              fieldState={payload.due_date ? "filled" : "empty"}
              value={payload.due_date ?? ""}
              onChange={(e) => patch({ due_date: e.target.value || null })}
            />
          </div>

          <div className="space-y-1">
            <FieldLabel>Para Birimi</FieldLabel>
            <Input
              fieldState={payload.currency ? "filled" : "empty"}
              value={payload.currency ?? ""}
              onChange={(e) => patch({ currency: e.target.value.toUpperCase() || null })}
              placeholder="TRY / EUR / USD"
            />
          </div>

          <div className="space-y-1">
            <FieldLabel>Müşteri Referans No</FieldLabel>
            <Input
              fieldState={payload.reference_no ? "filled" : "empty"}
              value={payload.reference_no ?? ""}
              onChange={(e) => patch({ reference_no: e.target.value || null })}
              placeholder="NumAtCard"
            />
          </div>
        </div>
      </div>

      <div className="rounded-lg border bg-white p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Satırlar ({payload.lines.length})</h3>
          <Button variant="secondary" size="sm" onClick={addLine}>
            <Plus className="h-3.5 w-3.5" />
            Satır Ekle
          </Button>
        </div>

        <div className="space-y-2">
          {payload.lines.length === 0 && (
            <p className="rounded-md border border-dashed border-slate-200 p-3 text-center text-xs text-slate-400">
              Satır yok — "Satır Ekle" ile manuel başlayın
            </p>
          )}
          {payload.lines.map((line) => {
            const itemState: FieldState = line.item_code ? "filled" : "uncertain";
            return (
              <div
                key={line.line_no}
                className="grid grid-cols-12 gap-2 rounded-md border border-slate-200 bg-slate-50 p-2"
              >
                <div className="col-span-12 md:col-span-6">
                  <FieldLabel>Ürün</FieldLabel>
                  <ItemPicker
                    itemCode={line.item_code ?? null}
                    itemName={line.item_name ?? null}
                    fallbackDescription={line.description}
                    fieldState={itemState}
                    onChange={(item) =>
                      patchLine(line.line_no, {
                        item_code: item?.code ?? null,
                        item_name: item?.name ?? null,
                      })
                    }
                  />
                  {line.description && line.description !== line.item_name && (
                    <p className="mt-1 text-[10px] text-slate-500">PDF: "{line.description}"</p>
                  )}
                </div>
                <div className="col-span-3 md:col-span-2">
                  <FieldLabel>Miktar</FieldLabel>
                  <Input
                    type="number"
                    step="any"
                    fieldState="filled"
                    value={line.quantity}
                    onChange={(e) => patchLine(line.line_no, { quantity: Number(e.target.value) })}
                  />
                </div>
                <div className="col-span-4 md:col-span-2">
                  <FieldLabel>Birim Fiyat</FieldLabel>
                  <Input
                    type="number"
                    step="any"
                    fieldState={line.unit_price != null ? "filled" : "empty"}
                    value={line.unit_price ?? ""}
                    onChange={(e) =>
                      patchLine(line.line_no, {
                        unit_price: e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="col-span-4 md:col-span-1">
                  <FieldLabel>İsk %</FieldLabel>
                  <Input
                    type="number"
                    step="any"
                    fieldState={line.discount_pct ? "uncertain" : "empty"}
                    value={line.discount_pct ?? ""}
                    onChange={(e) =>
                      patchLine(line.line_no, {
                        discount_pct: e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="col-span-1 flex items-end justify-end">
                  <button
                    type="button"
                    onClick={() => removeLine(line.line_no)}
                    className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600"
                    aria-label="Satırı sil"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-3 flex items-center justify-end gap-2 border-t pt-3 text-sm">
          <span className="text-slate-500">Toplam</span>
          <span className="font-semibold">{formatCurrency(total, payload.currency ?? "TRY")}</span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 rounded-lg border bg-white p-3">
        <div className="text-xs">
          {savedMessage && <span className="text-emerald-600">✓ {savedMessage}</span>}
          {!hasLines && (
            <span className="text-amber-700">JSON indirmek için en az 1 satir olmali.</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={save} loading={update.isPending} disabled={!dirty}>
            Kaydet
          </Button>
          <Button
            variant="secondary"
            onClick={onGeneratePdf}
            loading={generatePdf.isPending || downloadPdf.isPending}
            disabled={!hasLines}
          >
            PDF Teklif Üret & İndir
          </Button>
          {(document.status === "pdf_generated" ||
            document.status === "customer_accepted" ||
            document.status === "edited_after_acceptance") && (
            <Button variant="secondary" onClick={onDownloadPdf} loading={downloadPdf.isPending}>
              PDF'i Yeniden İndir
            </Button>
          )}
          {document.status === "pdf_generated" && (
            <>
              <Button variant="secondary" onClick={onCustomerAccepted} loading={accept.isPending}>
                Müşteri Kabul Etti
              </Button>
              <Button variant="danger" onClick={onCustomerRejected} loading={reject.isPending}>
                Müşteri Reddetti
              </Button>
            </>
          )}
          <Button variant="secondary" onClick={downloadJson} disabled={!hasLines}>
            <Download className="h-4 w-4" />
            JSON Indir
          </Button>
        </div>
      </div>
    </div>
  );
}

function BpField({
  label,
  value,
  mono,
  bold,
}: {
  label: string;
  value: string | number | null | undefined;
  mono?: boolean;
  bold?: boolean;
}) {
  if (value == null || value === "") return null;
  return (
    <span className="text-slate-500 truncate">
      {label}:{" "}
      <span className={`text-slate-800 ${mono ? "font-mono" : ""} ${bold ? "font-semibold" : ""}`}>
        {value}
      </span>
    </span>
  );
}

export function fieldStateFromConfidence(
  confidence: Record<string, number> | null | undefined,
  key: string,
  hasValue: boolean,
): FieldState {
  if (!hasValue) return "empty";
  const score = confidence?.[key];
  if (score == null) return "filled";
  return score >= CONFIDENCE_THRESHOLD ? "filled" : "uncertain";
}
