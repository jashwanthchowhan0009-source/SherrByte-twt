"""Hybrid recommendation scorer.

Score formula:
  final = topic_affinity * 0.40
        + content_sim    * 0.25   (cosine of user vec vs article vec)
        + freshness      * 0.20   (exponential decay, half-life 12h)
        + engagement     * 0.10   (global CTR)
        + serendipity    * 0.05   (random floor for 10% of articles)

Cold-start path (< 5 interactions):
  - topic_affinity weight bumped to 0.55, freshness to 0.40
  - content_sim dropped to 0.00 (no profile vector yet)
  - 15% articles picked randomly for exploration (ε-greedy)
"""
from __future__ import annotations

import math
import random
import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interactions import (
    FeedImpression, UserProfileVector, UserTopicAffinity
)

COLD_START_THRESHOLD = 5
FRESHNESS_HALFLIFE_HOURS = 12.0

W_WARM  = dict(topic=0.40, content=0.25, fresh=0.20, engage=0.10, seren=0.05)
W_COLD  = dict(topic=0.55, content=0.00, fresh=0.40, engage=0.05, seren=0.00)


def _freshness(published_at: Optional[datetime]) -> float:
    if not published_at:
        return 0.3
    now = datetime.now(timezone.utc)
    age_h = (now - published_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    return math.exp(-age_h * math.log(2) / FRESHNESS_HALFLIFE_HOURS)


def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


async def _load_affinity(uid: uuid.UUID, db: AsyncSession) -> dict[str, float]:
    rows = await db.execute(
        select(UserTopicAffinity).where(UserTopicAffinity.user_id == uid)
    )
    return {r.topic_slug: r.combined_score for r in rows.scalars()}


async def _load_profile(uid: uuid.UUID, db: AsyncSession) -> tuple[Optional[list[float]], int]:
    row = await db.get(UserProfileVector, uid)
    if not row:
        return None, 0
    vec = list(row.short_term_vec or row.long_term_vec or [])
    return (vec if vec else None), (row.interaction_cnt or 0)


async def _seen(uid: uuid.UUID, db: AsyncSession) -> set[uuid.UUID]:
    rows = await db.execute(
        select(FeedImpression.article_id).where(FeedImpression.user_id == uid)
    )
    return {r for r in rows.scalars()}


async def score_articles(
    user_id: uuid.UUID,
    candidates: list[dict],
    db: AsyncSession,
    limit: int = 30,
) -> list[dict]:
    affinity = await _load_affinity(user_id, db)
    profile_vec, interaction_cnt = await _load_profile(user_id, db)
    seen = await _seen(user_id, db)

    is_cold = interaction_cnt < COLD_START_THRESHOLD
    w = W_COLD if is_cold else W_WARM

    scored = []
    for art in candidates:
        if art["id"] in seen:
            continue

        topic_score   = affinity.get(art.get("micro_topic") or art.get("category") or "", 0.0)
        content_score = _cosine(profile_vec, art["embedding"]) if (not is_cold and profile_vec and art.get("embedding")) else 0.0
        fresh_score   = _freshness(art.get("published_at"))
        engage_score  = min(art.get("ctr", 0.0), 1.0)
        seren         = w["seren"] if random.random() < 0.10 else 0.0

        final = (
            w["topic"]   * topic_score
            + w["content"] * content_score
            + w["fresh"]   * fresh_score
            + w["engage"]  * engage_score
            + seren
        )
        scored.append({**art, "relevance_score": round(final, 4)})

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)

    # ε-greedy exploration for cold-start users
    if is_cold:
        explore_n = max(1, int(limit * 0.15))
        pool = [a for a in candidates if a["id"] not in seen and a not in scored[:limit]]
        random.shuffle(pool)
        for a in pool[:explore_n]:
            a["relevance_score"] = -1.0
            scored.append(a)

    return scored[:limit]
