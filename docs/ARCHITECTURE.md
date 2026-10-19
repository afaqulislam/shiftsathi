# Architecture

## Overview

```
┌────────────────────┐        HTTPS / JSON        ┌─────────────────────────┐
│  Next.js (Vercel)  │ ─────────────────────────► │  FastAPI (Vercel)       │
│  App Router + RSC  │   Bearer JWT in header     │  /api/v1/*              │
└────────────────────┘                            └───────────┬─────────────┘
        │  token in localStorage (client components)          │
        │                                                     │ async SQLAlchemy
        ▼                                                     ▼
   AuthProvider (lib/auth)                     ┌───────────────────────────────┐
   api client (lib/api)                        │  Services layer               │
                                                │  auth · document · rag ·      │
                                                │  incident · work_order ·      │
                                                │  dashboard · audit · ratelimit│
                                                └───────┬───────────────┬───────┘
                                                        │               │
                                        OpenAI or Gemini │         pgvector
                                                        ▼               ▼
                                            ┌────────────────┐  ┌──────────────────┐
                                            │ AI provider    │  │ PostgreSQL(Neon) │
                                            │ openai/gemini  │ │ + vector indexes │
                                            └────────────────┘  └──────────────────┘
```

## Request lifecycle & tenancy

1. **Auth** — `POST /auth/login` returns a short-lived HS256 JWT whose payload is
   `{sub, org, role, iat, exp}`. The frontend stores it in `localStorage` and
   sends `Authorization: Bearer …`.
2. **Context** — `get_current_context` decodes the token, loads the user,
   organization and membership, and produces a `CurrentContext`
   (`user`, `organization`, `role`, `user_id`, `organization_id`).
3. **RBAC** — dependencies `require_admin`, `require_supervisor`, `require_any`
   gate routes. Finer rules (e.g. workers may only update work orders assigned
   to them) live in the service layer.
4. **Isolation** — every query filters by `organization_id`. There is no route
   that reads data across organizations.

## Data model

| Table | Notes |
|-------|-------|
| `organizations` | tenant root; `slug`, `is_demo` |
| `users` | identity; email unique |
| `memberships` | `(user_id, organization_id)` → `role` |
| `documents` | uploaded PDFs; `checksum` (dedup), `status`, `page_count` |
| `document_chunks` | text + `embedding vector(1536)` + `page_number`, HNSW cosine index |
| `incidents` | status workflow, severity, machine, resolution notes |
| `work_orders` | status workflow, priority, assignee, `is_verified`, verification metadata |
| `verified_knowledge` | durable entries created when a work order is verified; also embedded for retrieval |
| `conversations` / `messages` | per-user chat history; assistant messages store citations JSON |
| `audit_logs` | append-only trail of significant mutations |

All timestamps use a Python-side `utcnow()` default so values are available on
the instance immediately after flush (avoids async lazy-load errors).

## RAG pipeline

```
question ──► embed ──► vector search (document_chunks + verified_knowledge)
                          │            org-scoped, cosine, top-k
                          ▼
                 filter score ≥ RETRIEVAL_MIN_SCORE  ──► no evidence ─► ABSTAIN
                          │                                              (honest)
                          ▼
        build grounded prompt (numbered evidence) ──► LLM ──► parse answer
                          │
                          ▼
        validate citations ──► persist message ──► return answer + citations
```

- The provider abstraction (`app/services/ai/provider.py`) exposes `embed` and
  `chat`. Implementations: `OpenAICompatibleProvider` (any OpenAI-compatible
  endpoint), `GeminiProvider` (Google Generative Language API — `embedContent` /
  `batchEmbedContents` / `generateContent`), deterministic `MockProvider`, and
  `NullProvider`.
- Gemini embeddings are requested at `EMBEDDING_DIM` (1536) via Matryoshka
  `outputDimensionality` so they fit the `vector(1536)` column; a dimension
  mismatch fails loudly rather than silently storing wrong-width vectors.
- **Abstention is first-class**: if no chunk clears the similarity threshold the
  assistant returns `insufficient_evidence: true` instead of guessing.
- Citations reference only evidence that was actually retrieved; the answer is
  never allowed to invent sources.

## Error contract

All failures share one shape:

```json
{ "error": { "code": "not_found", "message": "Document not found." } }
```

## Rate limiting

`app/core/ratelimit.py` provides a dependency-free sliding-window limiter keyed by
`bucket:client_ip`. `POST /auth/*` and `POST /chat/ask` are protected; limits are
configurable (`RATE_LIMIT_*`). State is per-process, so behind multiple instances
it is a best-effort guard — back it with Redis for strict global limits.

## Frontend conventions

- Route groups: `(auth)` for login/register, `(app)` for the authenticated
  shell (sidebar + guard).
- `AppShell` enforces the auth guard client-side and redirects to `/login`.
- `lib/api.ts` is the single typed gateway to the backend; `lib/use-async.ts`
  provides loading/error/reload for list pages.
- Design system: **Ethereal Glass** — OLED black, radial mesh background, glass
  “double-bezel” cards, accent `#0000FF`, Geist typography, cubic-bezier motion.
