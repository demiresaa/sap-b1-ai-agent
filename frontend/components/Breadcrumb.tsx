import { Icon } from "@/components/ui/icons";

interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
}

export function Breadcrumb({ items }: BreadcrumbProps) {
  return (
    <nav className="flex items-center gap-1.5 text-[12px] text-ink-500">
      {items.map((it, i) => (
        <span key={i} className="inline-flex items-center gap-1.5">
          {i > 0 && <Icon.chevR size={12} className="text-ink-400" />}
          {it.onClick ? (
            <button onClick={it.onClick} className="hover:text-ink-800">
              {it.label}
            </button>
          ) : (
            <span className={i === items.length - 1 ? "text-ink-800 font-medium" : ""}>
              {it.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
