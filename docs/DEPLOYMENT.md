# Deployment

Two Vercel projects (frontend + backend) and one Neon Postgres database.

```
frontend (Vercel, Next.js)  ──►  backend (Vercel, Python/FastAPI)  ──►  Neon Postgres (pgvector)
```

---

## 1. Database — Neon (PostgreSQL + pgvector)

1. Create a project at https://neon.tech and a database (e.g. `shiftsathi`).
2. Copy the connection string. ShiftSathi expects the **asyncpg** driver and SSL:
   ```
   postgresql+asyncpg://USER:PASSWORD@ep-xxx.REGION.aws.neon.tech/neondb?ssl=require
   ```
   (Replace the scheme if Neon gives you `postgresql://`.)
3. Apply the schema from your machine (the migration also runs
   `CREATE EXTENSION IF NOT EXISTS vector` and creates the HNSW indexes):
   ```bash
   cd backend
   DATABASE_URL="postgresql+asyncpg://…?ssl=require" uv run alembic upgrade head
   ```
   If the Neon role cannot create extensions, enable `vector` once from the Neon
   SQL editor, then re-run the migration.

---

## 2. Backend — Vercel

1. Push the repo to GitHub.
2. **New Project → import repo → set Root Directory to `backend`.**
3. Vercel detects `vercel.json`:
   ```json
   {
     "builds": [{ "src": "api/index.py", "use": "@vercel/python" }],
     "routes": [{ "src": "/(.*)", "dest": "api/index.py" }]
   }
   ```
   The Python runtime installs dependencies from `backend/requirements.txt`;
   `api/index.py` exports the FastAPI `app`.
4. **Environment variables** (Project → Settings → Environment Variables):

   | Key | Value |
   |-----|-------|
   | `ENVIRONMENT` | `production` |
   | `SECRET_KEY` | long random string (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
   | `DATABASE_URL` | Neon asyncpg URL (`?ssl=require`) |
   | `CORS_ORIGINS` | your frontend origin, e.g. `https://shiftsathi.vercel.app` |
   | `AI_PROVIDER` | `gemini` (or `openai`/`mock`/`none`) |
   | `AI_API_KEY` | your provider key (OpenAI-compatible) |
   | `AI_BASE_URL` | `https://api.openai.com/v1` (or a compatible gateway) |
   | `CHAT_MODEL` / `EMBEDDING_MODEL` | e.g. `gpt-4o-mini` / `text-embedding-3-small` |
   | `GEMINI_API_KEY` | Google AI Studio key (when `AI_PROVIDER=gemini`) |
   | `GEMINI_CHAT_MODEL` / `GEMINI_EMBEDDING_MODEL` | e.g. `gemini-3.8-flash` / `gemini-embedding-001` |
   | `EMBEDDING_DIM` | `1536` (must match your embedding model & schema) |
   | `RETRIEVAL_TOP_K` / `RETRIEVAL_MIN_SCORE` | tune retrieval & abstention |
   | `RATE_LIMIT_ENABLED` / `RATE_LIMIT_AUTH_PER_MINUTE` / `RATE_LIMIT_AI_PER_MINUTE` | per-IP rate limits |

   > Production mode disables `/docs`, `/redoc` and `/openapi.json`, and enables
   > a serverless-friendly DB pool (prepared-statement caching off, for Neon’s
   > connection pooler).

5. Deploy. Verify: `https://<backend>.vercel.app/api/v1/health`.

### Re-exporting dependencies

If you change `backend/pyproject.toml`, refresh the Vercel lockfile:

```bash
cd backend
uv export --no-hashes --no-dev --format requirements-txt -o requirements.txt
```

---

## 3. Frontend — Vercel

1. **New Project → import the same repo → Root Directory `frontend`.**
2. **Environment variable:**
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<backend>.vercel.app/api/v1` |
3. Deploy (build command `next build`, output auto-detected).

Finally, set the backend’s `CORS_ORIGINS` to the deployed frontend origin and
redeploy the backend so the browser requests are allowed.

---

## 4. Post-deploy checklist

- [ ] `GET /api/v1/health` → `{"status":"ok"}`
- [ ] Register an organization from the deployed frontend (first user = admin)
- [ ] Invite a supervisor and a worker (Settings)
- [ ] Upload a PDF (Knowledge Base) → status becomes `indexed`
- [ ] Ask the assistant → cited answer, and an **abstain** for an unrelated question
- [ ] Report an incident → create & assign a work order → resolve → verify
- [ ] Overview dashboard reflects the real numbers

---

## Notes & limits

- Vercel serverless functions have a request size limit; uploads are capped at
  `MAX_UPLOAD_BYTES` (10 MB default), which is safe for the platform.
- PDF work happens in-process (pypdf); keep `MAX_PDF_PAGES`/`CHUNK_SIZE`
  reasonable to stay within the function’s execution budget.
- `AI_PROVIDER=mock` requires no key and is handy for a smoke demo, but produces
  only lexical (non-semantic) retrieval. Use a real provider in production.
- With `AI_PROVIDER=gemini`, embeddings are requested at `EMBEDDING_DIM` (1536)
  via Matryoshka `outputDimensionality` to match the `vector(1536)` column. If
  you switch embedding models you must keep `EMBEDDING_DIM` and the schema in
  sync and **reindex** all documents (Knowledge Base → reindex).
- Rate limiting is per serverless instance; for strict global limits put a
  gateway/WAF or Redis-backed limiter in front.
- Rotating `SECRET_KEY` invalidates all existing tokens (users simply sign in
  again).
