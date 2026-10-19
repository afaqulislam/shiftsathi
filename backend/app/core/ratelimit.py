"""Rate limiting for sensitive endpoints (auth + AI).

Two backends, chosen automatically:

* **Redis** (when ``REDIS_URL`` is set) — a fixed-window counter shared across
  all instances, which is what you want in production behind a load balancer /
  serverless deployment. Works with Upstash or any Redis-compatible endpoint.
* **In-process** fallback — a sliding-window counter keyed by ``bucket:ip``. No
  dependencies, but the effective limit is *per instance*. Used for local dev,
  tests, and single-node deployments.

If Redis is configured but temporarily unreachable, we log and fall back to the
in-process limiter rather than failing the request.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

import redis.asyncio as aioredis
from fastapi import Request

from app.core.config import settings
from app.core.errors import RateLimitError

logger = logging.getLogger("shiftsathi.ratelimit")

_WINDOW_SECONDS = 60.0


class SlidingWindowLimiter:
    """Dependency-free in-process fallback."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > _WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()

_redis_client: aioredis.Redis | None = None
_redis_lock = threading.Lock()


def get_redis() -> aioredis.Redis | None:
    """Lazily build the Redis client. Returns ``None`` when not configured."""
    global _redis_client
    if not settings.REDIS_URL:
        return None
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                _redis_client = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:  # noqa: BLE001
            logger.warning("Failed to close Redis client", exc_info=True)
        finally:
            _redis_client = None


async def _allow_via_redis(client: aioredis.Redis, key: str, limit: int) -> bool:
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, int(_WINDOW_SECONDS))
    return int(count) <= limit


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_limit(bucket: str, request: Request) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return
    limit = {
        "auth": settings.RATE_LIMIT_AUTH_PER_MINUTE,
        "ai": settings.RATE_LIMIT_AI_PER_MINUTE,
    }.get(bucket, 0)
    if limit <= 0:
        return

    ip = _client_ip(request)
    allowed: bool | None = None

    client = get_redis()
    if client is not None:
        try:
            allowed = await _allow_via_redis(client, f"rl:{bucket}:{ip}", limit)
        except Exception:  # noqa: BLE001
            logger.warning(
                "Redis rate limiter unavailable; using in-process fallback",
                exc_info=True,
            )
            allowed = None

    if allowed is None:
        allowed = limiter.allow(f"{bucket}:{ip}", limit)

    if not allowed:
        raise RateLimitError(
            "Too many requests. Please slow down and try again shortly."
        )


def rate_limit(bucket: str):
    """Build a FastAPI dependency enforcing the per-minute limit for ``bucket``.

    Settings are resolved at request time so tests can toggle them.
    """

    async def dependency(request: Request) -> None:
        await enforce_limit(bucket, request)

    return dependency
