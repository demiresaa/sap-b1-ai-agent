"use client";

import { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface SwitchProps {
  checked: boolean;
  onChange?: (value: boolean) => void;
  label?: ReactNode;
  sublabel?: ReactNode;
  disabled?: boolean;
  className?: string;
}

export function Switch({ checked, onChange, label, sublabel, disabled, className }: SwitchProps) {
  return (
    <div className={cn("flex items-center justify-between gap-4", className)}>
      {label && (
        <div className="min-w-0">
          <div className="text-[13.5px] font-medium text-ink-900">{label}</div>
          {sublabel && <div className="text-[12px] text-ink-500 mt-0.5">{sublabel}</div>}
        </div>
      )}
      <button
        type="button"
        onClick={() => !disabled && onChange?.(!checked)}
        disabled={disabled}
        className={cn(
          "relative inline-flex h-5 w-9 rounded-full transition-colors shrink-0",
          checked ? "bg-accent" : "bg-ink-300",
          disabled && "opacity-50 cursor-not-allowed",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform",
            checked ? "translate-x-[18px]" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  );
}
