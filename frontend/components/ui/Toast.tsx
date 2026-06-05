"use client";

import {
  ReactNode,
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import { Icon } from "./icons";

interface ToastInput {
  message: ReactNode;
  icon?: ReactNode;
  duration?: number;
}

interface ToastItem extends ToastInput {
  id: string;
}

interface ToastContextValue {
  push: (toast: ToastInput) => void;
}

const ToastCtx = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const push = useCallback((toast: ToastInput) => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, ...toast }]);
    window.setTimeout(
      () => setToasts((t) => t.filter((x) => x.id !== id)),
      toast.duration ?? 2600,
    );
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 items-end pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto bg-ink-900 text-white text-[13px] px-3.5 py-2.5 rounded-md shadow-pop flex items-center gap-2 fade-in min-w-[220px]"
          >
            <span className="text-accent-100">{t.icon ?? <Icon.check2 size={16} />}</span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastCtx);
  if (!ctx) {
    // Provider yokken sessiz no-op — geliştirme sırasında zarar vermez
    return { push: () => {} };
  }
  return ctx;
}
