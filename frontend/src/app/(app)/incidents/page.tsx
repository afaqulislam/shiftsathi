"use client";

import { AlertTriangle, Plus, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Pagination } from "@/components/pagination";
import { IncidentStatusBadge, SeverityBadge } from "@/components/status";
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
import { Textarea } from "@/components/ui/textarea";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDateTime, humanize, relativeTime } from "@/lib/format";
import type { Incident, IncidentStatus, Severity } from "@/lib/types";
import { useAsyncData } from "@/lib/use-async";

const SEVERITIES: Severity[] = ["low", "medium", "high", "critical"];
const PAGE_SIZE = 20;
const STATUSES: IncidentStatus[] = [
  "open",
  "investigating",
  "resolved",
  "closed",
];

const NEXT_STATUS: Record<IncidentStatus, IncidentStatus[]> = {
  open: ["investigating", "resolved", "closed"],
  investigating: ["resolved", "closed", "open"],
  resolved: ["closed", "investigating"],
  closed: ["investigating"],
};

const SEVERITY_TONE: Record<Severity, string> = {
  low: "border-info/25 bg-info/10 text-info",
  medium: "border-warning/25 bg-warning/10 text-warning",
  high: "border-danger/25 bg-danger/10 text-danger",
  critical: "border-danger/40 bg-danger/20 text-danger",
};

export default function IncidentsPage() {
  const { me } = useAuth();
  const [status, setStatus] = useState("all");
  const [severity, setSeverity] = useState("all");
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [status, severity, search]);

  const { data, loading, error, reload } = useAsyncData(
    () =>
      api.incidents({
        status: status === "all" ? undefined : status,
        severity: severity === "all" ? undefined : severity,
        search: search || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    [status, severity, search, offset],
  );

  const incidents = data?.items ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Incidents"
        title="Reported issues"
        description="Anyone can report. Supervisors move issues through investigation to resolution."
        actions={
          <Button onClick={() => setCreating(true)}>
            <Plus className="size-4" strokeWidth={1.5} />
            Report incident
          </Button>
        }
      />

      <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-faint" strokeWidth={1.5} />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search incidents…"
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
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={severity} onValueChange={setSeverity}>
          <SelectTrigger className="lg:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All severities</SelectItem>
            {SEVERITIES.map((s) => (
              <SelectItem key={s} value={s} className="capitalize">
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-3xl" />
          ))}
        </div>
      ) : error ? (
        <EmptyState icon={AlertTriangle} title="Couldn't load incidents" description={error} />
      ) : incidents.length === 0 ? (
        <EmptyState
          icon={AlertTriangle}
          title="No incidents found"
          description="Nothing matches the current filters."
          action={
            <Button variant="secondary" onClick={() => setCreating(true)}>
              <Plus className="size-4" strokeWidth={1.5} />
              Report incident
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {incidents.map((incident) => (
            <Card key={incident.id}>
              <CardContent className="p-5">
                <button
                  className="flex w-full items-start justify-between gap-4 text-left"
                  onClick={() => setSelected(incident)}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{incident.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-muted">
                      {incident.description || "No description"}
                    </p>
                    <p className="mt-2 text-xs text-faint">
                      {incident.machine ?? "No machine"} ·{" "}
                      {relativeTime(incident.created_at)}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-2">
                    <span
                      className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-medium ${SEVERITY_TONE[incident.severity]}`}
                    >
                      {humanize(incident.severity)}
                    </span>
                    <IncidentStatusBadge value={incident.status} />
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

      <CreateIncidentDialog
        open={creating}
        onOpenChange={setCreating}
        onCreated={() => void reload()}
      />

      {selected ? (
        <IncidentDetailDialog
          incident={selected}
          canManage={me?.role === "admin" || me?.role === "supervisor"}
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

function CreateIncidentDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [machine, setMachine] = useState("");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [busy, setBusy] = useState(false);

  function reset() {
    setTitle("");
    setDescription("");
    setMachine("");
    setSeverity("medium");
  }

  async function submit() {
    if (title.trim().length < 3) {
      toast.error("Give the incident a short title.");
      return;
    }
    setBusy(true);
    try {
      await api.createIncident({
        title: title.trim(),
        description,
        machine: machine.trim() || null,
        severity,
      });
      toast.success("Incident reported");
      reset();
      onOpenChange(false);
      onCreated();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not report.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Report an incident</DialogTitle>
          <DialogDescription>
            Capture what happened so it can be investigated and resolved.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="inc-title">Title</Label>
            <Input
              id="inc-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Hydraulic press pressure drop"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="inc-desc">Description</Label>
            <Textarea
              id="inc-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What did you observe? Any error codes?"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="inc-machine">Machine (optional)</Label>
              <Input
                id="inc-machine"
                value={machine}
                onChange={(e) => setMachine(e.target.value)}
                placeholder="Press H2"
              />
            </div>
            <div className="space-y-2">
              <Label>Severity</Label>
              <Select
                value={severity}
                onValueChange={(v) => setSeverity(v as Severity)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SEVERITIES.map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={() => void submit()} disabled={busy}>
              {busy ? "Reporting…" : "Report"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function IncidentDetailDialog({
  incident,
  canManage,
  onClose,
  onUpdated,
}: {
  incident: Incident;
  canManage: boolean;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [target, setTarget] = useState<IncidentStatus | "">("");
  const [notes, setNotes] = useState(incident.resolution_notes ?? "");

  async function update() {
    if (!target) return;
    setBusy(true);
    try {
      await api.updateIncident(incident.id, {
        status: target,
        resolution_notes: notes || undefined,
      });
      toast.success(`Moved to ${humanize(target)}`);
      onUpdated();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Update failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{incident.title}</DialogTitle>
          <DialogDescription>
            Reported {formatDateTime(incident.created_at)}
          </DialogDescription>
        </DialogHeader>
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <SeverityBadge value={incident.severity} />
          <IncidentStatusBadge value={incident.status} />
          {incident.machine ? (
            <span className="text-xs text-faint">{incident.machine}</span>
          ) : null}
        </div>
        <p className="mb-5 whitespace-pre-wrap rounded-2xl border border-white/[0.07] bg-white/[0.02] p-3.5 text-sm text-muted">
          {incident.description || "No description provided."}
        </p>

        {canManage ? (
          <div className="space-y-4 border-t border-white/[0.06] pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Move to status</Label>
                <Select
                  value={target}
                  onValueChange={(v) => setTarget(v as IncidentStatus)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Choose status" />
                  </SelectTrigger>
                  <SelectContent>
                    {NEXT_STATUS[incident.status].map((s) => (
                      <SelectItem key={s} value={s} className="capitalize">
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="inc-notes">Resolution notes</Label>
              <Textarea
                id="inc-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Required when resolving…"
              />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={onClose}>
                Close
              </Button>
              <Button onClick={() => void update()} disabled={busy || !target}>
                {busy ? "Saving…" : "Save change"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex justify-end border-t border-white/[0.06] pt-4">
            <Button variant="ghost" onClick={onClose}>
              Close
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
