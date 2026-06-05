import { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { DocumentStatus, STATUS_LABEL } from "@/lib/types";

/* ============== Yeni jenerik Badge ============== */

export type Tone = "neutral" | "accent" | "info" | "warn" | "danger" | "ghost";

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  dot?: boolean;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const tones: Record<Tone, string> = {
  neutral: "bg-ink-100 text-ink-700 border-ink-200",
  accent: "bg-accent-100 text-accent border-accent-100",
  info: "bg-info-100 text-info border-info-100",
  warn: "bg-warn-100 text-warn border-warn-100",
  danger: "bg-danger-100 text-danger border-danger-100",
  ghost: "bg-transparent text-ink-600 border-ink-200",
};

const sizesMap: Record<NonNullable<BadgeProps["size"]>, string> = {
  sm: "text-[10.5px] px-1.5 h-[18px]",
  md: "text-[11.5px] px-2 h-[20px]",
  lg: "text-[12px] px-2.5 h-[22px]",
};

const dotTones: Record<Tone, string> = {
  neutral: "bg-ink-500",
  accent: "bg-accent",
  info: "bg-info",
  warn: "bg-warn",
  danger: "bg-danger",
  ghost: "bg-ink-500",
};

export function Badge({ children, tone = "neutral", dot, size = "md", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 border rounded-full font-medium tracking-tight whitespace-nowrap",
        tones[tone],
        sizesMap[size],
        className,
      )}
    >
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full", dotTones[tone])} />}
      {children}
    </span>
  );
}

/* ============== Eski API — geriye dönük uyum ============== */

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

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <Badge tone={STATUS_TONE[status]} dot size="sm">
      {STATUS_LABEL[status]}
    </Badge>
  );
}

export function ConfidenceBadge({ score }: { score: number | null | undefined }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const tone: Tone = pct >= 85 ? "accent" : pct >= 60 ? "warn" : "danger";
  return (
    <Badge tone={tone} size="sm">
      AI %{pct}
    </Badge>
  );
}
