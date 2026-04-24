from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_session
from app.schemas.events import InteractionBatch, InteractionBatchResponse
from app.models.interactions import FeedImpression

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/interactions", response_model=InteractionBatchResponse, status_code=status.HTTP_201_CREATED)
async def ingest_interactions(
    body: InteractionBatch,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_session)
):
    user_id = current_user.id
    accepted = 0
    try:
        for evt in body.events:
            impression = FeedImpression(
                user_id=user_id,
                article_id=str(evt.article_id),
                created_at=evt.interacted_at or datetime.now(timezone.utc)
            )
            db.add(impression)
            accepted += 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed: {e}")
        raise HTTPException(status_code=500, detail="Database Error")
    return InteractionBatchResponse(accepted=accepted, rejected=len(body.events) - accepted)