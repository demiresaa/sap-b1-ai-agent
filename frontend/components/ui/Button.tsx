"use client";

import { ButtonHTMLAttributes, ReactNode, forwardRef } from "react";

import { cn } from "@/lib/cn";

type Variant =
  | "primary"
  | "default"
  | "ghost"
  | "danger"
  | "soft"
  | "accentSoft"
  // Eski API geriye dönük uyum
  | "secondary";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  iconRight?: ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-500 border border-accent shadow-card",
  default:
    "bg-white text-ink-900 hover:bg-ink-50 border border-ink-200 shadow-card",
  ghost:
    "bg-transparent text-ink-800 hover:bg-ink-100 border border-transparent",
  danger:
    "bg-white text-danger hover:bg-danger-50 border border-ink-200",
  soft:
    "bg-ink-100 text-ink-900 hover:bg-ink-200 border border-transparent",
  accentSoft:
    "bg-accent-100 text-accent hover:bg-accent-50 border border-accent-100",
  // legacy
  secondary: "bg-ink-100 text-ink-900 hover:bg-ink-200 border border-transparent",
};

const sizes: Record<Size, string> = {
  sm: "h-7 px-2.5 text-[12.5px]",
  md: "h-8 px-3 text-[13px]",
  lg: "h-10 px-4 text-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    className,
    variant = "default",
    size = "md",
    loading,
    disabled,
    icon,
    iconRight,
    children,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md font-medium select-none whitespace-nowrap transition-colors focus-ring",
        sizes[size],
        variants[variant],
        (disabled || loading) && "opacity-50 cursor-not-allowed",
        className,
      )}
      {...rest}
    >
      {loading ? (
        <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden>
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
          <path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
        </svg>
      ) : (
        icon && <span className="-ml-0.5">{icon}</span>
      )}
      {children != null && <span>{children}</span>}
      {iconRight && <span className="-mr-0.5">{iconRight}</span>}
    </button>
  );
});
