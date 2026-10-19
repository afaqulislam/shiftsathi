"use client";

import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  ClipboardList,
  Clock,
  FileText,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { MiniBarList, StatCard } from "@/components/metrics";
import { PageHeader } from "@/components/page-header";
import { Reveal } from "@/components/reveal";
import {
  IncidentStatusBadge,
  SeverityBadge,
  WorkOrderStatusBadge,
} from "@/components/status";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/format";
import { useAsyncData } from "@/lib/use-async";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];
const WO_STATUS_ORDER = [
  "open",
  "assigned",
  "in_progress",
  "resolved",
  "closed",
];

export default function DashboardPage() {
  const { data, loading, error } = useAsyncData(() => api.dashboard(), []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 rounded-4xl" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-3xl" />
          ))}
        </div>
        <Skeleton className="h-72 rounded-4xl" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Couldn't load the dashboard"
        description={error ?? "Unexpected error."}
      />
    );
  }

  const m = data.metrics;
  const severityItems = SEVERITY_ORDER.filter(
    (s) => (m.incidents_by_severity[s] ?? 0) > 0 || s === "critical",
  ).map((s) => ({ label: s, value: m.incidents_by_severity[s] ?? 0 }));
  const woItems = WO_STATUS_ORDER.map((s) => ({
    label: s.replace("_", " "),
    value: m.work_orders_by_status[s] ?? 0,
  }));

  return (
    <div>
      <PageHeader
        eyebrow="Overview"
        title="Shift command"
        description="Live, database-backed signals across incidents, work orders, knowledge and approvals."
        actions={
          <Button asChild>
            <Link href="/assistant">
              <Sparkles className="size-4" strokeWidth={1.5} />
              Ask the assistant
            </Link>
          </Button>
        }
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Reveal>
          <StatCard
            label="Open incidents"
            value={m.open_incidents}
            icon={AlertTriangle}
            hint={`${m.resolved_last_7_days} resolved in the last 7 days`}
          />
        </Reveal>
        <Reveal delay={0.05}>
          <StatCard
            label="Active work orders"
            value={m.active_work_orders}
            icon={ClipboardList}
            hint={`${m.overdue_work_orders} overdue`}
          />
        </Reveal>
        <Reveal delay={0.1}>
          <StatCard
            label="Pending approvals"
            value={m.pending_approvals}
            icon={Clock}
            hint="Resolved work orders awaiting verification"
          />
        </Reveal>
        <Reveal delay={0.15}>
          <StatCard
            label="Verified knowledge"
            value={m.verified_knowledge_count}
            icon={BadgeCheck}
            accent
            hint="Human-approved resolutions"
          />
        </Reveal>
        <Reveal delay={0.2}>
          <StatCard
            label="Documents indexed"
            value={m.documents.indexed}
            icon={FileText}
            hint={`${m.documents.processing} processing · ${m.documents.failed} failed`}
          />
        </Reveal>
        <Reveal delay={0.25}>
          <StatCard
            label="Overdue work orders"
            value={m.overdue_work_orders}
            icon={Clock}
            hint="Past due date and not closed"
          />
        </Reveal>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Reveal className="lg:col-span-2">
          <Card>
            <CardContent className="p-6">
              <div className="mb-5 flex items-center justify-between">
                <CardTitle>Recent incidents</CardTitle>
                <Button asChild variant="ghost" size="sm">
                  <Link href="/incidents">View all</Link>
                </Button>
              </div>
              {data.recent_incidents.length === 0 ? (
                <EmptyState
                  icon={AlertTriangle}
                  title="No incidents yet"
                  description="Reported issues will surface here."
                />
              ) : (
                <ul className="divide-y divide-white/[0.06]">
                  {data.recent_incidents.slice(0, 6).map((incident) => (
                    <li
                      key={incident.id}
                      className="flex items-center justify-between gap-4 py-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground">
                          {incident.title}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-faint">
                          {incident.machine ?? "No machine"} ·{" "}
                          {relativeTime(incident.created_at)}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <SeverityBadge value={incident.severity} />
                        <IncidentStatusBadge value={incident.status} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </Reveal>

        <Reveal delay={0.05}>
          <Card className="h-full">
            <CardContent className="p-6">
              <CardTitle className="mb-5">Incidents by severity</CardTitle>
              <MiniBarList items={severityItems} />
            </CardContent>
          </Card>
        </Reveal>

        <Reveal>
          <Card>
            <CardContent className="p-6">
              <div className="mb-5 flex items-center justify-between">
                <CardTitle>Active work orders</CardTitle>
                <Button asChild variant="ghost" size="sm">
                  <Link href="/work-orders">View all</Link>
                </Button>
              </div>
              {data.recent_work_orders.length === 0 ? (
                <EmptyState
                  icon={ClipboardList}
                  title="No work orders yet"
                  description="Assigned tasks will appear here."
                />
              ) : (
                <ul className="divide-y divide-white/[0.06]">
                  {data.recent_work_orders.slice(0, 5).map((wo) => (
                    <li
                      key={wo.id}
                      className="flex items-center justify-between gap-4 py-3"
                    >
                      <div className="min-w-0">
                        <p className="truncate text-sm text-foreground">
                          {wo.title}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-faint">
                          {wo.assignee
                            ? `Assigned to ${wo.assignee.full_name}`
                            : "Unassigned"}
                        </p>
                      </div>
                      <WorkOrderStatusBadge value={wo.status} />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </Reveal>

        <Reveal delay={0.05}>
          <Card className="h-full">
            <CardContent className="p-6">
              <CardTitle className="mb-5">Work orders by status</CardTitle>
              <MiniBarList items={woItems} />
            </CardContent>
          </Card>
        </Reveal>

        <Reveal delay={0.1} className="lg:col-span-2">
          <Card className="h-full">
            <CardContent className="p-6">
              <div className="mb-5 flex items-center gap-2">
                <Activity className="size-4 text-faint" strokeWidth={1.5} />
                <CardTitle>Recent activity</CardTitle>
              </div>
              {data.recent_activity.length === 0 ? (
                <p className="py-6 text-center text-sm text-faint">
                  Audit events will appear as your team works.
                </p>
              ) : (
                <ul className="space-y-3">
                  {data.recent_activity.slice(0, 7).map((entry) => (
                    <li
                      key={entry.id}
                      className="flex items-center justify-between gap-4 text-sm"
                    >
                      <span className="text-muted">
                        <span className="font-mono text-xs text-accent">
                          {entry.action}
                        </span>{" "}
                        <span className="text-faint">
                          · {entry.entity_type}
                        </span>
                      </span>
                      <span className="shrink-0 text-xs text-faint">
                        {relativeTime(entry.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </Reveal>
      </div>
    </div>
  );
}
