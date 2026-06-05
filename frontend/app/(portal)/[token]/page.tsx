"use client";

import { useState } from "react";

import { Logo } from "@/components/Logo";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Icon } from "@/components/ui/icons";
import { MessageStrip } from "@/components/ui/MessageStrip";

export default function PortalPage({ params }: { params: { token: string } }) {
  const [decided, setDecided] = useState<"accept" | "fix" | null>(null);
  const [showFix, setShowFix] = useState(false);
  const [note, setNote] = useState("");

  if (decided) {
    return (
      <div className="min-h-screen bg-paper flex items-center justify-center p-6">
        <div className="bg-surface rounded-xl border border-ink-200 shadow-card max-w-[520px] w-full p-10 text-center fade-in">
          <div
            className={`mx-auto w-16 h-16 rounded-full inline-flex items-center justify-center mb-5 ${
              decided === "accept" ? "bg-accent text-white" : "bg-warn text-white"
            }`}
          >
            {decided === "accept" ? (
              <Icon.check size={28} stroke={2.4} />
            ) : (
              <Icon.edit size={24} />
            )}
          </div>
          <h1 className="text-[22px] font-semibold tracking-tightish text-ink-900">
            {decided === "accept" ? "Teklifi kabul ettiniz" : "Düzeltme talebiniz iletildi"}
          </h1>
          <p className="text-[13.5px] text-ink-600 mt-2 max-w-[380px] mx-auto leading-relaxed">
            {decided === "accept"
              ? "Teklif onayınız ekibimize iletildi. Sipariş hazırlandığında bilgilendirileceksiniz."
              : "Mesajınız satış ekibimize ulaştı. En kısa sürede güncellenmiş bir teklifle dönüş yapacağız."}
          </p>
          <div className="mt-6 inline-flex items-center gap-2 px-3 py-2 rounded-md bg-ink-50 text-[12px] text-ink-600">
            <Icon.mail size={13} /> Onay e-postası gönderildi
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper">
      {/* Top bar */}
      <header className="bg-surface hair-b">
        <div className="max-w-[920px] mx-auto px-6 h-[56px] flex items-center gap-4">
          <Logo size={26} />
          <div className="h-5 w-px bg-ink-200" />
          <div className="flex-1">
            <div className="text-[11px] uppercase tracking-wider text-ink-500 font-medium">Teklif</div>
            <div className="num text-[13.5px] font-medium text-ink-900 -mt-0.5">
              {params.token.slice(0, 16)}…
            </div>
          </div>
        </div>
      </header>

      {/* Hero / özet */}
      <div className="bg-surface hair-b">
        <div className="max-w-[920px] mx-auto px-6 py-8">
          <MessageStrip tone="info" title="Faz 2'de aktif olacak">
            Müşteri portalı Faz 2&apos;de tam olarak aktif edilecek. Token:{" "}
            <span className="num font-medium">{params.token}</span>
          </MessageStrip>

          <div className="mt-6 flex items-start justify-between gap-6 flex-wrap">
            <div>
              <div className="inline-flex items-center gap-2 text-[11.5px] uppercase tracking-wider text-accent font-medium mb-2">
                <Icon.sparkle size={12} /> Yeni teklif
              </div>
              <h1 className="text-[32px] leading-tight font-semibold tracking-tightish text-ink-900">
                Teklifiniz hazır.
              </h1>
              <p className="text-[13.5px] text-ink-600 mt-3 max-w-[480px] leading-relaxed">
                Aşağıdaki teklifi inceleyebilir, onaylayabilir veya düzeltme talep edebilirsiniz.
              </p>
            </div>
            <div className="bg-ink-900 text-white rounded-xl p-5 min-w-[220px]">
              <div className="text-[11.5px] uppercase tracking-wider text-ink-400">Durum</div>
              <Badge tone="warn" dot className="mt-2">Teklif onay bekliyor</Badge>
              <div className="hair-t border-white/10 mt-3 pt-3 text-[12px] text-ink-300 space-y-1">
                <div className="flex justify-between">
                  <span>Geçerlilik</span>
                  <span className="text-white num">30 gün</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Karar alanı */}
      <div className="max-w-[920px] mx-auto px-6 py-6 space-y-5">
        {!showFix ? (
          <div className="bg-surface rounded-xl border border-ink-200 shadow-card p-5">
            <div className="flex items-center gap-4 flex-wrap">
              <div className="flex-1">
                <div className="text-[14px] font-semibold text-ink-900">Karar verme zamanı</div>
                <div className="text-[12.5px] text-ink-500 mt-0.5">
                  Teklifi kabul edebilir veya satış ekibimizden düzeltme talep edebilirsiniz.
                </div>
              </div>
              <Button
                variant="default"
                icon={<Icon.edit size={14} />}
                onClick={() => setShowFix(true)}
              >
                Düzeltme istiyorum
              </Button>
              <Button
                variant="primary"
                size="lg"
                icon={<Icon.check size={16} />}
                onClick={() => setDecided("accept")}
              >
                Teklifi kabul et
              </Button>
            </div>
          </div>
        ) : (
          <div className="bg-surface rounded-xl border border-accent shadow-card p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="text-[14px] font-semibold text-ink-900">Düzeltme talebi</div>
                <div className="text-[12.5px] text-ink-500 mt-0.5">
                  Hangi konuda revizyon istediğinizi açıklayın.
                </div>
              </div>
              <button onClick={() => setShowFix(false)} className="text-ink-500 hover:text-ink-900">
                <Icon.cross size={16} />
              </button>
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Örn: Miktarı güncelleyebilir misiniz?"
              className="w-full h-24 border border-ink-200 rounded-md px-3 py-2 text-[13px] focus:outline-none focus:border-accent focus:shadow-[0_0_0_3px_rgba(14,111,78,0.12)] resize-none"
            />
            <div className="flex items-center justify-between mt-3">
              <div className="text-[11.5px] text-ink-500">
                Satış ekibimiz 2 iş günü içinde dönüş yapacaktır.
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" onClick={() => setShowFix(false)}>İptal</Button>
                <Button
                  variant="primary"
                  icon={<Icon.check size={14} />}
                  disabled={!note.trim()}
                  onClick={() => setDecided("fix")}
                >
                  Gönder
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Güven şeridi */}
        <div className="grid grid-cols-3 gap-3 pt-2">
          {[
            { i: <Icon.lock size={14} />, t: "Güvenli bağlantı", s: "Bu link size özel ve şifrelenmiştir" },
            { i: <Icon.shield size={14} />, t: "Yasal geçerlilik", s: "Onayınız elektronik imza yerine geçer" },
            { i: <Icon.mail size={14} />, t: "Destek", s: "Sorularınız için satış ekibimize yazın" },
          ].map((x) => (
            <div key={x.t} className="flex items-start gap-2.5 text-[12px]">
              <span className="w-7 h-7 rounded-md bg-ink-100 text-ink-700 inline-flex items-center justify-center shrink-0">
                {x.i}
              </span>
              <div>
                <div className="text-ink-900 font-medium">{x.t}</div>
                <div className="text-ink-500">{x.s}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <footer className="max-w-[920px] mx-auto px-6 py-6 hair-t mt-4 flex items-center justify-between text-[11.5px] text-ink-500">
        <div>© 2026 Firma A.Ş. · Tüm hakları saklıdır.</div>
        <div className="num">v3.1.4</div>
      </footer>
    </div>
  );
}
