"""Nightly affinity recompute worker.

Runs at 01:00 IST (19:30 UTC) for all users active in the last 24h.
Recalculates implicit topic scores + long-term profile vectors.

GitHub Actions cron: '30 19 * * *'
Usage: python -m app.workers.recompute_affinity
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def run() -> None:
    from app.db.session import SessionLocal
    from app.services.affinity import recompute_implicit
    from app.services.profile_vectors import recompute_long_term
    from sqlalchemy import text

    async with SessionLocal() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        rows   = await db.execute(
            text("SELECT DISTINCT user_id FROM user_interactions WHERE interacted_at >= :cutoff"),
            {"cutoff": cutoff},
        )
        active_users = [r[0] for r in rows]

    logger.info("Recomputing affinity for %d active users", len(active_users))

    for i, uid in enumerate(active_users):
        async with SessionLocal() as db:
            try:
                await recompute_implicit(uid, db)
                await recompute_long_term(uid, db)
            except Exception:
                logger.warning("Failed for user %s", uid, exc_info=True)
        if i % 50 == 0:
            logger.info("  %d/%d done", i + 1, len(active_users))

    logger.info("Nightly recompute complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run())
