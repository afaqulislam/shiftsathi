import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  accent = false,
  className,
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  hint?: string;
  accent?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-white/[0.07] bg-white/[0.02] p-5 shadow-inner-hairline transition-colors duration-500 hover:border-white/[0.12]",
        accent && "bg-accent/[0.07] border-accent-soft/25",
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted">
          {label}
        </p>
        <Icon
          className={cn("size-4 text-faint", accent && "text-accent")}
          strokeWidth={1.5}
        />
      </div>
      <p className="mt-4 text-3xl font-medium tracking-tight tabular-nums">
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-faint">{hint}</p> : null}
    </div>
  );
}

export function MiniBarList({
  items,
  emptyLabel = "No data yet.",
}: {
  items: { label: string; value: number }[];
  emptyLabel?: string;
}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  const total = items.reduce((sum, i) => sum + i.value, 0);
  if (total === 0) {
    return <p className="py-6 text-center text-sm text-faint">{emptyLabel}</p>;
  }
  return (
    <ul className="space-y-3.5">
      {items.map((item) => (
        <li key={item.label} className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="capitalize text-muted">{item.label}</span>
            <span className="tabular-nums text-foreground">{item.value}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.05]">
            <div
              className="h-full rounded-full bg-accent/80 transition-[width] duration-700 ease-silk"
              style={{ width: `${Math.max(4, (item.value / max) * 100)}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
