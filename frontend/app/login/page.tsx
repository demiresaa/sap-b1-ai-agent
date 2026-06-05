"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/Button";
import { Checkbox } from "@/components/ui/Checkbox";
import { Icon } from "@/components/ui/icons";
import { Input } from "@/components/ui/Input";
import { MessageStrip } from "@/components/ui/MessageStrip";
import { useLogin } from "@/lib/queries";

export default function LoginPage() {
  const router = useRouter();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login.mutateAsync({ email, password });
      router.push("/pipeline");
    } catch (err) {
      setError((err as Error).message || "Giriş başarısız.");
    }
  }

  return (
    <div className="min-h-screen bg-paper flex">
      {/* Sol — marka paneli */}
      <div className="hidden md:flex w-1/2 bg-ink-900 text-white p-12 relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage: "radial-gradient(rgba(255,255,255,0.7) 1px, transparent 1px)",
            backgroundSize: "20px 20px",
          }}
        />
        <div className="absolute -bottom-32 -right-32 w-[420px] h-[420px] rounded-full bg-accent/20 blur-3xl" />
        <div className="absolute top-12 right-12 w-[200px] h-[200px] rounded-full bg-accent/10 blur-2xl" />

        <div className="relative flex flex-col w-full max-w-[440px]">
          <div className="flex items-center gap-2.5">
            <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
              <rect x="2" y="2" width="28" height="28" rx="7" fill="#FAFAF6" />
              <path
                d="M9 19V10h6.5a4 4 0 0 1 0 8H11"
                stroke="#0E0F0C"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
              <circle cx="22" cy="22" r="2.2" fill="#0E6F4E" />
            </svg>
            <span className="text-[15px] font-semibold tracking-tightish">B1 Agent</span>
          </div>

          <div className="mt-auto">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/10 text-[12px] text-accent-100 mb-6">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              SAP Business One için AI operasyon paneli
            </div>
            <h1 className="text-[40px] leading-[1.05] font-semibold tracking-tightish">
              Doküman geldi.<br />
              <span className="text-accent-100">Sipariş çıktı.</span>
            </h1>
            <p className="mt-4 text-[14.5px] text-ink-300 leading-relaxed max-w-[400px]">
              PDF, e-posta ya da portaldan gelen her dokümanı çözümleyip
              SAP B1&apos;e tek tık ile gönderen ajan altyapısı.
            </p>

            <ul className="mt-10 space-y-3.5 text-[13.5px] text-ink-200">
              {[
                ["AI ile doküman → sipariş", "Çoklu format desteği, sahaya özel eşleme"],
                ["Eşik tabanlı otomatik onay", "Confidence + iş kuralı kombinasyonu"],
                ["Service Layer entegrasyonu", "Dry-run, JSON önizleme, rollback"],
              ].map(([title, sub]) => (
                <li key={title} className="flex items-start gap-3">
                  <span className="mt-1 inline-flex w-5 h-5 rounded-md bg-accent/30 text-accent-100 items-center justify-center shrink-0">
                    <Icon.check size={12} stroke={2.4} />
                  </span>
                  <div>
                    <div className="text-white font-medium">{title}</div>
                    <div className="text-ink-400">{sub}</div>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-12 pt-6 border-t border-white/10 grid grid-cols-3 gap-6 text-[12px] text-ink-400">
              <div>
                <div className="num text-[20px] text-white font-semibold">96.4%</div>
                match doğruluğu
              </div>
              <div>
                <div className="num text-[20px] text-white font-semibold">3.2s</div>
                ortalama işlem
              </div>
              <div>
                <div className="num text-[20px] text-white font-semibold">42</div>
                aktif iş akışı
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sağ — form paneli */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12 relative">
        <form onSubmit={onSubmit} className="w-full max-w-[400px]">
          <div className="md:hidden mb-8">
            <Logo />
          </div>

          <div className="mb-6">
            <h2 className="text-[22px] font-semibold tracking-tightish text-ink-900">
              Hoş geldiniz
            </h2>
            <p className="text-[13.5px] text-ink-500 mt-1">
              Devam etmek için hesabınıza giriş yapın.
            </p>
          </div>

          {error && (
            <div className="mb-4">
              <MessageStrip tone="danger" title="E-posta veya şifre hatalı">
                {error}
              </MessageStrip>
            </div>
          )}

          <div className="space-y-3.5">
            <div>
              <label className="block text-[12px] font-medium text-ink-700 mb-1.5">
                İş e-postası
              </label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ad.soyad@firma.com"
                icon={<Icon.mail size={14} />}
                autoComplete="email"
                required
                className="h-10"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-[12px] font-medium text-ink-700">Şifre</label>
                <button type="button" className="text-[11.5px] text-accent hover:underline">
                  Şifremi unuttum
                </button>
              </div>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                icon={<Icon.lock size={14} />}
                autoComplete="current-password"
                required
                className="h-10"
              />
            </div>

            <div className="flex items-center justify-between pt-1">
              <Checkbox checked={remember} onChange={setRemember} label="Beni 14 gün hatırla" />
              <span className="text-[11.5px] text-ink-500 inline-flex items-center gap-1">
                <Icon.shield size={12} /> SSO destekli
              </span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={login.isPending}
              className="w-full justify-center mt-2"
              iconRight={<Icon.chevR size={14} />}
            >
              {login.isPending ? "Bağlanıyor…" : "Giriş yap"}
            </Button>

            <div className="relative my-2">
              <div className="h-px bg-ink-200" />
              <span className="absolute left-1/2 -translate-x-1/2 -top-2.5 bg-paper px-2 text-[11px] uppercase tracking-wider text-ink-500">
                veya
              </span>
            </div>

            <Button
              type="button"
              variant="default"
              size="lg"
              className="w-full justify-center"
              icon={<Icon.shield size={14} />}
            >
              Kurumsal SSO ile devam et
            </Button>
          </div>

          <p className="mt-8 text-[12px] text-ink-500 text-center">
            Hesabınız mı yok? Sistem yöneticinizle iletişime geçin.
            <br />
            <span className="num">v3.1.4 · build 2026.05.17</span>
          </p>
        </form>
      </div>
    </div>
  );
}
