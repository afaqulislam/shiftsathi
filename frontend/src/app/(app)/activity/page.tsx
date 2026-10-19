"use client";

import { Activity as ActivityIcon, ScrollText } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatDateTime, humanize, relativeTime } from "@/lib/format";
import { useAsyncData } from "@/lib/use-async";

function formatAction(action: string): string {
  return action.split(".").map(humanize).join(" · ");
}

export default function ActivityPage() {
  const [offset, setOffset] = useState(0);
  const PAGE_SIZE = 25;

  const { data, loading, error } = useAsyncData(
    () => api.activity({ limit: PAGE_SIZE, offset }),
    [offset],
  );

  const items = data?.items ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Activity"
        title="Audit trail"
        description="Every consequential action across incidents, work orders, verification, and knowledge — recorded with actor and time."
      />

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-3xl" />
          ))}
        </div>
      ) : error ? (
        <EmptyState
          icon={ActivityIcon}
          title="Couldn't load activity"
          description={error}
        />
      ) : items.length === 0 ? (
        <EmptyState
          icon={ScrollText}
          title="No activity yet"
          description="Actions taken in this workspace will appear here."
        />
      ) : (
        <Card>
          <CardContent className="p-2">
            <ol className="divide-y divide-white/[0.06]">
              {items.map((event) => (
                <li
                  key={event.id}
                  className="flex items-start gap-4 px-3 py-3.5"
                >
                  <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.03]">
                    <ActivityIcon
                      className="size-4 text-accent"
                      strokeWidth={1.5}
                    />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium">
                        {formatAction(event.action)}
                      </p>
                      <Badge tone="neutral">{humanize(event.entity_type)}</Badge>
                    </div>
                    <p className="mt-1 text-[11px] text-faint">
                      {formatDateTime(event.created_at)} ·{" "}
                      {relativeTime(event.created_at)}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      <Pagination
        total={data?.total ?? 0}
        limit={PAGE_SIZE}
        offset={offset}
        onChange={setOffset}
      />
    </div>
  );
}
