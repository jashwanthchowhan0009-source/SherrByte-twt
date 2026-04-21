"""Redis client — used for LLM response caching and (later) event streams.

Lazy-initialized singleton. If REDIS_URL is empty (dev mode), all cache ops
become no-ops so callers never need to branch on "redis is configured".
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis_async

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

_client: redis_async.Redis | None = None


def _get_client() -> redis_async.Redis | None:
    global _client
    if not settings.redis_url:
        return None
    if _client is None:
        _client = redis_async.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
    return _client


async def cache_get_json(key: str) -> dict[str, Any] | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except Exception as e:
        log.warning("redis_get_failed", key=key, error=str(e))
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def cache_set_json(
    key: str, value: dict[str, Any], ttl_seconds: int = 86_400
) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as e:
        log.warning("redis_set_failed", key=key, error=str(e))


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
