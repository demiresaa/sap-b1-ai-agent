"use client";

import { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { Icon } from "./icons";

interface CheckboxProps {
  checked: boolean;
  onChange?: (value: boolean) => void;
  label?: ReactNode;
  className?: string;
  disabled?: boolean;
}

export function Checkbox({ checked, onChange, label, className, disabled }: CheckboxProps) {
  return (
    <label
      className={cn(
        "inline-flex items-center gap-2 select-none",
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
        className,
      )}
    >
      <span
        onClick={(e) => {
          e.stopPropagation();
          if (!disabled) onChange?.(!checked);
        }}
        className={cn(
          "w-4 h-4 rounded-[4px] border flex items-center justify-center transition",
          checked ? "bg-accent border-accent" : "bg-white border-ink-300 hover:border-ink-500",
        )}
      >
        {checked && <Icon.check size={11} className="text-white" />}
      </span>
      {label && <span className="text-[13px] text-ink-800">{label}</span>}
    </label>
  );
}
