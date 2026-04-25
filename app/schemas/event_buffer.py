"""Redis Streams event buffer.

Client → POST /v1/interactions → publish_events() → Redis Stream
Background drain worker → drain_stream_to_db() → Postgres

Keeps the API endpoint sub-5ms regardless of DB load.

Stream key : sherrbyte:events
Consumer group: db_writer
"""
from __future__ import annotations

import logging
import uuid
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
    """Push interaction events onto the Redis stream. Returns accepted count."""
    r = await _redis()
    accepted = 0
    try:
        pipe = r.pipeline()
        for evt in events:
            payload = {
                "user_id": str(user_id),
                "article_id": str(evt["article_id"]),
                "event_type": evt["event_type"],
                "dwell_ms": str(evt.get("dwell_ms", 0)),
                "scroll_pct": str(evt.get("scroll_pct", 0)),
                "source_id": str(evt.get("source_id", "")),
                "ts": evt.get("interacted_at") or datetime.now(timezone.utc).isoformat(),
            }
            pipe.xadd(STREAM_KEY, payload, maxlen=MAX_STREAM_LEN, approximate=True)
            accepted += 1
        await pipe.execute()
    except Exception:
        logger.exception("Redis stream publish failed")
    finally:
        await r.aclose()
    return accepted


async def ensure_consumer_group() -> None:
    """Idempotent — create consumer group if it doesn't exist."""
    r = await _redis()
    try:
        await r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Created consumer group %s", CONSUMER_GROUP)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    finally:
        await r.aclose()


async def drain_stream_to_db(batch_size: int = 200) -> int:
    """
    Read up to batch_size messages from stream → write to Postgres.
    Called by workers/event_drain.py. Returns count processed.
    """
    from app.db.session import SessionLocal
    from app.models.interactions import UserInteraction

    r = await _redis()
    processed = 0

    try:
        messages = await r.xreadgroup(
            groupname=CONSUMER_GROUP,
            consumername="drain_worker",
            streams={STREAM_KEY: ">"},
            count=batch_size,
            block=500,
        )
        if not messages:
            return 0

        rows = []
        ids_to_ack = []
        for msg_id, fields in messages[0][1]:
            try:
                rows.append(UserInteraction(
                    user_id=uuid.UUID(fields["user_id"]),
                    article_id=uuid.UUID(fields["article_id"]),
                    event_type=fields["event_type"],
                    dwell_ms=int(fields.get("dwell_ms", 0)),
                    scroll_pct=int(fields.get("scroll_pct", 0)),
                    source_id=uuid.UUID(fields["source_id"]) if fields.get("source_id") else None,
                    interacted_at=datetime.fromisoformat(fields["ts"]),
                ))
                ids_to_ack.append(msg_id)
            except Exception:
                logger.warning("Malformed event msg %s — skipping", msg_id, exc_info=True)

        async with SessionLocal() as session:
            session.add_all(rows)
            await session.commit()

        await r.xack(STREAM_KEY, CONSUMER_GROUP, *ids_to_ack)
        processed = len(rows)

    except Exception:
        logger.exception("Drain failed")
    finally:
        await r.aclose()

    return processed
