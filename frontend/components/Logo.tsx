interface LogoProps {
  size?: number;
  showLabel?: boolean;
}

export function Logo({ size = 28, showLabel = true }: LogoProps) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect x="2" y="2" width="28" height="28" rx="7" fill="#0E0F0C" />
        <path
          d="M9 19V10h6.5a4 4 0 0 1 0 8H11"
          stroke="#A6E5C7"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <circle cx="22" cy="22" r="2.2" fill="#0E6F4E" />
      </svg>
      {showLabel && (
        <span className="font-semibold tracking-tightish text-[14.5px] text-ink-900">
          B1 Agent
        </span>
      )}
    </span>
  );
}
