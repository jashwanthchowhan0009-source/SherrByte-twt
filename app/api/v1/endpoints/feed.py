"""GET /v1/feed — personalised, cursor-paginated article stream.

Flow:
  1. Check onboarding (has user picked topics?)
  2. Fetch candidate articles from DB (unseen, last 7 days)
  3. Hybrid score (scorer.py)
  4. MMR re-rank for diversity (mmr.py)
  5. Inject trending articles every 5 slots
  6. Record impressions so articles aren't repeated next page
  7. Return cursor for next page
"""
from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_session
from app.models.interactions import FeedImpression, OnboardingState
from app.schemas.feed import FeedArticle, FeedResponse
from app.services.scorer import score_articles
from app.services.mmr import mmr_rerank, inject_trending

logger = logging.getLogger(__name__)
router = APIRouter()

CANDIDATE_POOL = 200


def _encode(dt: datetime) -> str:
    return base64.urlsafe_b64encode(dt.isoformat().encode()).decode()


def _decode(cursor: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(base64.urlsafe_b64decode(cursor).decode())
    except Exception:
        return None


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=30),
    pillar: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    user_id: uuid.UUID = current_user.id
    before_dt = _decode(cursor) if cursor else datetime.now(timezone.utc)

    ob = await db.get(OnboardingState, user_id)
    has_topics = ob and ob.step >= 1

    pillar_filter = "AND a.pillar_id = (SELECT id FROM pillars WHERE slug = :pillar)" if pillar else ""

    rows = await db.execute(text(f"""
        SELECT
            a.id, a.title, aa.summary_60w AS cached_summary,
            a.image_url, s.name AS source_name,
            a.language AS category, a.language AS micro_topic,
            a.pillar_id, a.published_at,
            COALESCE(aa.quality_score, 0.0) AS ctr,
            ae.embedding
        FROM articles a
        LEFT JOIN article_ai aa         ON aa.article_id = a.id
        LEFT JOIN article_embeddings ae ON ae.article_id = a.id
        LEFT JOIN sources s             ON s.id = a.source_id
        WHERE a.published_at < :before_dt
          AND a.published_at >= NOW() - INTERVAL '7 days'
          AND a.deleted_at IS NULL
          AND a.id NOT IN (
              SELECT article_id FROM feed_impressions WHERE user_id = :uid
          )
          {pillar_filter}
        ORDER BY a.published_at DESC
        LIMIT :pool
    """), {
        "before_dt": before_dt, "uid": user_id, "pool": CANDIDATE_POOL,
        **({"pillar": pillar} if pillar else {}),
    })

    candidates = [dict(r._mapping) for r in rows]
    if not candidates:
        return FeedResponse(articles=[], next_cursor=None, feed_type="fallback")

    # Score + rank
    if has_topics:
        scored    = await score_articles(user_id, candidates, db, limit=limit * 3)
        feed_type = "personalised"
    else:
        scored    = sorted(candidates, key=lambda x: x.get("published_at") or datetime.min, reverse=True)
        feed_type = "cold_start"

    reranked = mmr_rerank(scored, target_n=limit + 5)

    # Trending injection
    trending_rows = await db.execute(text("""
        SELECT a.id, a.title, aa.summary_60w AS cached_summary,
               a.image_url, s.name AS source_name,
               a.language AS category, a.language AS micro_topic,
               a.published_at, NULL AS embedding
        FROM articles a
        LEFT JOIN article_ai aa ON aa.article_id = a.id
        LEFT JOIN sources s     ON s.id = a.source_id
        WHERE a.published_at >= NOW() - INTERVAL '3 hours'
        ORDER BY COALESCE(aa.quality_score, 0) DESC
        LIMIT 5
    """))
    trending = [dict(r._mapping) for r in trending_rows]

    final = inject_trending(reranked[:limit], trending)[:limit]

    # Record impressions
    for art in final:
        await db.merge(FeedImpression(user_id=user_id, article_id=art["id"]))
    await db.commit()

    oldest_dt  = min((a.get("published_at") for a in final if a.get("published_at")), default=None)
    next_cursor = _encode(oldest_dt) if oldest_dt else None

    articles = [
        FeedArticle(
            id=a["id"], title=a.get("title") or "",
            cached_summary=a.get("cached_summary"),
            image_url=a.get("image_url"), source_name=a.get("source_name"),
            category=a.get("category"), micro_topic=a.get("micro_topic"),
            published_at=a.get("published_at"),
            is_trending=a.get("is_trending", False),
            relevance_score=a.get("relevance_score", 0.0),
        )
        for a in final
    ]
    return FeedResponse(articles=articles, next_cursor=next_cursor, feed_type=feed_type)
