"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { Tabs } from "@/components/ui/Tabs";
import { fmt } from "@/lib/format";
import { useConvertToOrder, useOrderCandidates } from "@/lib/queries";
import type { OrderCandidateOut } from "@/lib/types";

type TabValue = "all" | "candidates" | "converted";

export default function OrdersPage() {
  const [tab, setTab] = useState<TabValue>("all");
  const [query, setQuery] = useState("");
  const [converting, setConverting] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  const { data: rows = [], isLoading } = useOrderCandidates(tab);
  const convertMutation = useConvertToOrder();

  const filtered = useMemo(() => {
    if (!query) return rows;
    const q = query.toLowerCase();
    return rows.filter(
      (r) =>
        (r.card_name?.toLowerCase().includes(q) ?? false) ||
        (r.card_code?.toLowerCase().includes(q) ?? false) ||
        (r.original_filename?.toLowerCase().includes(q) ?? false) ||
        String(r.quotation_doc_num ?? "").includes(q) ||
        String(r.order_doc_num ?? "").includes(q),
    );
  }, [rows, query]);

  const tabs: { value: TabValue; label: string; count: number }[] = [
    { value: "all", label: "Tümü", count: rows.length },
    {
      value: "candidates",
      label: "Aday Siparişler",
      count: rows.filter((r) => r.status === "candidate").length,
    },
    {
      value: "converted",
      label: "Kesinleşmiş",
      count: rows.filter((r) => r.status === "converted").length,
    },
  ];

  async function handleConvert(order: OrderCandidateOut) {
    setConverting(order.document_id);
    setToast(null);
    try {
      const res = await convertMutation.mutateAsync(order.document_id);
      setToast({
        msg: res.dry_run
          ? `[Dry-run] Simüle sipariş #${res.order_doc_num ?? res.order_doc_entry}`
          : `Sipariş oluşturuldu — SAP No: ${res.order_doc_num ?? res.order_doc_entry}`,
        ok: true,
      });
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Sipariş oluşturulamadı.";
      setToast({ msg, ok: false });
    } finally {
      setConverting(null);
    }
  }

  return (
    <div className="flex-1 overflow-y-auto thin-scroll fade-in">
      <PageHeader
        eyebrow={<Breadcrumb items={[{ label: "Operasyon" }, { label: "Siparişler" }]} />}
        title="Siparişler"
        subtitle="Müşteri onaylı teklifler — aday ve kesinleşmiş SAP siparişleri."
      />

      {toast && (
        <div
          className={`mx-6 mt-4 px-4 py-2.5 rounded-lg text-[13px] flex items-center gap-2 ${
            toast.ok
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {toast.ok ? <Icon.check size={14} /> : <Icon.warning size={14} />}
          {toast.msg}
          <button
            onClick={() => setToast(null)}
            className="ml-auto text-inherit opacity-60 hover:opacity-100"
          >
            <Icon.cross size={12} />
          </button>
        </div>
      )}

      <div className="px-6 py-5 space-y-4">
        <div className="bg-surface border border-ink-200 rounded-lg shadow-card">
          <div className="flex items-center gap-3 px-3 py-2.5 hair-b flex-wrap">
            <Tabs
              tabs={tabs}
              value={tab}
              onChange={(v) => setTab(v as TabValue)}
              className="border-none h-auto"
            />
            <div className="flex-1" />
            <Input
              icon={<Icon.search size={14} />}
              placeholder="Müşteri, dosya, teklif no…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-[240px]"
            />
            <span className="text-[11.5px] text-ink-500 num">{filtered.length} kayıt</span>
          </div>

          <table className="w-full text-[13px]">
            <thead className="bg-ink-50 text-ink-500 text-[11.5px] uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Müşteri</th>
                <th className="text-left px-2 py-2.5 font-medium">Para / Tutar</th>
                <th className="text-left px-2 py-2.5 font-medium">Teklif No</th>
                <th className="text-left px-2 py-2.5 font-medium">Sipariş No</th>
                <th className="text-left px-2 py-2.5 font-medium">Durum</th>
                <th className="text-left px-2 py-2.5 font-medium">Tarih</th>
                <th className="text-right px-4 py-2.5 font-medium">İşlem</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-[13px] text-ink-500">
                    Yükleniyor…
                  </td>
                </tr>
              )}
              {!isLoading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-10 text-center text-[13px] text-ink-500">
                    {rows.length === 0
                      ? "Henüz aday sipariş yok. Teklifler müşteri tarafından onaylandığında burada görünür."
                      : "Eşleşen kayıt bulunamadı."}
                  </td>
                </tr>
              )}
              {filtered.map((order) => (
                <tr
                  key={order.document_id}
                  className="hair-t group hover:bg-ink-50/60 transition-colors"
                >
                  {/* Müşteri */}
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/documents/${order.document_id}`}
                      className="text-ink-900 hover:text-accent font-medium block"
                    >
                      {order.card_name || order.card_code || "(bilinmiyor)"}
                    </Link>
                    {order.card_code && (
                      <span className="text-[11px] text-ink-400 num">{order.card_code}</span>
                    )}
                  </td>

                  {/* Para / Tutar */}
                  <td className="px-2 py-2.5 num text-ink-700">
                    {order.doc_currency && (
                      <span className="text-[11px] text-ink-400 mr-1">{order.doc_currency}</span>
                    )}
                    {order.doc_total != null ? order.doc_total.toLocaleString("tr-TR", { maximumFractionDigits: 2 }) : "—"}
                  </td>

                  {/* Teklif No */}
                  <td className="px-2 py-2.5 num text-ink-600 text-[12px]">
                    {order.quotation_doc_num ?? "—"}
                  </td>

                  {/* Sipariş No */}
                  <td className="px-2 py-2.5 num text-ink-600 text-[12px]">
                    {order.order_doc_num ?? (
                      <span className="text-ink-400">—</span>
                    )}
                  </td>

                  {/* Durum */}
                  <td className="px-2 py-2.5">
                    {order.status === "converted" ? (
                      <Badge tone="accent" dot size="sm">Kesinleşti</Badge>
                    ) : (
                      <Badge tone="warn" dot size="sm">Aday Sipariş</Badge>
                    )}
                  </td>

                  {/* Tarih */}
                  <td className="px-2 py-2.5 text-ink-500 num text-[12px]">
                    {order.converted_at
                      ? fmt.dateTime(order.converted_at)
                      : fmt.dateTime(order.created_at)}
                  </td>

                  {/* İşlem */}
                  <td className="px-4 py-2.5 text-right">
                    {order.status === "candidate" ? (
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={converting === order.document_id}
                        onClick={() => handleConvert(order)}
                      >
                        {converting === order.document_id ? (
                          <><Icon.refresh size={13} className="animate-spin" /> Oluşturuluyor…</>
                        ) : (
                          <><Icon.check size={13} /> Siparişe Dönüştür</>
                        )}
                      </Button>
                    ) : (
                      <Link
                        href={`/documents/${order.document_id}`}
                        className="text-[12px] text-ink-500 hover:text-accent"
                      >
                        Detay →
                      </Link>
                    )}
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
