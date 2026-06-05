import { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface CardProps {
  children: ReactNode;
  className?: string;
  padded?: boolean;
}

export function Card({ children, className, padded = true }: CardProps) {
  return (
    <div
      className={cn(
        "bg-surface border border-ink-200 rounded-lg shadow-card",
        padded && "p-5",
        className,
      )}
    >
      {children}
    </div>
  );
}

interface SectionTitleProps {
  children: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function SectionTitle({ children, sub, action, className }: SectionTitleProps) {
  return (
    <div className={cn("flex items-end justify-between mb-3 gap-4", className)}>
      <div className="min-w-0">
        <h3 className="text-[14px] font-semibold text-ink-900 tracking-tightish">{children}</h3>
        {sub && <p className="text-[12.5px] text-ink-500 mt-0.5">{sub}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
