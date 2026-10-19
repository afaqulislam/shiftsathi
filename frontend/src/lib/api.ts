import { tokenStore } from "./token";
import type {
  AskResponse,
  AuditLog,
  Conversation,
  ConversationDetail,
  Dashboard,
  DocumentChunk,
  DocumentDetail,
  DocumentRecord,
  Incident,
  Me,
  Member,
  Paginated,
  TokenResponse,
  VerifiedKnowledge,
  WorkOrder,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(message: string, code: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = options;
  const finalHeaders = new Headers(headers);
  if (!(rest.body instanceof FormData)) {
    finalHeaders.set("Content-Type", "application/json");
  }
  if (auth) {
    const token = tokenStore.get();
    if (token) finalHeaders.set("Authorization", `Bearer ${token}`);
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...rest, headers: finalHeaders });
  } catch {
    throw new ApiError(
      "Cannot reach the ShiftSathi API. Is the backend running?",
      "network_error",
      0,
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const payload = text ? safeJson(text) : null;

  if (!res.ok) {
    const err = (
      payload as { error?: { code?: string; message?: string } } | null
    )?.error;
    if (res.status === 401 && auth) tokenStore.clear();
    throw new ApiError(
      err?.message ?? `Request failed (${res.status})`,
      err?.code ?? "http_error",
      res.status,
    );
  }
  return payload as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function qs(params: Record<string, string | number | boolean | undefined | null>) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export const api = {
  // --- health ---
  health() {
    return request<{ status: string; app: string; environment: string }>(
      "/health",
      { auth: false },
    );
  },

  // --- auth ---
  register(body: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }) {
    return request<TokenResponse>("/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify(body),
    });
  },
  login(body: { email: string; password: string }) {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify(body),
    });
  },
  me() {
    return request<Me>("/auth/me");
  },
  changePassword(body: {
    current_password: string;
    new_password: string;
  }) {
    return request<void>("/auth/password", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  members() {
    return request<Member[]>("/auth/members");
  },
  inviteMember(body: {
    full_name: string;
    email: string;
    password: string;
    role: string;
  }) {
    return request<Member>("/auth/members", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  changeRole(userId: string, role: string) {
    return request<Member>(`/auth/members/${userId}/role${qs({ role })}`, {
      method: "PATCH",
    });
  },

  // --- dashboard ---
  dashboard() {
    return request<Dashboard>("/dashboard");
  },

  // --- documents ---
  documents(params: {
    status?: string;
    search?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    return request<Paginated<DocumentRecord>>(`/documents${qs(params)}`);
  },
  document(id: string) {
    return request<DocumentDetail>(`/documents/${id}`);
  },
  documentChunks(id: string, params: { limit?: number; offset?: number } = {}) {
    return request<Paginated<DocumentChunk>>(
      `/documents/${id}/chunks${qs(params)}`,
    );
  },
  uploadDocument(file: File, title?: string) {
    const form = new FormData();
    form.append("file", file);
    if (title) form.append("title", title);
    return request<DocumentRecord>("/documents", { method: "POST", body: form });
  },
  reindexDocument(id: string, file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentRecord>(`/documents/${id}/reindex`, {
      method: "POST",
      body: form,
    });
  },
  deleteDocument(id: string) {
    return request<void>(`/documents/${id}`, { method: "DELETE" });
  },

  // --- chat ---
  ask(question: string, conversationId?: string | null) {
    return request<AskResponse>("/chat/ask", {
      method: "POST",
      body: JSON.stringify({
        question,
        conversation_id: conversationId ?? null,
      }),
    });
  },
  conversations() {
    return request<{ items: Conversation[] }>("/chat/conversations");
  },
  conversation(id: string) {
    return request<ConversationDetail>(`/chat/conversations/${id}`);
  },
  deleteConversation(id: string) {
    return request<void>(`/chat/conversations/${id}`, { method: "DELETE" });
  },

  // --- incidents ---
  incidents(params: {
    status?: string;
    severity?: string;
    machine?: string;
    search?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    return request<Paginated<Incident>>(`/incidents${qs(params)}`);
  },
  incident(id: string) {
    return request<Incident>(`/incidents/${id}`);
  },
  createIncident(body: {
    title: string;
    description?: string;
    machine?: string | null;
    severity?: string;
  }) {
    return request<Incident>("/incidents", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateIncident(id: string, body: Record<string, unknown>) {
    return request<Incident>(`/incidents/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },

  // --- work orders ---
  workOrders(params: {
    status?: string;
    priority?: string;
    assignee_id?: string;
    incident_id?: string;
    machine?: string;
    search?: string;
    overdue_only?: boolean;
    limit?: number;
    offset?: number;
  } = {}) {
    return request<Paginated<WorkOrder>>(`/work-orders${qs(params)}`);
  },
  workOrder(id: string) {
    return request<WorkOrder>(`/work-orders/${id}`);
  },
  createWorkOrder(body: Record<string, unknown>) {
    return request<WorkOrder>("/work-orders", {
      method: "POST",
      body: JSON.stringify(body),
    });
  },
  updateWorkOrder(id: string, body: Record<string, unknown>) {
    return request<WorkOrder>(`/work-orders/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  changeWorkOrderStatus(
    id: string,
    status: string,
    resolutionNotes?: string,
  ) {
    return request<WorkOrder>(`/work-orders/${id}/status`, {
      method: "POST",
      body: JSON.stringify({
        status,
        resolution_notes: resolutionNotes ?? null,
      }),
    });
  },
  verifyWorkOrder(id: string, verified: boolean) {
    return request<WorkOrder>(
      `/work-orders/${id}/verify${qs({ verified })}`,
      { method: "POST" },
    );
  },

  // --- verified knowledge ---
  verifiedKnowledge(params: {
    search?: string;
    machine?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    return request<Paginated<VerifiedKnowledge>>(
      `/verified-knowledge${qs(params)}`,
    );
  },
  verifiedKnowledgeItem(id: string) {
    return request<VerifiedKnowledge>(`/verified-knowledge/${id}`);
  },

  // --- activity ---
  activity(params: {
    entity_type?: string;
    action?: string;
    limit?: number;
    offset?: number;
  } = {}) {
    return request<Paginated<AuditLog>>(`/activity${qs(params)}`);
  },
};
