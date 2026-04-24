from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base  # <--- CHANGE THIS LINE HERE!
import uuid

class OnboardingState(Base):
# ... rest of the code ...
"""POST /v1/interactions – direct database ingest.
Modified to work with SherrByte project structure.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_session
from app.schemas.events import InteractionBatch, InteractionBatchResponse
from app.models.interactions import FeedImpression  # Corrected Import

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/interactions",
    response_model=InteractionBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_interactions(
    body: InteractionBatch,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """Save interaction events directly to PostgreSQL."""
    user_id: uuid.UUID = current_user.id
    accepted = 0

    try:
        for evt in body.events:
            # We create a record for each impression
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
        logger.error(f"Failed to save interactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save interactions to database"
        )

    return InteractionBatchResponse(accepted=accepted, rejected=len(body.events) - accepted)