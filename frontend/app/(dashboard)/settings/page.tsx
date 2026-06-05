"use client";

import { ReactNode, useState } from "react";

import { Breadcrumb } from "@/components/Breadcrumb";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, SectionTitle } from "@/components/ui/Card";
import { Icon } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { MessageStrip } from "@/components/ui/MessageStrip";
import { Switch } from "@/components/ui/Switch";
import { useCurrentUser } from "@/lib/queries";
import { cn } from "@/lib/cn";

type SectionId = "account" | "sap" | "thresholds" | "models" | "dryrun" | "audit";

interface NavItem {
  id: SectionId;
  label: string;
  icon: ReactNode;
}

const NAV: NavItem[] = [
  { id: "account", label: "Hesap", icon: <Icon.user size={14} /> },
  { id: "sap", label: "SAP Bağlantısı", icon: <Icon.database size={14} /> },
  { id: "thresholds", label: "Eşikler & kurallar", icon: <Icon.shield size={14} /> },
  { id: "models", label: "AI modelleri", icon: <Icon.cpu size={14} /> },
  { id: "dryrun", label: "Dry-Run & ortamlar", icon: <Icon.bolt size={14} /> },
  { id: "audit", label: "Denetim & log", icon: <Icon.doc size={14} /> },
];

export default function SettingsPage() {
  const [section, setSection] = useState<SectionId>("account");
  const [saved, setSaved] = useState(false);

  function save() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden fade-in">
      <PageHeader
        eyebrow={<Breadcrumb items={[{ label: "Yönetim" }, { label: "Ayarlar" }]} />}
        title="Ayarlar"
        subtitle="Sistem, AI ve operasyon parametrelerini yönetin."
        actions={
          <>
            <Button variant="ghost">Değişiklikleri at</Button>
            <Button
              variant="primary"
              icon={saved ? <Icon.check size={14} /> : <Icon.check size={14} />}
              onClick={save}
            >
              {saved ? "Kaydedildi" : "Tüm ayarları kaydet"}
            </Button>
          </>
        }
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Sol — ikincil nav */}
        <aside className="w-[240px] shrink-0 hair-r bg-paper p-3 overflow-y-auto thin-scroll">
          <div className="text-[11px] uppercase tracking-wider text-ink-500 px-2 mb-2 mt-1 font-medium">
            Konular
          </div>
          <nav className="space-y-0.5">
            {NAV.map((s) => {
              const active = section === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setSection(s.id)}
                  className={cn(
                    "w-full text-left flex items-center gap-2.5 h-8 px-2 rounded-md text-[13px] font-medium transition-colors",
                    active
                      ? "bg-surface text-ink-900 shadow-card border border-ink-200"
                      : "text-ink-700 hover:bg-ink-100",
                  )}
                >
                  <span className={active ? "text-accent" : "text-ink-500"}>{s.icon}</span>
                  <span>{s.label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Sağ — içerik */}
        <main className="flex-1 overflow-y-auto thin-scroll">
          <div className="max-w-[820px] mx-auto px-6 py-6 space-y-5">
            {section === "account" && <AccountSection />}
            {section === "sap" && <SapSection />}
            {section === "thresholds" && <ThresholdsSection />}
            {section === "models" && <ModelsSection />}
            {section === "dryrun" && <DryRunSection />}
            {section === "audit" && <AuditSection />}
          </div>
        </main>
      </div>
    </div>
  );
}

/* ---------- Hesap ---------- */
function AccountSection() {
  const { data: user } = useCurrentUser();
  return (
    <Card>
      <SectionTitle sub="Giriş yapan kullanıcı bilgileri">Hesap bilgisi</SectionTitle>
      <dl className="grid grid-cols-[160px_1fr] gap-x-4 gap-y-3 text-[13px]">
        <dt className="text-ink-500 font-medium">E-posta</dt>
        <dd className="text-ink-900">{user?.email ?? "—"}</dd>
        <dt className="text-ink-500 font-medium">Tam Ad</dt>
        <dd className="text-ink-900">{user?.full_name ?? "—"}</dd>
        <dt className="text-ink-500 font-medium">Roller</dt>
        <dd className="flex flex-wrap gap-1">
          {user?.roles?.map((r) => (
            <Badge key={r} tone="neutral" size="sm">{r}</Badge>
          )) ?? "—"}
        </dd>
        <dt className="text-ink-500 font-medium">Durum</dt>
        <dd>
          {user?.is_active ? (
            <Badge tone="accent" dot size="sm">Aktif</Badge>
          ) : (
            <Badge tone="danger" dot size="sm">Pasif</Badge>
          )}
        </dd>
      </dl>
    </Card>
  );
}

