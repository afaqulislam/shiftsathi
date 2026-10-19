"use client";

import {
  AlertTriangle,
  BadgeCheck,
  ClipboardList,
  Plus,
  Search,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { PriorityBadge, WorkOrderStatusBadge } from "@/components/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, humanize, relativeTime } from "@/lib/format";
import type {
  Incident,
  Member,
  Priority,
  WorkOrder,
  WorkOrderStatus,
} from "@/lib/types";
import { useAsyncData } from "@/lib/use-async";

const STATUSES: WorkOrderStatus[] = [
  "open",
  "assigned",
  "in_progress",
  "resolved",
  "closed",
];
const PRIORITIES: Priority[] = ["low", "medium", "high", "urgent"];
const PAGE_SIZE = 20;

const TRANSITIONS: Record<WorkOrderStatus, WorkOrderStatus[]> = {
  open: ["assigned", "in_progress", "resolved", "closed"],
  assigned: ["in_progress", "resolved", "open"],
  in_progress: ["resolved", "assigned"],
  resolved: ["closed", "in_progress"],
  closed: ["in_progress"],
};

export default function WorkOrdersPage() {
  const { me } = useAuth();
  const canManage = me?.role === "admin" || me?.role === "supervisor";

  const [status, setStatus] = useState("all");
  const [priority, setPriority] = useState("all");
  const [overdue, setOverdue] = useState(false);
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<WorkOrder | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [status, priority, overdue, search]);

  const { data, loading, error, reload } = useAsyncData(
    () =>
      api.workOrders({
        status: status === "all" ? undefined : status,
        priority: priority === "all" ? undefined : priority,
        overdue_only: overdue || undefined,
        search: search || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    [status, priority, overdue, search, offset],
  );

  const workOrders = data?.items ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Work Orders"
        title="Execution queue"
        description="Assign, track and resolve the work that keeps the line running."
        actions={
          canManage ? (
            <Button onClick={() => setCreating(true)}>
              <Plus className="size-4" strokeWidth={1.5} />
              New work order
            </Button>
          ) : undefined
        }
      />

      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-faint" strokeWidth={1.5} />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search work orders…"
            className="pl-11"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="lg:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">
                {s.replace("_", " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={priority} onValueChange={setPriority}>
          <SelectTrigger className="lg:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priorities</SelectItem>
            {PRIORITIES.map((p) => (
              <SelectItem key={p} value={p} className="capitalize">
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <label className="flex items-center gap-2.5 rounded-2xl border border-white/10 bg-white/[0.02] px-4 py-2.5 text-sm text-muted">
          <Switch checked={overdue} onCheckedChange={setOverdue} />
          Overdue only
        </label>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-3xl" />
          ))}
        </div>
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Couldn't load work orders" description={error} />
      ) : workOrders.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No work orders found"
          description="Nothing matches the current filters."
          action={
            canManage ? (
              <Button variant="secondary" onClick={() => setCreating(true)}>
                <Plus className="size-4" strokeWidth={1.5} />
                New work order
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div className="space-y-3">
          {workOrders.map((wo) => (
            <Card key={wo.id}>
              <CardContent className="p-5">
                <button
                  className="flex w-full items-start justify-between gap-4 text-left"
                  onClick={() => setSelected(wo)}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-medium">{wo.title}</p>
                      {wo.is_verified ? (
                        <Badge tone="success">
                          <BadgeCheck className="size-3" strokeWidth={2} />
                          verified
                        </Badge>
                      ) : null}
                    </div>
                    <p className="mt-1 line-clamp-1 text-xs text-muted">
                      {wo.description || "No description"}
                    </p>
                    <p className="mt-2 text-xs text-faint">
                      {wo.assignee
                        ? `Assigned to ${wo.assignee.full_name}`
                        : "Unassigned"}
                      {wo.machine ? ` · ${wo.machine}` : ""} ·{" "}
                      {relativeTime(wo.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <PriorityBadge value={wo.priority} />
                    <WorkOrderStatusBadge value={wo.status} />
                  </div>
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

      {creating ? (
        <CreateWorkOrderDialog
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            void reload();
          }}
        />
      ) : null}

      {selected ? (
        <WorkOrderDetailDialog
          workOrder={selected}
          role={me?.role ?? "worker"}
          userId={me?.user.id ?? ""}
          onClose={() => setSelected(null)}
          onUpdated={() => {
            setSelected(null);
            void reload();
          }}
        />
      ) : null}
    </div>
  );
}

function CreateWorkOrderDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [machine, setMachine] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");
  const [assigneeId, setAssigneeId] = useState<string>("");
  const [incidentId, setIncidentId] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const { data: members } = useAsyncData<Member[]>(() => api.members(), []);
  const { data: incidents } = useAsyncData(
    () => api.incidents({ status: "open", limit: 50 }),
    [],
  );

  async function submit() {
    if (title.trim().length < 3) {
      toast.error("Give the work order a title.");
      return;
    }
    setBusy(true);
    try {
      await api.createWorkOrder({
        title: title.trim(),
        description,
        machine: machine.trim() || null,
        priority,
        assignee_id: assigneeId || null,
        incident_id: incidentId || null,
      });
      toast.success("Work order created");
      onCreated();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>New work order</DialogTitle>
          <DialogDescription>
            Assign work and, optionally, link it to an open incident.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="wo-title">Title</Label>
            <Input
              id="wo-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Replace hydraulic seal kit"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="wo-desc">Description</Label>
            <Textarea
              id="wo-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What needs to be done?"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select
                value={priority}
                onValueChange={(v) => setPriority(v as Priority)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p} value={p} className="capitalize">
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="wo-machine">Machine (optional)</Label>
              <Input
                id="wo-machine"
                value={machine}
                onChange={(e) => setMachine(e.target.value)}
                placeholder="Press H2"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Assignee</Label>
              <Select value={assigneeId} onValueChange={setAssigneeId}>
                <SelectTrigger>
                  <SelectValue placeholder="Unassigned" />
                </SelectTrigger>
                <SelectContent>
                  {members?.map((m) => (
                    <SelectItem key={m.user.id} value={m.user.id}>
                      {m.user.full_name} · {humanize(m.role)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Link incident</Label>
              <Select value={incidentId} onValueChange={setIncidentId}>
                <SelectTrigger>
                  <SelectValue placeholder="None" />
                </SelectTrigger>
                <SelectContent>
                  {incidents?.items.map((inc: Incident) => (
                    <SelectItem key={inc.id} value={inc.id}>
                      {inc.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy}>
              {busy ? "Creating…" : "Create"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function WorkOrderDetailDialog({
  workOrder,
  role,
  userId,
  onClose,
  onUpdated,
}: {
  workOrder: WorkOrder;
  role: "admin" | "supervisor" | "worker";
  userId: string;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState<WorkOrderStatus | "">("");
  const [notes, setNotes] = useState(workOrder.resolution_notes ?? "");

  const isSupervisor = role === "admin" || role === "supervisor";
  const isAssignee = workOrder.assignee_id === userId;

  const allowed = TRANSITIONS[workOrder.status].filter((s) => {
    if (isSupervisor) return true;
    if (!isAssignee) return false;
    return s === "in_progress" || s === "resolved";
  });

  async function changeStatus() {
    if (!target) return;
    setBusy(true);
    try {
      await api.changeWorkOrderStatus(workOrder.id, target, notes || undefined);
      toast.success(`Moved to ${humanize(target)}`);
      onUpdated();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  async function verify(verified: boolean) {
    setBusy(true);
    try {
      await api.verifyWorkOrder(workOrder.id, verified);
      toast.success(verified ? "Resolution verified" : "Verification revoked");
      onUpdated();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  const canVerify =
    isSupervisor &&
    (workOrder.status === "resolved" || workOrder.status === "closed") &&
    Boolean(workOrder.resolution_notes);

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{workOrder.title}</DialogTitle>
          <DialogDescription>
            Created {formatDateTime(workOrder.created_at)}
          </DialogDescription>
        </DialogHeader>

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <PriorityBadge value={workOrder.priority} />
          <WorkOrderStatusBadge value={workOrder.status} />
          {workOrder.is_verified ? (
            <Badge tone="success">
              <BadgeCheck className="size-3" strokeWidth={2} />
              verified
            </Badge>
          ) : null}
          <span className="text-xs text-faint">
            {workOrder.assignee
              ? `Assigned to ${workOrder.assignee.full_name}`
              : "Unassigned"}
          </span>
        </div>

        <p className="mb-4 whitespace-pre-wrap rounded-2xl border border-white/[0.07] bg-white/[0.02] p-3.5 text-sm text-muted">
          {workOrder.description || "No description provided."}
        </p>

        {workOrder.resolution_notes ? (
          <div className="mb-4 rounded-2xl border border-success/20 bg-success/[0.06] p-3.5">
            <p className="mb-1 text-[11px] uppercase tracking-[0.14em] text-success">
              Resolution
            </p>
            <p className="text-sm text-foreground/90">
              {workOrder.resolution_notes}
            </p>
          </div>
        ) : null}

        <div className="space-y-4 border-t border-white/[0.06] pt-4">
          {allowed.length > 0 ? (
            <>
              <div className="space-y-2">
                <Label>Move to status</Label>
                <Select
                  value={target}
                  onValueChange={(v) => setTarget(v as WorkOrderStatus)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Choose status" />
                  </SelectTrigger>
                  <SelectContent>
                    {allowed.map((s) => (
                      <SelectItem key={s} value={s} className="capitalize">
                        {s.replace("_", " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="wo-notes">Resolution notes</Label>
                <Textarea
                  id="wo-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Required when resolving…"
                />
              </div>
              <div className="flex items-center justify-between gap-2">
                <Button variant="ghost" onClick={onClose}>
                  Close
                </Button>
                <Button onClick={() => void changeStatus()} disabled={busy || !target}>
                  {busy ? "Saving…" : "Save change"}
                </Button>
              </div>
            </>
          ) : (
            <div className="flex justify-end">
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
            </div>
          )}

          {canVerify ? (
            <div className="flex items-center justify-between gap-3 rounded-2xl border border-accent-soft/25 bg-accent/[0.06] p-3.5">
              <div>
                <p className="text-sm font-medium">
                  {workOrder.is_verified
                    ? "This resolution is verified"
                    : "Verify this resolution"}
                </p>
                <p className="text-xs text-muted">
                  Verified resolutions become searchable knowledge for the whole
                  team.
                </p>
              </div>
              <Button
                variant={workOrder.is_verified ? "outline" : "primary"}
                size="sm"
                disabled={busy}
                onClick={() => void verify(!workOrder.is_verified)}
              >
                {workOrder.is_verified ? "Revoke" : "Verify"}
              </Button>
            </div>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
