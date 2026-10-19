"use client";

import { BadgeCheck, Library, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime, relativeTime } from "@/lib/format";
import type { VerifiedKnowledge } from "@/lib/types";
import { useAsyncData } from "@/lib/use-async";

export default function VerifiedKnowledgePage() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<VerifiedKnowledge | null>(null);
  const [offset, setOffset] = useState(0);
  const PAGE_SIZE = 24;

  useEffect(() => {
    setOffset(0);
  }, [search]);

  const { data, loading, error } = useAsyncData(
    () =>
      api.verifiedKnowledge({
        search: search || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    [search, offset],
  );

  const items = data?.items ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Verified Knowledge"
        title="Approved resolutions"
        description="Every verified resolution is searchable knowledge the assistant can cite — institutional memory that compounds."
      />

      <div className="relative mb-5 max-w-xl">
        <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-faint" strokeWidth={1.5} />
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search verified knowledge…"
          className="pl-11"
        />
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-40 rounded-3xl" />
          ))}
        </div>
      ) : error ? (
        <EmptyState icon={BadgeCheck} title="Couldn't load knowledge" description={error} />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Library}
          title="No verified knowledge yet"
          description="Supervisors verify resolved work orders and they appear here."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {items.map((item) => (
            <Card key={item.id}>
              <CardContent className="flex h-full flex-col p-5">
                <button
                  className="flex flex-1 flex-col text-left"
                  onClick={() => setSelected(item)}
                >
                  <div className="flex items-center gap-2">
                    <Badge tone="success">
                      <BadgeCheck className="size-3" strokeWidth={2} />
                      verified
                    </Badge>
                    {item.machine ? (
                      <span className="text-xs text-faint">{item.machine}</span>
                    ) : null}
                  </div>
                  <p className="mt-3 text-sm font-medium">{item.title}</p>
                  <p className="mt-1.5 line-clamp-3 flex-1 text-xs leading-relaxed text-muted">
                    {item.content}
                  </p>
                  <p className="mt-3 text-[11px] text-faint">
                    Approved {relativeTime(item.approved_at)}
                  </p>
                </button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Pagination
        total={data?.total ?? 0}
        limit={PAGE_SIZE}
        offset={offset}
        onChange={setOffset}
      />

      {selected ? (
        <Dialog open onOpenChange={(o) => !o && setSelected(null)}>
          <DialogContent className="max-w-xl">
            <DialogHeader>
              <DialogTitle>{selected.title}</DialogTitle>
              <DialogDescription>
                Approved {formatDateTime(selected.approved_at)}
              </DialogDescription>
            </DialogHeader>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge tone="success">
                <BadgeCheck className="size-3" strokeWidth={2} />
                verified
              </Badge>
              {selected.machine ? (
                <span className="text-xs text-faint">{selected.machine}</span>
              ) : null}
            </div>
            <p className="whitespace-pre-wrap rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4 text-sm leading-relaxed text-muted">
              {selected.content}
            </p>
          </DialogContent>
        </Dialog>
      ) : null}
    </div>
  );
}
