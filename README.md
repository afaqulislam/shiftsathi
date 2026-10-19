# ShiftSathi

AI-grounded frontline operations assistant for factories and workshops.

ShiftSathi turns PDF manuals and verified fixes into a searchable, cited knowledge base and connects them to incidents, work orders, and verified resolutions. Answers are grounded in retrieved evidence and explicitly abstain when evidence is insufficient. All metrics and data access are scoped to the caller's organization.

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation and Local Setup](#installation-and-local-setup)
- [Environment Variables](#environment-variables)
- [Usage Guide](#usage-guide)
- [API Documentation](#api-documentation)
- [Database Design](#database-design)
- [AI, Retrieval & Citations](#ai-retrieval--citations)
- [Security & Privacy](#security--privacy)
- [Testing](#testing)
- [Deployment](#deployment)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

Frontline maintenance teams in workshops and factories often rely on scattered PDF manuals, tribal knowledge, WhatsApp messages, or paper logs. Critical fixes are lost when people leave, recurring issues lack traceability, and work gets duplicated. Without a single source of truth tied to incidents and work orders, troubleshooting is slow and inconsistent.

## The Solution

ShiftSathi provides an organization-scoped operations workspace that:
- Creates a cited, searchable knowledge base from uploaded PDFs and verified resolutions.
- Routes reported issues through structured incidents and work orders with role-based transitions.
- Captures verified solutions as durable, searchable knowledge entries.
- Surfaces real dashboard metrics from the database.

---

## Key Features

| Feature | Description | Who Uses It |
|---|---|---|
| AI Assistant (RAG) | Asks questions in English/phrases; returns grounded answers with citations (document, page, snippet, score) or explicit 'not enough evidence' abstention. Conversations persisted per user. | All members (role-scoped access) |
| Knowledge Base | Upload PDFs (supervisor/admin). Validates, checksum-deduplicates, chunks, embeds (pgvector), indexes per org. Tracks status (pending/processing/indexed/failed). | Admin/Supervisor |
| Incidents | Report incidents; supervisors manage transitions open → investigating → resolved → closed with validated state changes. | Any member reports; supervisors manage |
| Work Orders | Supervisors create/assign; assignees start/resolve with required notes; supervisors close and verify. | Supervisor/Worker |
| Verified Knowledge | Verifying a resolved work order creates a searchable knowledge entry linked to the original resolution. | Supervisor |
| Dashboard | Real DB-backed counts (open incidents, active/overdue work orders, pending approvals, documents by status, severity/status breakdowns, audit activity). | All members |
| Activity Feed | Org-scoped, filterable, paginated audit trail of consequential actions. | Members with access |
| Org Isolation & RBAC | Every query filtered by organization_id. Roles: admin, supervisor, worker. Finer rules in service layer. | System-wide |
| Security | Bcrypt password hashing, JWT (HS256), in-app password change, per-IP rate limiting on auth/AI endpoints, CORS, secure headers. | System-wide |

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Radix UI/shadcn, Lucide, React Hook Form + Zod, Sonner, Framer Motion | UI, routing, forms, validation, toasts |
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, python-jose, bcrypt, httpx, python-multipart | API, validation, ORM, migrations, auth, HTTP |
| Database | PostgreSQL + pgvector | Relational data + vector embeddings, HNSW indexes |
| AI/Embeddings | Pluggable: OpenAI-compatible, Google Gemini, deterministic mock, or none | Chat + embeddings (configurable) |
| Infra/Tooling | uv, ruff, pytest, Vercel (deployment config), Docker (local Postgres) | Dev tools, testing, deployment |

---

## Architecture

Request flow: Client (Next.js) → FastAPI (JWT Bearer) → Service layer (RBAC/org-scoped) → SQLAlchemy/asyncpg + pgvector. Auth context from token provides user/org/role. RAG: embed query → vector search (document chunks + verified knowledge, org-scoped, cosine) → filter by min score → grounded prompt with citations → LLM response → validate/persist.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for details.

---

## Prerequisites

- Node.js 18+ (tested with current setup; Next.js 14)
- npm (or pnpm/yarn)
- Python 3.12+
- PostgreSQL 16 with pgvector extension (local via Docker or managed like Neon)
- AI provider credentials if using real provider (Gemini/OpenAI-compatible). Mock works offline.

---

## Installation and Local Setup

### 1. Clone repository
`ash
git clone https://github.com/your-username/shiftsathi.git
cd shiftsathi
`
*(Adjust URL if different; actual remote not specified in repo.)*

### 2. Database (pgvector via Docker)
`ash
docker run --name shiftsathi-pg \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=shiftsathi \
  -p 5433:5432 -d pgvector/pgvector:pg16
`
Tests expect localhost:5433 with user/pass postgres; they create shiftsathi_test.

### 3. Backend
`ash
cd backend
# Create venv and install deps (uv recommended)
uv sync
cp .env.example .env  # fill values
uv run alembic upgrade head  # apply migrations + vector extension
uv run uvicorn app.main:app --reload --port 8000
`
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

### 4. Frontend
`ash
cd frontend
npm install
cp .env.example .env.local  # set NEXT_PUBLIC_API_BASE_URL
npm run dev
`
Open http://localhost:3000. Create workspace (becomes admin), upload PDF, ask assistant.

---

## Environment Variables

### Backend (.env)
| Variable | Purpose | Required | Default/Notes |
|---|---|---|---|
| ENVIRONMENT | App env | No | development |
| DEBUG | Debug mode | No | false |
| API_V1_PREFIX | API prefix | No | /api/v1 |
| SECRET_KEY | JWT signing key | Yes (prod) | set to long random string |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry | No | 720 |
| DATABASE_URL | Postgres async URL | Yes | postgresql+asyncpg://... |
| CORS_ORIGINS | Allowed origins (comma-separated) | No | http://localhost:3000 |
| AI_PROVIDER | openai/gemini/mock/none | No | mock |
| AI_API_KEY | OpenAI-compatible key | If provider=openai | - |
| AI_BASE_URL | Base URL | If provider=openai | https://api.openai.com/v1 |
| CHAT_MODEL/EMBEDDING_MODEL | Model names | If provider=openai | configurable |
| GEMINI_API_KEY | Gemini key | If provider=gemini | - |
| GEMINI_BASE_URL/CHAT_MODEL/EMBEDDING_MODEL | Gemini config | If provider=gemini | gemini-3.8-flash/gemini-embedding-001 |
| EMBEDDING_DIM | Vector dimension | Yes | 1536 (must match schema/model) |
| AI_TIMEOUT_SECONDS | Timeout | No | 60 |
| RATE_LIMIT_ENABLED | Per-IP limits | No | true |
| RATE_LIMIT_AUTH_PER_MINUTE | Auth limit | No | 12 |
| RATE_LIMIT_AI_PER_MINUTE | AI limit | No | 20 |
| REDIS_URL | Global rate limit (optional) | No | empty (in-process) |
| RETRIEVAL_TOP_K | Top results | No | 6 |
| RETRIEVAL_MIN_SCORE | Min cosine score (abstain if below) | No | 0.25 |
| MAX_QUESTION_LENGTH | Max question chars | No | 2000 |
| MAX_UPLOAD_BYTES | Max upload size | No | 10MB |
| MAX_PDF_PAGES | Max pages | No | 200 |
| CHUNK_SIZE/CHUNK_OVERLAP | Chunking | No | 900/150 |

### Frontend (.env.local)
| Variable | Purpose | Required | Notes |
|---|---|---|---|
| NEXT_PUBLIC_API_BASE_URL | Backend API base (include /api/v1) | Yes | http://localhost:8000/api/v1 |

---

## Usage Guide

1. **Register/Login**: Create account/org (first user becomes admin context). JWT stored in localStorage.
2. **Upload Documents** (Admin/Supervisor): Knowledge Base → Upload PDF. System validates, dedups by checksum, chunks, embeds, indexes. Status shows processing/indexed/failed.
3. **Ask Assistant**: Assistant page → ask question. Responses include citations (doc/page/snippet/score). If insufficient evidence, explicit abstention.
4. **Manage Incidents**: Report incident (any member). Supervisors transition states; resolved incidents may lead to work orders.
5. **Manage Work Orders**: Supervisor creates/assigns. Assignee marks in_progress/resolved with notes. Supervisor closes and verifies.
6. **Verified Knowledge**: Verification writes durable knowledge entry searchable via RAG.
7. **Monitor**: Dashboard shows real counts; Activity feed shows audit trail; Settings for password change.

---

## API Documentation

Base URL (local): http://localhost:8000/api/v1

Key routes (see pp/api/v1/routes/*):
- POST /auth/register, POST /auth/login, GET /auth/me, POST /auth/password/change
- GET/POST/PATCH/DELETE /documents, POST /documents/upload, GET /documents/{id}/chunks
- POST /chat/ask, GET /chat/conversations, GET /chat/conversations/{id}
- GET/POST/PATCH /incidents
- GET/POST/PATCH /work-orders, POST /work-orders/{id}/verify
- GET/POST /verified-knowledge
- GET /dashboard/overview, GET /activity, GET /health

Interactive docs: http://localhost:8000/docs (disabled in production). Schemas in pp/schemas/*.

---

## Database Design

PostgreSQL + pgvector. Core entities: organizations, users, memberships (org+role), documents, document_chunks (with embedding vector(1536), page, org-scoped), incidents, work_orders, erified_knowledge (with embeddings), conversations/messages (citations JSON), udit_logs (append-only). All data org-scoped. Migrations via Alembic (lembic/versions/7ad9f9f662f4_initial_schema.py creates extension, tables, indexes; HNSW index on embeddings).

---

## AI, Retrieval & Citations

- Provider abstraction (pp/services/ai/provider.py): OpenAI-compatible, Gemini (native REST), Mock (deterministic, offline), Null.
- Embeddings: vector(1536). Gemini uses Matryoshka outputDimensionality=1536.
- Retrieval: search document_chunks union erified_knowledge, org-scoped, cosine similarity, top-k (RETRIEVAL_TOP_K), filter by RETRIEVAL_MIN_SCORE → abstain if none meet threshold.
- Generation: grounded prompt with numbered evidence; answers must cite sources or abstain.
- Limitations: quality depends on provider/model, PDFs/chunking affect recall, abstention is conservative by design. Mock is lexical (not semantic) for testing.

---

## Security & Privacy

- RBAC + org isolation enforced in deps/services (every query filtered by org_id).
- Passwords hashed with bcrypt (12 rounds), max 72 bytes.
- JWT HS256 with configurable expiry; tokens invalidated if SECRET_KEY changes.
- Per-IP rate limiting (auth/AI), optional Redis for global limits.
- CORS restricted to configured origins.
- Upload validation (size/pages/type), checksum dedup.
- In-app password change, active user checks.
- API docs/redoc/openapi disabled in production.

---

## Testing

Framework: pytest + pytest-asyncio (asyncio mode auto). Tests require PostgreSQL (pgvector) on localhost:5433; they create shiftsathi_test, run Alembic migrations, use transactions with savepoints for isolation, force AI_PROVIDER=mock. 34 tests collected (auth/isolation, documents, operations, RAG).

Commands:
`ash
cd backend
uv run pytest           # run tests (skip gracefully if DB unavailable)
uv run pytest -v        # verbose
uv run ruff check app tests
`

Frontend:
`ash
cd frontend
npm run typecheck
npm run lint
`

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Typical: Neon (Postgres+pgvector) + Vercel backend (Python/FastAPI via vercel.json/api/index.py) + Vercel frontend (Next.js). Set env vars per environment (SECRET_KEY, DATABASE_URL, CORS_ORIGINS, AI_PROVIDER/keys). Apply migrations on DB. CORS must include frontend origin.

---

## Limitations

- Tests require local Postgres+pgvector (skipped without it).
- Real AI requires external API keys; mock is non-semantic.
- In-process rate limiter is per-instance (use Redis for multi-instance).
- PDF processing assumes text-based PDFs (images/OCR not implemented).
- No built-in file storage beyond DB metadata; chunks stored as text.
- No license specified in repo.

---

## Roadmap

- [ ] Add OCR support for scanned PDFs
- [ ] Expand AI provider options/config validation
- [ ] Enhance analytics/exporting
- [ ] Improve mobile responsiveness
- [ ] Add batch operations/workflows

---

## Contributing

1. Fork/branch, make changes.
2. Run lint/typecheck/tests.
3. Follow existing code style (ruff, TypeScript strict).
4. Submit PR with clear description.

---

## License

No license file found in repository. License not specified. Contact repository owner for usage/redistribution terms.

