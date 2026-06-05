"use client";

import { useState } from "react";

import { Combobox } from "@/components/ui/Combobox";
import { FieldState } from "@/components/ui/Input";
import { useItems } from "@/lib/queries";

interface Props {
  itemCode: string | null;
  itemName: string | null;
  fallbackDescription?: string;
  onChange: (item: { code: string; name: string } | null) => void;
  fieldState?: FieldState;
}

export function ItemPicker({
  itemCode,
  itemName,
  fallbackDescription,
  onChange,
  fieldState = "empty",
}: Props) {
  const [query, setQuery] = useState(itemName ?? fallbackDescription ?? "");
  const { data: results = [], isLoading } = useItems(query);

  return (
    <Combobox
      label={itemName ?? fallbackDescription ?? ""}
      value={itemCode}
      placeholder="Ürün kodu/adı/barkod (≥2 karakter)"
      fieldState={fieldState}
      onSearch={setQuery}
      loading={isLoading}
      onChange={(opt) => onChange(opt ? { code: opt.value, name: opt.label } : null)}
      options={results.map((it) => ({
        value: it.ItemCode,
        label: it.ItemName,
        hint: [it.ItemCode, it.BarCode].filter(Boolean).join(" • "),
      }))}
    />
  );
}
