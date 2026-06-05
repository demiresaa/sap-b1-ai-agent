import { cn } from "@/lib/cn";

interface PlaceholderProps {
  label?: string;
  height?: number;
  className?: string;
}

export function Placeholder({ label = "placeholder", height = 240, className }: PlaceholderProps) {
  return (
    <div
      className={cn(
        "stripe-bg rounded-md border border-ink-200 flex items-center justify-center text-ink-500",
        className,
      )}
      style={{ height }}
    >
      <span className="num text-[11px] uppercase tracking-wider bg-paper px-2 py-1 rounded border border-ink-200">
        {label}
      </span>
    </div>
  );
}
