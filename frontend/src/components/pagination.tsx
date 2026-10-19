"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Pagination({
  total,
  limit,
  offset,
  onChange,
  className,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
  className?: string;
}) {
  if (total <= limit) return null;
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.max(1, Math.ceil(total / limit));
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);

  return (
    <div
      className={cn(
        "mt-5 flex items-center justify-between gap-3",
        className,
      )}
    >
      <p className="text-xs tabular-nums text-faint">
        {from}–{to} of {total}
      </p>
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          disabled={offset <= 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          <ChevronLeft className="size-4" strokeWidth={1.5} />
          Prev
        </Button>
        <span className="text-xs tabular-nums text-faint">
          Page {page} / {pages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={to >= total}
          onClick={() => onChange(offset + limit)}
        >
          Next
          <ChevronRight className="size-4" strokeWidth={1.5} />
        </Button>
      </div>
    </div>
  );
}
