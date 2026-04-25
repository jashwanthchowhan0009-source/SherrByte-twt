from __future__ import annotations
import math, random, uuid
from datetime import datetime, timezone
from typing import Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.interactions import FeedImpression, UserProfileVector, UserTopicAffinity

COLD_START_THRESHOLD = 5
FRESHNESS_HALFLIFE_HOURS = 12.0
W_WARM = dict(topic=0.40, content=0.25, fresh=0.20, engage=0.10, seren=0.05)
W_COLD = dict(topic=0.55, content=0.00, fresh=0.40, engage=0.05, seren=0.00)

def _freshness(published_at: Optional[datetime]) -> float:
    if not published_at:
        return 0.3
    now = datetime.now(timezone.utc)
    age_h = (now - published_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600
    return math.exp(-age_h * math.log(2) / FRESHNESS_HALFLIFE_HOURS)

def _cosine(a, b):
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0

async def score_articles(user_id: uuid.UUID, candidates: list[dict], db: AsyncSession, limit: int = 30) -> list[dict]:
    rows = await db.execute(select(UserTopicAffinity).where(UserTopicAffinity.user_id == user_id))
    affinity = {r.topic_slug: r.combined_score for r in rows.scalars()}
    row = await db.get(UserProfileVector, user_id)
    profile_vec = list(row.short_term_vec or row.long_term_vec or []) if row else None
    interaction_cnt = row.interaction_cnt or 0 if row else 0
    seen_rows = await db.execute(select(FeedImpression.article_id).where(FeedImpression.user_id == user_id))
    seen = {r for r in seen_rows.scalars()}
    is_cold = interaction_cnt < COLD_START_THRESHOLD
    w = W_COLD if is_cold else W_WARM
    scored = []
    for art in candidates:
        if art["id"] in seen:
            continue
        topic_score = affinity.get(art.get("micro_topic") or art.get("category") or "", 0.0)
        content_score = _cosine(profile_vec, art["embedding"]) if (not is_cold and profile_vec and art.get("embedding")) else 0.0
        fresh_score = _freshness(art.get("published_at"))
        engage_score = min(art.get("ctr", 0.0), 1.0)
        seren = w["seren"] if random.random() < 0.10 else 0.0
        final = w["topic"] * topic_score + w["content"] * content_score + w["fresh"] * fresh_score + w["engage"] * engage_score + seren
        scored.append({**art, "relevance_score": round(final, 4)})
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:limit]