"use client";

import { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { Icon } from "./icons";

type Tone = "info" | "accent" | "warn" | "danger";

interface MessageStripProps {
  tone?: Tone;
  title?: ReactNode;
  children?: ReactNode;
  onClose?: () => void;
  action?: ReactNode;
  className?: string;
}

const tonesMap: Record<
  Tone,
  { bg: string; bar: string; tx: string; ic: ReactNode }
> = {
  info: { bg: "bg-info-50", bar: "bg-info", tx: "text-info", ic: <Icon.info size={16} /> },
  accent: { bg: "bg-accent-50", bar: "bg-accent", tx: "text-accent", ic: <Icon.check2 size={16} /> },
  warn: { bg: "bg-warn-50", bar: "bg-warn", tx: "text-warn", ic: <Icon.warning size={16} /> },
  danger: { bg: "bg-danger-50", bar: "bg-danger", tx: "text-danger", ic: <Icon.warning size={16} /> },
};

export function MessageStrip({ tone = "info", title, children, onClose, action, className }: MessageStripProps) {
  const t = tonesMap[tone];
  return (
    <div className={cn("relative rounded-md border border-ink-200/70 overflow-hidden flex", t.bg, className)}>
      <div className={cn("w-1 shrink-0", t.bar)} />
      <div className="flex-1 px-3 py-2.5 flex items-start gap-2.5">
        <div className={cn("mt-0.5", t.tx)}>{t.ic}</div>
        <div className="flex-1 min-w-0">
          {title && <div className="text-[13px] font-medium text-ink-900">{title}</div>}
          {children && <div className={cn("text-[12.5px] mt-0.5", title ? "text-ink-700" : "text-ink-800")}>{children}</div>}
        </div>
        {action}
        {onClose && (
          <button onClick={onClose} className="text-ink-500 hover:text-ink-800 mt-0.5">
            <Icon.cross size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
