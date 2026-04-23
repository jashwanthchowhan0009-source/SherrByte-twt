"""Event drain worker — drains Redis stream → Postgres.

Run as a continuous process on Fly.io OR via GitHub Actions cron (every 5 min).

Usage:
  python -m app.workers.event_drain          # continuous loop
  python -m app.workers.event_drain --once   # single pass (for cron)
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid

logger = logging.getLogger(__name__)

POSITIVE_EVENTS   = {"open", "save", "share", "dwell"}
DRAIN_INTERVAL_S  = 10


async def _side_effects(events_written: list[dict]) -> None:
    """Update short-term profile vectors after positive events."""
    from app.db.session import SessionLocal
    from app.services.profile_vectors import update_short_term
    from sqlalchemy import text

    pos = [e for e in events_written if e["event_type"] in POSITIVE_EVENTS]
    if not pos:
        return

    async with SessionLocal() as db:
        for evt in pos:
            row = await db.execute(
                text("SELECT embedding FROM article_embeddings WHERE article_id = :aid LIMIT 1"),
                {"aid": evt["article_id"]},
            )
            result = row.fetchone()
            if result and result[0]:
                try:
                    await update_short_term(
                        user_id=uuid.UUID(str(evt["user_id"])),
                        article_embedding=list(result[0]),
                        db=db,
                    )
                except Exception:
                    logger.warning("Short-term vector update failed", exc_info=True)


async def run_once() -> int:
    from app.services.event_buffer import drain_stream_to_db
    n = await drain_stream_to_db(batch_size=200)
    if n > 0:
        logger.info("Drained %d events", n)
    return n


async def run_continuous() -> None:
    from app.services.event_buffer import ensure_consumer_group
    await ensure_consumer_group()
    logger.info("Event drain worker started")
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("Drain iteration error")
        await asyncio.sleep(DRAIN_INTERVAL_S)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if "--once" in sys.argv:
        asyncio.run(run_once())
    else:
        asyncio.run(run_continuous())
