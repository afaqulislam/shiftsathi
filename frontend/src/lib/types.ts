export type Role = "admin" | "supervisor" | "worker";

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed";
export type Severity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "investigating" | "resolved" | "closed";
export type WorkOrderStatus =
  | "open"
  | "assigned"
  | "in_progress"
  | "resolved"
  | "closed";
export type Priority = "low" | "medium" | "high" | "urgent";
export type KnowledgeSource = "verified_resolution" | "document";

export interface UserPublic {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  is_demo: boolean;
  created_at: string;
}

export interface Me {
  user: UserPublic;
  organization: Organization;
  role: Role;
}

export interface Member {
  user: UserPublic;
  role: Role;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface DocumentRecord {
  id: string;
  title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  page_count: number;
  status: DocumentStatus;
  error_message: string | null;
  checksum: string;
  uploaded_by: string | null;
  created_at: string;
  indexed_at: string | null;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  page_number: number | null;
  content: string;
  token_count: number;
  has_embedding: boolean;
}

export interface DocumentDetail {
  document: DocumentRecord;
  chunk_count: number;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  machine: string | null;
  severity: Severity;
  status: IncidentStatus;
  reported_by: string | null;
  resolution_notes: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface AssigneeSummary {
  id: string;
  full_name: string;
  email: string;
}

export interface WorkOrder {
  id: string;
  incident_id: string | null;
  title: string;
  description: string;
  machine: string | null;
  priority: Priority;
  status: WorkOrderStatus;
  assignee_id: string | null;
  assignee: AssigneeSummary | null;
  created_by: string | null;
  due_date: string | null;
  resolution_notes: string | null;
  is_verified: boolean;
  verified_by: string | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}

export interface Citation {
  index: number;
  source_type: KnowledgeSource;
  document_id: string | null;
  document_title: string;
  page_number: number | null;
  snippet: string;
  score: number;
}

export interface AskResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  insufficient_evidence: boolean;
  provider: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: ChatMessage[];
}

export interface VerifiedKnowledge {
  id: string;
  work_order_id: string | null;
  incident_id: string | null;
  title: string;
  machine: string | null;
  content: string;
  approved_by: string | null;
  approved_at: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  actor_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}

export interface DashboardMetrics {
  open_incidents: number;
  active_work_orders: number;
  overdue_work_orders: number;
  resolved_last_7_days: number;
  pending_approvals: number;
  verified_knowledge_count: number;
  documents: {
    indexed: number;
    processing: number;
    pending: number;
    failed: number;
  };
  incidents_by_severity: Record<string, number>;
  work_orders_by_status: Record<string, number>;
}

export interface Dashboard {
  metrics: DashboardMetrics;
  recent_incidents: Incident[];
  recent_work_orders: WorkOrder[];
  recent_activity: AuditLog[];
}
