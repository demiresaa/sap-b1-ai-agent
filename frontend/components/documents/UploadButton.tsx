"use client";

import { Upload } from "lucide-react";
import { ChangeEvent, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { Icon } from "@/components/ui/icons";
import { useUploadDocument } from "@/lib/queries";

export function UploadButton() {
  const inputRef = useRef<HTMLInputElement>(null);
  const upload = useUploadDocument();
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  async function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    try {
      await upload.mutateAsync(file);
      toast.push({
        icon: <Icon.sparkle size={16} />,
        duration: 4000,
        message: (
          <span>
            <strong>{file.name}</strong> yüklendi. AI işleme başlıyor — durumu pipeline'da takip edin.
          </span>
        ),
      });
    } catch (err) {
      const msg = (err as Error).message || "Yukleme basarisiz.";
      setError(msg);
      toast.push({
        icon: <Icon.warning size={16} />,
        duration: 5000,
        message: <span>Yukleme basarisiz: {msg}</span>,
      });
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col items-start gap-1">
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls,.pdf,.docx,.png,.jpg,.jpeg"
        onChange={onChange}
        className="hidden"
      />
      <Button
        onClick={() => inputRef.current?.click()}
        loading={upload.isPending}
        disabled={upload.isPending}
      >
        <Upload className="h-4 w-4" />
        {upload.isPending ? "Yukleniyor..." : "Excel veya PDF Yukle"}
      </Button>
      {upload.isPending && (
        <span className="text-xs text-muted-foreground animate-pulse">
          Dosya yukleniyor, lutfen bekleyin...
        </span>
      )}
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
