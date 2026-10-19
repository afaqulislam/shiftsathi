"""Test fixtures.

Strategy:
* A dedicated ``shiftsathi_test`` database is created for the test session and
  the real Alembic migrations are applied to it (so migrations are exercised).
* Each test runs inside an outer transaction that is rolled back afterwards, so
  tests are isolated even though the application layer calls ``commit()``
  (we bind the session with ``join_transaction_mode="create_savepoint"``).
* The AI provider is forced to the deterministic ``mock`` implementation so no
  network calls or API keys are required.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

BACKEND_ROOT = Path(__file__).resolve().parent.parent

ADMIN_DSN = "postgresql://postgres:postgres@localhost:5433/shiftsathi"
TEST_DB = "shiftsathi_test"
TEST_DSN = f"postgresql://postgres:postgres@localhost:5433/{TEST_DB}"
TEST_ASYNC_URL = f"postgresql+asyncpg://postgres:postgres@localhost:5433/{TEST_DB}"

# Database availability flag: tests that need Postgres are skipped otherwise.
os.environ.setdefault("AI_PROVIDER", "mock")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdefghijklmnop")


async def _database_available() -> bool:
    try:
        conn = await asyncpg.connect(ADMIN_DSN, timeout=5)
    except Exception:  # noqa: BLE001
        return False
    await conn.close()
    return True


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: requires PostgreSQL")


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def _prepared_database() -> bool:
    """Create the test DB and apply migrations once per session."""
    if not await _database_available():
        return False

    admin = await asyncpg.connect(ADMIN_DSN)
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{TEST_DB}"')
    finally:
        await admin.close()

    conn = await asyncpg.connect(TEST_DSN)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await conn.close()

    env = {**os.environ, "DATABASE_URL": TEST_ASYNC_URL, "ENVIRONMENT": "test"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic upgrade failed:\n{result.stderr}\n{result.stdout}")
    return True


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine(_prepared_database: bool):
    if not _prepared_database:
        pytest.skip("PostgreSQL test database is not available")
    engine = create_async_engine(TEST_ASYNC_URL, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(db_engine) -> AsyncSession:
    """A session bound to a transaction that is rolled back after each test."""
    async with db_engine.connect() as connection:
        trans = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session: AsyncSession) -> AsyncClient:
    # Import after env vars are set so settings pick up test values.
    from app.db.base import get_db
    from app.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_PASSWORD = "worker1234"


async def register_account(
    client: AsyncClient,
    *,
    org_name: str,
    email: str,
    full_name: str = "Test Admin",
    password: str = DEFAULT_PASSWORD,
):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": org_name,
            "full_name": full_name,
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def login(client: AsyncClient, email: str, password: str = DEFAULT_PASSWORD):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def make_pdf(pages: list[str]) -> bytes:
    """Build a real multi-page PDF using reportlab for ingestion tests."""
    import io

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    for text in pages:
        y = 720
        for line in text.splitlines():
            c.drawString(72, y, line)
            y -= 18
        c.showPage()
    c.save()
    return buffer.getvalue()
