from __future__ import annotations
import logging, uuid
from datetime import datetime, timezone
from typing import Any
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)
STREAM_KEY = "sherrbyte:events"
CONSUMER_GROUP = "db_writer"
MAX_STREAM_LEN = 50_000

async def _redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)

async def publish_events(user_id: uuid.UUID, events: list[dict[str, Any]]) -> int:
    if not settings.redis_url:
        return len(events)
    r = await _redis()
    accepted = 0
    try:
        pipe = r.pipeline()
        for evt in events:
            payload = {"user_id": str(user_id), "article_id": str(evt["article_id"]), "event_type": evt["event_type"], "dwell_ms": str(evt.get("dwell_ms", 0)), "scroll_pct": str(evt.get("scroll_pct", 0)), "source_id": str(evt.get("source_id", "")), "ts": evt.get("interacted_at") or datetime.now(timezone.utc).isoformat()}
            pipe.xadd(STREAM_KEY, payload, maxlen=MAX_STREAM_LEN, approximate=True)
            accepted += 1
        await pipe.execute()
    except Exception:
        logger.exception("Redis stream publish failed")
        return len(events)
    finally:
        await r.aclose()
    return accepted

async def ensure_consumer_group() -> None:
    if not settings.redis_url:
        return
    r = await _redis()
    try:
        await r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    finally:
        await r.aclose()

async def drain_stream_to_db(batch_size: int = 200) -> int:
    return 0