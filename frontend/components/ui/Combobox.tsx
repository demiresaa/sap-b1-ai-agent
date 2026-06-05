"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import { FieldState } from "./Input";

interface ComboboxOption {
  value: string;
  label: string;
  hint?: string;
}

interface ComboboxProps {
  value: string | null;
  label: string;
  placeholder?: string;
  fieldState?: FieldState;
  onChange: (option: ComboboxOption | null) => void;
  onSearch: (query: string) => void;
  options: ComboboxOption[];
  loading?: boolean;
}

export function Combobox({
  value,
  label,
  placeholder,
  fieldState = "empty",
  onChange,
  onSearch,
  options,
  loading,
}: ComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(label);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setQuery(label);
  }, [label]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  function handleInput(value: string) {
    setQuery(value);
    setOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSearch(value), 350);
  }

  return (
    <div ref={wrapperRef} className="relative">
      <input
        value={query}
        placeholder={placeholder ?? "Aramak için yazın…"}
        onFocus={() => setOpen(true)}
        onChange={(e) => handleInput(e.target.value)}
        className={cn(
          "w-full rounded-md border px-2.5 py-1.5 text-sm shadow-sm transition focus:outline-none focus:ring-2 focus:ring-blue-500/60",
          fieldState === "filled" && "bg-ai-filled border-green-200",
          fieldState === "uncertain" && "bg-ai-uncertain border-yellow-300",
          fieldState === "empty" && "bg-ai-empty border-slate-200",
        )}
      />
      {value && (
        <button
          type="button"
          onClick={() => {
            onChange(null);
            setQuery("");
            onSearch("");
          }}
          className="absolute right-2 top-1.5 text-xs text-slate-400 hover:text-slate-700"
          aria-label="Seçimi temizle"
        >
          ✕
        </button>
      )}
      {open && (
        <div className="absolute z-20 mt-1 max-h-72 w-full overflow-y-auto rounded-md border bg-white shadow-lg">
          {loading && <div className="p-2 text-xs text-slate-400">Yükleniyor…</div>}
          {!loading && options.length === 0 && (
            <div className="p-2 text-xs text-slate-400">Sonuç yok — en az 2 karakter yazın</div>
          )}
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onChange(opt);
                setOpen(false);
                setQuery(opt.label);
              }}
              className="block w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
            >
              <div className="font-medium">{opt.label}</div>
              {opt.hint ? <div className="text-[11px] text-slate-500">{opt.hint}</div> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
