import { Badge } from "@/components/ui/badge";
import type {
  DocumentStatus,
  IncidentStatus,
  Priority,
  Severity,
  WorkOrderStatus,
} from "@/lib/types";
import { humanize } from "@/lib/format";

type Tone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

const SEVERITY_TONE: Record<Severity, Tone> = {
  low: "info",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

const INCIDENT_TONE: Record<IncidentStatus, Tone> = {
  open: "warning",
  investigating: "info",
  resolved: "success",
  closed: "neutral",
};

const WORK_ORDER_TONE: Record<WorkOrderStatus, Tone> = {
  open: "warning",
  assigned: "info",
  in_progress: "accent",
  resolved: "success",
  closed: "neutral",
};

const PRIORITY_TONE: Record<Priority, Tone> = {
  low: "neutral",
  medium: "info",
  high: "warning",
  urgent: "danger",
};

const DOC_TONE: Record<DocumentStatus, Tone> = {
  pending: "warning",
  processing: "info",
  indexed: "success",
  failed: "danger",
};

export function SeverityBadge({ value }: { value: Severity }) {
  return <Badge tone={SEVERITY_TONE[value]}>{humanize(value)}</Badge>;
}

export function IncidentStatusBadge({ value }: { value: IncidentStatus }) {
  return <Badge tone={INCIDENT_TONE[value]}>{humanize(value)}</Badge>;
}

export function WorkOrderStatusBadge({ value }: { value: WorkOrderStatus }) {
  return <Badge tone={WORK_ORDER_TONE[value]}>{humanize(value)}</Badge>;
}

export function PriorityBadge({ value }: { value: Priority }) {
  return <Badge tone={PRIORITY_TONE[value]}>{humanize(value)}</Badge>;
}

export function DocumentStatusBadge({ value }: { value: DocumentStatus }) {
  return <Badge tone={DOC_TONE[value]}>{humanize(value)}</Badge>;
}
