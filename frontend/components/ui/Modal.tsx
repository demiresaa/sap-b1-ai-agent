"use client";

import { ReactNode, useEffect } from "react";

import { cn } from "@/lib/cn";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  size?: "md" | "lg" | "xl";
}

const sizes = {
  md: "max-w-xl",
  lg: "max-w-3xl",
  xl: "max-w-5xl",
};

export function Modal({ open, onClose, title, children, footer, size = "lg" }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-900/50"
      onClick={onClose}
      aria-modal="true"
      role="dialog"
    >
      <div
        className={cn(
          "relative w-full max-h-[90vh] flex flex-col rounded-lg bg-white shadow-xl overflow-hidden",
          sizes[size],
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {title !== undefined && (
          <div className="flex items-center justify-between border-b border-ink-200 px-5 py-3">
            <div className="text-sm font-semibold text-ink-900">{title}</div>
            <button
              type="button"
              onClick={onClose}
              className="text-ink-500 hover:text-ink-900 rounded p-1"
              aria-label="Kapat"
            >
              ✕
            </button>
          </div>
        )}
        <div className="flex-1 overflow-auto px-5 py-4">{children}</div>
        {footer && (
          <div className="border-t border-ink-200 px-5 py-3 flex justify-end gap-2">{footer}</div>
        )}
      </div>
    </div>
  );
}