/* ---------- SAP Bağlantısı ---------- */
function SapSection() {
  return (
    <Card>
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-[15px] font-semibold text-ink-900">SAP Business One bağlantısı</h3>
          <p className="text-[12.5px] text-ink-500 mt-1">Service Layer endpoint ve kimlik bilgileri.</p>
        </div>
        <Badge tone="neutral" dot>Yapılandırılmadı</Badge>
      </div>
      <MessageStrip tone="info" title="Bağlantı bilgileri backend'de tutulur">
        SAP Service Layer URL, kullanıcı adı ve şifre `.env` dosyasında saklanır.
        Web üzerinden düzenleme Sprint 5&apos;te eklenecek.
      </MessageStrip>
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="block text-[11px] uppercase tracking-wider font-medium text-ink-500 mb-1">
            Service Layer URL
          </label>
          <Input
            disabled
            value="https://sap-b1.firma.local:50000/b1s/v1"
            inputClassName="num"
          />
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wider font-medium text-ink-500 mb-1">
            Veritabanı
          </label>
          <Input disabled value="FIRMA_PROD" inputClassName="num" />
        </div>
        <div>
          <label className="block text-[11px] uppercase tracking-wider font-medium text-ink-500 mb-1">
            Kullanıcı
          </label>
          <Input disabled value="manager" inputClassName="num" />
        </div>
      </div>
    </Card>
  );
}

/* ---------- Eşikler & Kurallar ---------- */
function ThresholdsSection() {
  const [autoApprove, setAutoApprove] = useState(true);
  const [threshold, setThreshold] = useState(85);

  return (
    <Card>
      <SectionTitle sub="Otomatik onay ve inceleme eşikleri">Eşikler & iş kuralları</SectionTitle>
      <div className="space-y-5">
        <Switch
          checked={autoApprove}
          onChange={setAutoApprove}
          label="Otomatik onay"
          sublabel="Eşik üstü güven skoru sahip belgeler direkt SAP'a gönderilir"
        />
        <div>
          <label className="block text-[12px] font-medium text-ink-700 mb-2">
            Güven eşiği: <span className="num text-accent font-semibold">{threshold}%</span>
          </label>
          <input
            type="range"
            min={50}
            max={99}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full accent-[#0E6F4E]"
          />
          <div className="flex justify-between text-[11px] text-ink-400 num mt-1">
            <span>50%</span>
            <span>99%</span>
          </div>
        </div>
        <div className="hair-t pt-4 text-[13px] text-ink-600 space-y-2">
          <div className="flex justify-between">
            <span>Maksimum otomatik iskonto</span>
            <span className="num font-medium text-ink-900">%15</span>
          </div>
          <div className="flex justify-between">
            <span>Otomatik onay tutar limiti</span>
            <span className="num font-medium text-ink-900">₺50.000</span>
          </div>
          <p className="text-[11.5px] text-ink-500 pt-1">
            Limit değerleri backend <code className="num">.env</code> üzerinden değiştirilir.
          </p>
        </div>
      </div>
    </Card>
  );
}

/* ---------- AI Modelleri ---------- */
function ModelsSection() {
  return (
    <Card>
      <SectionTitle sub="OpenRouter üzerinden model yapılandırması">AI modelleri</SectionTitle>
      <div className="space-y-3 text-[13px]">
        {[
          { key: "LLM_MODEL_DEFAULT", label: "Varsayılan (Sonnet)", value: "anthropic/claude-sonnet-4.5", tone: "accent" as const },
          { key: "LLM_MODEL_HARD", label: "Zor görevler (Opus)", value: "anthropic/claude-opus-4.1", tone: "warn" as const },
          { key: "LLM_MODEL_FAST", label: "Hızlı görevler (Haiku)", value: "anthropic/claude-haiku-4.5", tone: "info" as const },
        ].map((m) => (
          <div key={m.key} className="flex items-center justify-between p-3 bg-ink-50 rounded-md">
            <div>
              <div className="font-medium text-ink-900">{m.label}</div>
              <div className="num text-[12px] text-ink-500 mt-0.5">{m.key}</div>
            </div>
            <Badge tone={m.tone} size="sm">{m.value}</Badge>
          </div>
        ))}
        <MessageStrip tone="info">
          Model değiştirmek için <code className="num">.env</code> dosyasındaki
          <code className="num ml-1">LLM_MODEL_*</code> değerlerini düzenleyin.
        </MessageStrip>
      </div>
    </Card>
  );
}

/* ---------- Dry-Run ---------- */
function DryRunSection() {
  const [dryRun, setDryRun] = useState(true);
  return (
    <Card>
      <SectionTitle sub="SAP'a gerçek POST yapılıp yapılmadığını kontrol eder">Dry-Run modu</SectionTitle>
      <div className="space-y-4">
        <Switch
          checked={dryRun}
          onChange={setDryRun}
          label="Dry-Run aktif"
          sublabel="Aktifken tüm SAP POST'lar JSON önizlemesine yönlendirilir"
        />
        {dryRun && (
          <MessageStrip tone="warn" title="Dry-Run modu açık">
            Gerçek SAP POST'ları yapılmıyor. Danışman JSON&apos;ı test edip onaylayana kadar
            bu mod açık kalmalıdır.
          </MessageStrip>
        )}
        {!dryRun && (
          <MessageStrip tone="danger" title="Canlı mod — dikkatli olun!">
            SAP&apos;a gerçek POST yapılıyor. Oluşturulan siparişler/teklifler SAP&apos;ta görünecek.
          </MessageStrip>
        )}
      </div>
    </Card>
  );
}

/* ---------- Denetim ---------- */
function AuditSection() {
  return (
    <Card>
      <SectionTitle sub="Değiştirilemez sistem logları">Denetim & log</SectionTitle>
      <MessageStrip tone="info">
        Audit log kayıtları Postgres&apos;te append-only olarak tutulur. UI üzerinden log görüntüleme
        Faz 2&apos;de eklenecek.
      </MessageStrip>
    </Card>
  );
}
