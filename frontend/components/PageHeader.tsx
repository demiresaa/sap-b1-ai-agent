import { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface PageHeaderProps {
  eyebrow?: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
}

export function PageHeader({ eyebrow, title, subtitle, actions, children, className }: PageHeaderProps) {
  return (
    <div className={cn("hair-b bg-surface", className)}>
      <div className="px-6 py-4">
        <div className="flex items-end justify-between gap-4">
          <div className="min-w-0">
            {eyebrow && <div className="mb-1">{eyebrow}</div>}
            <h1 className="text-[20px] font-semibold tracking-tightish text-ink-900 leading-tight truncate">
              {title}
            </h1>
            {subtitle && <p className="text-[13px] text-ink-500 mt-1">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>
        {children && <div className="mt-3">{children}</div>}
      </div>
    </div>
  );
}
