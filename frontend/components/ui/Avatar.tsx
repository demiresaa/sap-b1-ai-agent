import { cn } from "@/lib/cn";

type Tone = "ink" | "accent" | "soft";

interface AvatarProps {
  name?: string;
  size?: number;
  tone?: Tone;
  className?: string;
}

const tonesMap: Record<Tone, string> = {
  ink: "bg-ink-900 text-white",
  accent: "bg-accent text-white",
  soft: "bg-ink-200 text-ink-800",
};

export function Avatar({ name = "?", size = 28, tone = "ink", className }: AvatarProps) {
  const initials = name
    .split(" ")
    .map((s) => s[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  return (
    <span
      className={cn("inline-flex items-center justify-center rounded-full font-medium", tonesMap[tone], className)}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.4) }}
    >
      {initials}
    </span>
  );
}
