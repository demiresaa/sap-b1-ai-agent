"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

import { Logo } from "@/components/Logo";
import { Icon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";

interface NavItem {
  href: string;
  label: string;
  icon: ReactNode;
  badge?: number;
  badgeTone?: "warn" | "default";
  /** Aktif eşleşmesi için ek path prefix'leri */
  matchPrefixes?: string[];
}

const NAV: NavItem[] = [
  {
    href: "/pipeline",
    label: "Pipeline",
    icon: <Icon.flow size={16} />,
  },
  {
    href: "/orders",
    label: "Siparişler",
    icon: <Icon.doc size={16} />,
  },
  {
    href: "/quotes",
    label: "Teklifler",
    icon: <Icon.quote size={16} />,
  },
  {
    href: "/settings",
    label: "Ayarlar",
    icon: <Icon.cog size={16} />,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] shrink-0 bg-paper hair-r flex flex-col">
      {/* Logo */}
      <div className="h-[52px] px-4 flex items-center hair-b">
        <Logo />
      </div>

      {/* Nav */}
      <nav className="flex-1 p-2 space-y-0.5">
        {NAV.map((item) => {
          const active =
            pathname === item.href ||
            pathname?.startsWith(item.href + "/") ||
            item.matchPrefixes?.some((p) => pathname?.startsWith(p));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 h-8 px-2 rounded-md text-[13px] font-medium transition-colors group",
                active
                  ? "bg-ink-900 text-white"
                  : "text-ink-700 hover:bg-ink-100",
              )}
            >
              <span className={cn(active ? "text-white" : "text-ink-500 group-hover:text-ink-800")}>
                {item.icon}
              </span>
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge != null && (
                <span
                  className={cn(
                    "text-[10.5px] num px-1.5 h-4 rounded-full inline-flex items-center",
                    item.badgeTone === "warn"
                      ? "bg-warn-100 text-warn"
                      : active
                        ? "bg-white/15 text-white"
                        : "bg-ink-200 text-ink-700",
                  )}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Dry-run göstergesi */}
      <div className="p-2 hair-t">
        <div className="bg-surface border border-ink-200 rounded-md p-2.5">
          <div className="flex items-center gap-2 text-[11.5px] text-ink-600">
            <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-accent pulse-dot" />
            <span className="font-medium">Dry-Run aktif</span>
          </div>
          <div className="text-[11.5px] text-ink-500 mt-0.5 leading-snug">
            SAP&apos;a gerçek POST yapılmıyor.
          </div>
        </div>
      </div>
    </aside>
  );
}
