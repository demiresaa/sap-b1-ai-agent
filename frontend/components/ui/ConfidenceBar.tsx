import { cn } from "@/lib/cn";

interface ConfidenceBarProps {
  /** 0-100 arasında değer */
  value: number;
  showLabel?: boolean;
  width?: number;
  className?: string;
}

export function ConfidenceBar({ value, showLabel = true, width = 80, className }: ConfidenceBarProps) {
  const tone = value >= 80 ? "bg-accent" : value >= 60 ? "bg-warn" : "bg-danger";
  return (
    <div className={cn("inline-flex items-center gap-2", className)}>
      <div className="h-1.5 rounded-full bg-ink-100 overflow-hidden" style={{ width }}>
        <div className={cn(tone, "h-full rounded-full transition-all")} style={{ width: `${value}%` }} />
      </div>
      {showLabel && <span className="num text-[11.5px] text-ink-600 w-8 text-right">{value}%</span>}
    </div>
  );
}
