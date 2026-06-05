"use client";

import { InputHTMLAttributes, ReactNode, forwardRef } from "react";

import { cn } from "@/lib/cn";

export type FieldState = "filled" | "uncertain" | "empty";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  fieldState?: FieldState;
  invalid?: boolean;
  icon?: ReactNode;
  prefix?: ReactNode;
  suffix?: ReactNode;
  /** İç input elementi için sınıf (nadiren gerekli) */
  inputClassName?: string;
}

const stateRing: Record<FieldState, string> = {
  filled: "border-accent/40",
  uncertain: "border-warn/60",
  empty: "border-ink-200",
};

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, inputClassName, fieldState = "empty", invalid, icon, prefix, suffix, ...rest },
  ref,
) {
  return (
    <div
      className={cn(
        "group h-9 flex items-center bg-white border rounded-md px-2.5 gap-2 transition-shadow",
        "focus-within:border-accent focus-within:shadow-[0_0_0_3px_rgba(14,111,78,0.12)]",
        stateRing[fieldState],
        invalid && "border-danger focus-within:border-danger focus-within:shadow-[0_0_0_3px_rgba(181,50,29,0.12)]",
        className,
      )}
    >
      {icon && <span className="text-ink-500 shrink-0">{icon}</span>}
      {prefix && <span className="text-ink-500 text-[13px] shrink-0">{prefix}</span>}
      <input
        ref={ref}
        className={cn(
          "flex-1 bg-transparent outline-none text-[13.5px] text-ink-900 placeholder:text-ink-400 min-w-0",
          inputClassName,
        )}
        {...rest}
      />
      {suffix && <span className="text-ink-500 text-[12px] shrink-0">{suffix}</span>}
    </div>
  );
});

export function FieldLabel({
  children,
  htmlFor,
  hint,
}: {
  children: ReactNode;
  htmlFor?: string;
  hint?: string | null;
}) {
  return (
    <label htmlFor={htmlFor} className="flex items-center justify-between text-[11px] font-medium uppercase tracking-wider text-ink-500 mb-1">
      <span>{children}</span>
      {hint ? <span className="text-[10px] font-normal normal-case tracking-normal text-ink-400">{hint}</span> : null}
    </label>
  );
}
