# Vercel deployments are ephemeral and read-only outside /tmp. Any filesystem
# caching must therefore stay within the OS temp directory.
import tempfile
from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_SCHEME = "postgresql+asyncpg"
_SYNC_SCHEMES = {
    "postgres",
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
}


def normalize_database_url(url: str) -> str:
    """Coerce any Postgres URL into one the async engine understands.

    Neon (and most dashboards) hand out ``postgresql://…?sslmode=require``,
    which targets the sync driver and uses libpq query params. We rewrite the
    scheme to ``postgresql+asyncpg`` and translate ``sslmode`` -> ``ssl`` (asyncpg
    does not understand ``sslmode`` or ``channel_binding``).
    """
    parts = urlsplit(url)
    scheme = _ASYNC_SCHEME if parts.scheme in _SYNC_SCHEMES else parts.scheme

    query = dict(parse_qsl(parts.query))
    if "sslmode" in query:
        sslmode = query.pop("sslmode")
        query.pop("ssl", None)
        query["ssl"] = (
            "require"
            if sslmode in ("require", "verify-ca", "verify-full", "prefer")
            else sslmode
        )
    query.pop("channel_binding", None)

    return urlunsplit(
        (scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Application ---
    APP_NAME: str = "ShiftSathi API"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # --- Security ---
    # SECRET_KEY must be provided in production. A dev default is generated so
    # local setup works, but tokens are invalidated whenever it changes.
    SECRET_KEY: str = "dev-insecure-change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    ALGORITHM: str = "HS256"

    # --- API docs ---
    # When left unset, interactive docs (/docs, /redoc, /openapi.json) follow
    # the environment: enabled outside production, disabled in production.
    # Set ENABLE_DOCS=true to expose them on a production deployment.
    ENABLE_DOCS: bool | None = None

    # --- Database ---
    # Neon PostgreSQL connection string, e.g.
    # postgresql+asyncpg://user:pass@host/db?ssl=require
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5433/shiftsathi"
    )
    DB_ECHO: bool = False

    # --- CORS ---
    # Comma separated list of allowed origins for the frontend.
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- AI provider ---
    # Provider implementation: "openai" (any OpenAI-compatible endpoint),
    # "gemini" (Google Generative Language API), "mock" (deterministic offline
    # provider used for tests / no-key demos), or "none".
    AI_PROVIDER: Literal["openai", "gemini", "mock", "none"] = "mock"
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    CHAT_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    AI_TIMEOUT_SECONDS: float = 60.0

    # --- Gemini (used when AI_PROVIDER=gemini) ---
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_CHAT_MODEL: str = "gemini-3.8-flash"
    # gemini-embedding-001 supports Matryoshka truncation via outputDimensionality,
    # so we request EMBEDDING_DIM to stay compatible with the vector(1536) schema.
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # --- Retrieval ---
    RETRIEVAL_TOP_K: int = 6
    # Minimum cosine similarity (0-1) required before answering. Below this the
    # assistant abstains instead of guessing.
    RETRIEVAL_MIN_SCORE: float = 0.25
    MAX_QUESTION_LENGTH: int = 2000

    # --- Document ingestion ---
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB, safe for serverless
    MAX_PDF_PAGES: int = 200
    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 150

    # --- Rate limiting (in-process, per client IP) ---
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MINUTE: int = 12
    RATE_LIMIT_AI_PER_MINUTE: int = 20

    # --- Redis (optional) ---
    # When set, rate limiting is enforced globally through Redis (e.g. Upstash:
    # rediss://default:password@host:6379). When empty, an in-process limiter is
    # used, which is only per-instance (fine for local dev / single node).
    REDIS_URL: str = ""

    UPLOAD_TMP_DIR: str = Field(
        default_factory=lambda: tempfile.gettempdir()
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_db_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def docs_enabled(self) -> bool:
        return self.ENABLE_DOCS if self.ENABLE_DOCS is not None else not self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
