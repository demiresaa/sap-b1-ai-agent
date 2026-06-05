import { ReactNode } from "react";

import { cn } from "@/lib/cn";

type Tone = "ink" | "accent" | "warn" | "info" | "danger";

interface KpiProps {
  label: ReactNode;
  value: ReactNode;
  delta?: string;
  tone?: Tone;
  sub?: ReactNode;
  icon?: ReactNode;
  className?: string;
}

const tonesMap: Record<Tone, string> = {
  ink: "text-ink-900",
  accent: "text-accent",
  warn: "text-warn",
  info: "text-info",
  danger: "text-danger",
};

export function Kpi({ label, value, delta, tone = "ink", sub, icon, className }: KpiProps) {
  const deltaTone = delta && delta.startsWith("-") ? "text-danger" : "text-accent";
  return (
    <div className={cn("bg-surface border border-ink-200 rounded-lg p-4 shadow-card", className)}>
      <div className="flex items-center justify-between text-[12px] text-ink-500">
        <span className="uppercase tracking-wider font-medium">{label}</span>
        {icon && <span className="text-ink-400">{icon}</span>}
      </div>
      <div className="mt-1.5 flex items-baseline gap-2">
        <span className={cn("num text-[28px] font-semibold tracking-tightish", tonesMap[tone])}>{value}</span>
        {delta && <span className={cn("num text-[12px]", deltaTone)}>{delta}</span>}
      </div>
      {sub && <div className="text-[12px] text-ink-500 mt-1">{sub}</div>}
    </div>
  );
}
