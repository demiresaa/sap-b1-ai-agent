import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & {
  size?: number;
  stroke?: number;
};

function I({ children, size = 16, stroke = 1.6, className, ...rest }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const Icon = {
  inbox: (p: IconProps) => (
    <I {...p}>
      <path d="M3 13l2-7h14l2 7" />
      <path d="M3 13v6h18v-6" />
      <path d="M8 13a4 4 0 0 0 8 0" />
    </I>
  ),
  flow: (p: IconProps) => (
    <I {...p}>
      <circle cx="5" cy="6" r="2" />
      <circle cx="19" cy="18" r="2" />
      <circle cx="5" cy="18" r="2" />
      <path d="M7 6h6a4 4 0 0 1 4 4v6" />
    </I>
  ),
  doc: (p: IconProps) => (
    <I {...p}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 13h6M9 17h4" />
    </I>
  ),
  quote: (p: IconProps) => (
    <I {...p}>
      <path d="M5 4h11l3 3v13a2 2 0 0 1-2 2H5z" />
      <path d="M9 9h6M9 13h6M9 17h4" />
    </I>
  ),
  check: (p: IconProps) => (
    <I {...p}>
      <path d="M4 12l5 5L20 6" />
    </I>
  ),
  check2: (p: IconProps) => (
    <I {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12l3 3 5-6" />
    </I>
  ),
  cross: (p: IconProps) => (
    <I {...p}>
      <path d="M6 6l12 12M18 6L6 18" />
    </I>
  ),
  bell: (p: IconProps) => (
    <I {...p}>
      <path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </I>
  ),
  cog: (p: IconProps) => (
    <I {...p}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </I>
  ),
  search: (p: IconProps) => (
    <I {...p}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </I>
  ),
  filter: (p: IconProps) => (
    <I {...p}>
      <path d="M3 5h18l-7 9v5l-4 2v-7z" />
    </I>
  ),
  plus: (p: IconProps) => (
    <I {...p}>
      <path d="M12 5v14M5 12h14" />
    </I>
  ),
  chevD: (p: IconProps) => (
    <I {...p}>
      <path d="M6 9l6 6 6-6" />
    </I>
  ),
  chevR: (p: IconProps) => (
    <I {...p}>
      <path d="M9 6l6 6-6 6" />
    </I>
  ),
  chevL: (p: IconProps) => (
    <I {...p}>
      <path d="M15 6l-6 6 6 6" />
    </I>
  ),
  dots: (p: IconProps) => (
    <I {...p}>
      <circle cx="5" cy="12" r="1.4" />
      <circle cx="12" cy="12" r="1.4" />
      <circle cx="19" cy="12" r="1.4" />
    </I>
  ),
  link: (p: IconProps) => (
    <I {...p}>
      <path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5" />
      <path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5" />
    </I>
  ),
  copy: (p: IconProps) => (
    <I {...p}>
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a2 2 0 0 1 2-2h10" />
    </I>
  ),
  user: (p: IconProps) => (
    <I {...p}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21a8 8 0 0 1 16 0" />
    </I>
  ),
  users: (p: IconProps) => (
    <I {...p}>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3 20a6 6 0 0 1 12 0" />
      <circle cx="17" cy="9" r="3" />
      <path d="M15 20a5 5 0 0 1 6-4" />
    </I>
  ),
  shield: (p: IconProps) => (
    <I {...p}>
      <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
      <path d="M9 12l2 2 4-4" />
    </I>
  ),
  bolt: (p: IconProps) => (
    <I {...p}>
      <path d="M13 3L4 14h7l-1 7 9-11h-7z" />
    </I>
  ),
  cpu: (p: IconProps) => (
    <I {...p}>
      <rect x="5" y="5" width="14" height="14" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M2 10h3M2 14h3M19 10h3M19 14h3M10 2v3M14 2v3M10 19v3M14 19v3" />
    </I>
  ),
  database: (p: IconProps) => (
    <I {...p}>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
      <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" />
    </I>
  ),
  logout: (p: IconProps) => (
    <I {...p}>
      <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
      <path d="M10 17l-5-5 5-5" />
      <path d="M15 12H5" />
    </I>
  ),
  mail: (p: IconProps) => (
    <I {...p}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 7l9 6 9-6" />
    </I>
  ),
  pdf: (p: IconProps) => (
    <I {...p}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5" />
      <path d="M9 14v3M9 14h2a1 1 0 1 1 0 2H9M13 17v-3h2M13 15.5h1.5M17 17v-3h2M17 15.5h2" />
    </I>
  ),
  download: (p: IconProps) => (
    <I {...p}>
      <path d="M12 4v12" />
      <path d="M7 11l5 5 5-5" />
      <path d="M5 20h14" />
    </I>
  ),
  edit: (p: IconProps) => (
    <I {...p}>
      <path d="M4 20h4l11-11-4-4L4 16z" />
      <path d="M14 5l4 4" />
    </I>
  ),
  refresh: (p: IconProps) => (
    <I {...p}>
      <path d="M4 4v6h6" />
      <path d="M20 20v-6h-6" />
      <path d="M5 14a8 8 0 0 0 14 3M19 10A8 8 0 0 0 5 7" />
    </I>
  ),
  warning: (p: IconProps) => (
    <I {...p}>
      <path d="M12 3l10 18H2z" />
      <path d="M12 10v5M12 18h.01" />
    </I>
  ),
  trash: (p: IconProps) => (
    <I {...p}>
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
    </I>
  ),
  info: (p: IconProps) => (
    <I {...p}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </I>
  ),
  sparkle: (p: IconProps) => (
    <I {...p}>
      <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" />
      <path d="M19 4l.7 1.8L21 6l-1.3.7L19 8l-.7-1.7L17 6l1.3-.7z" />
    </I>
  ),
  attach: (p: IconProps) => (
    <I {...p}>
      <path d="M21 11l-8.5 8.5a5 5 0 1 1-7-7L13 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L14 6" />
    </I>
  ),
  tag: (p: IconProps) => (
    <I {...p}>
      <path d="M20 12V4h-8L3 13l8 8z" />
      <circle cx="15.5" cy="8.5" r="1.2" />
    </I>
  ),
  calendar: (p: IconProps) => (
    <I {...p}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 9h18M8 3v4M16 3v4" />
    </I>
  ),
  ext: (p: IconProps) => (
    <I {...p}>
      <path d="M14 4h6v6" />
      <path d="M20 4L11 13" />
      <path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" />
    </I>
  ),
  eye: (p: IconProps) => (
    <I {...p}>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </I>
  ),
  lock: (p: IconProps) => (
    <I {...p}>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </I>
  ),
};

export type IconKey = keyof typeof Icon;
