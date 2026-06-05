/**
 * TR formatlama yardımcıları — para, tarih, dosya boyutu.
 */

export function formatCurrency(value: number | null | undefined, currency = "TRY"): string {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(value);
  } catch {
    return `${value} ${currency}`;
  }
}

export function formatNumber(value: number | null | undefined, fractionDigits = 2): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("tr-TR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("tr-TR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

/**
 * Kompakt UI biçimleyiciler — para/sayı/tarih için "—" yerine boş string döner.
 * Tablo hücreleri ve KPI'larda kullanılır.
 */
export const fmt = {
  tl(n: number | null | undefined, currency = "₺"): string {
    if (n == null || Number.isNaN(n)) return "";
    return (
      n.toLocaleString("tr-TR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }) + ` ${currency}`
    );
  },
  num(n: number | null | undefined): string {
    if (n == null || Number.isNaN(n)) return "";
    return n.toLocaleString("tr-TR");
  },
  date(d: string | Date | null | undefined): string {
    if (!d) return "";
    return new Date(d).toLocaleDateString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  },
  dateTime(d: string | Date | null | undefined): string {
    if (!d) return "";
    return new Date(d).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },
};
