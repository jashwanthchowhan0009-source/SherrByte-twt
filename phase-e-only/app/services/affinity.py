"""Affinity service — merges onboarding (explicit) + behavioral (implicit) signals.

combined = 0.6 * explicit_weight + 0.4 * implicit_score

Implicit score derived from interaction history:
  raw = Σ event_weights  (opens, dwell-time, saves, shares, minus skips/hides)
  implicit_score = sigmoid(raw / 5)
"""
from __future__ import annotations

import math
import uuid
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interactions import UserTopicAffinity

logger = logging.getLogger(__name__)

EVENT_WEIGHTS: dict[str, float] = {
    "open":        1.0,
    "dwell":       1.5,
    "save":        3.0,
    "share":       4.0,
    "scroll":      0.3,
    "impression":  0.0,
    "skip":       -1.0,
    "hide":       -4.0,
    "mute_source": -6.0,
}
DWELL_BONUS_PER_30S = 0.5
MAX_DWELL_BONUS     = 3.0


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x / 5))


async def seed_explicit_weights(
    user_id: uuid.UUID,
    topic_slugs: list[str],
    topic_pillar_map: dict[str, int],
    db: AsyncSession,
) -> None:
    """Seed explicit affinity rows from onboarding selections (weight = 1.0)."""
    for slug in topic_slugs:
        existing = await db.get(UserTopicAffinity, (user_id, slug))
        if existing:
            existing.explicit_weight = 1.0
            existing.combined_score  = max(existing.combined_score, 0.6)
        else:
            db.add(UserTopicAffinity(
                user_id=user_id,
                topic_slug=slug,
                pillar_id=topic_pillar_map.get(slug),
                explicit_weight=1.0,
                implicit_score=0.0,
                combined_score=0.6,
            ))
    await db.commit()
    logger.info("Seeded %d explicit weights for user %s", len(topic_slugs), user_id)


async def recompute_implicit(
    user_id: uuid.UUID,
    db: AsyncSession,
    lookback_days: int = 90,
) -> None:
    """Recompute implicit scores from raw interaction history (nightly)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    rows = await db.execute(text("""
        SELECT a.micro_topic, a.pillar_id, ui.event_type, ui.dwell_ms
        FROM user_interactions ui
        JOIN articles a ON a.id = ui.article_id
        WHERE ui.user_id = :uid
          AND ui.interacted_at >= :cutoff
          AND a.micro_topic IS NOT NULL
    """), {"uid": user_id, "cutoff": cutoff})

    topic_signals: dict[str, float] = {}
    topic_pillar:  dict[str, int]   = {}

    for micro_topic, pillar_id, event_type, dwell_ms in rows:
        base = EVENT_WEIGHTS.get(event_type, 0.0)
        if event_type == "dwell" and dwell_ms:
            base += min(dwell_ms / 30_000 * DWELL_BONUS_PER_30S, MAX_DWELL_BONUS)
        topic_signals[micro_topic] = topic_signals.get(micro_topic, 0.0) + base
        if pillar_id:
            topic_pillar[micro_topic] = pillar_id

    for slug, raw in topic_signals.items():
        impl = _sigmoid(raw)
        existing = await db.get(UserTopicAffinity, (user_id, slug))
        if existing:
            existing.implicit_score  = impl
            existing.combined_score  = 0.6 * existing.explicit_weight + 0.4 * impl
            existing.last_updated    = datetime.now(timezone.utc)
        else:
            db.add(UserTopicAffinity(
                user_id=user_id,
                topic_slug=slug,
                pillar_id=topic_pillar.get(slug),
                explicit_weight=0.0,
                implicit_score=impl,
                combined_score=0.4 * impl,
            ))

    await db.commit()
