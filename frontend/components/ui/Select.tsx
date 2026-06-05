"use client";

import { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { Icon } from "./icons";

type Option = string | { value: string; label: string };

interface SelectProps {
  value: string;
  onChange?: (value: string) => void;
  options: Option[];
  placeholder?: string;
  className?: string;
  icon?: ReactNode;
  disabled?: boolean;
}

export function Select({ value, onChange, options = [], placeholder, className, icon, disabled }: SelectProps) {
  return (
    <div
      className={cn(
        "group h-9 flex items-center bg-white border border-ink-200 rounded-md pl-2.5 pr-7 gap-2 relative transition-shadow",
        "focus-within:border-accent focus-within:shadow-[0_0_0_3px_rgba(14,111,78,0.12)]",
        disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
    >
      {icon && <span className="text-ink-500 shrink-0">{icon}</span>}
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        className="flex-1 bg-transparent outline-none text-[13.5px] text-ink-900 appearance-none cursor-pointer min-w-0"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) =>
          typeof o === "string" ? (
            <option key={o} value={o}>
              {o}
            </option>
          ) : (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ),
        )}
      </select>
      <span className="absolute right-2 text-ink-500 pointer-events-none">
        <Icon.chevD size={14} />
      </span>
    </div>
  );
}
