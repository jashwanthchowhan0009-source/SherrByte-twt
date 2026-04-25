from __future__ import annotations
import uuid, logging
from datetime import datetime, timezone
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.interactions import UserProfileVector

logger = logging.getLogger(__name__)
EMA_ALPHA = 0.30

def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v

async def update_short_term(user_id: uuid.UUID, article_embedding: list[float], db: AsyncSession) -> None:
    new_vec = np.array(article_embedding, dtype=np.float32)
    row = await db.get(UserProfileVector, user_id)
    if row is None:
        db.add(UserProfileVector(user_id=user_id, short_term_vec=new_vec.tolist(), interaction_cnt=1, updated_at=datetime.now(timezone.utc)))
    else:
        if row.short_term_vec:
            old = np.array(row.short_term_vec, dtype=np.float32)
            updated = _norm(EMA_ALPHA * new_vec + (1 - EMA_ALPHA) * old)
        else:
            updated = new_vec
        row.short_term_vec = updated.tolist()
        row.interaction_cnt = (row.interaction_cnt or 0) + 1
        row.updated_at = datetime.now(timezone.utc)
    await db.commit()

async def recompute_long_term(user_id: uuid.UUID, db: AsyncSession, lookback_days: int = 90) -> None:
    rows = await db.execute(text("SELECT ae.embedding FROM user_interactions ui JOIN article_embeddings ae ON ae.article_id = ui.article_id WHERE ui.user_id = :uid AND ui.event_type IN ('open', 'save', 'share', 'dwell') ORDER BY ui.interacted_at DESC LIMIT 500"), {"uid": user_id})
    embeddings = [np.array(r[0], dtype=np.float32) for r in rows if r[0]]
    if not embeddings:
        return
    mean_vec = _norm(np.mean(embeddings, axis=0))
    row = await db.get(UserProfileVector, user_id)
    if row:
        row.long_term_vec = mean_vec.tolist()
        row.updated_at = datetime.now(timezone.utc)
    else:
        db.add(UserProfileVector(user_id=user_id, long_term_vec=mean_vec.tolist(), interaction_cnt=len(embeddings), updated_at=datetime.now(timezone.utc)))
    await db.commit()