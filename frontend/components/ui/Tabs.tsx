"use client";

import { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface TabItem {
  value: string;
  label: ReactNode;
  count?: number;
}

interface TabsProps {
  tabs: TabItem[];
  value: string;
  onChange?: (value: string) => void;
  className?: string;
}

export function Tabs({ tabs, value, onChange, className }: TabsProps) {
  return (
    <div className={cn("flex gap-0 hair-b", className)}>
      {tabs.map((t) => {
        const active = t.value === value;
        return (
          <button
            key={t.value}
            onClick={() => onChange?.(t.value)}
            className={cn(
              "px-3 h-10 text-[13px] font-medium relative -mb-px border-b-2 transition-colors",
              active
                ? "text-ink-900 border-accent"
                : "text-ink-500 hover:text-ink-800 border-transparent",
            )}
          >
            <span className="inline-flex items-center gap-1.5">
              {t.label}
              {typeof t.count === "number" && (
                <span
                  className={cn(
                    "text-[10.5px] num px-1 rounded-sm",
                    active ? "bg-accent-100 text-accent" : "bg-ink-100 text-ink-600",
                  )}
                >
                  {t.count}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
