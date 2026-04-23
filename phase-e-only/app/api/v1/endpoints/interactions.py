"""POST /v1/interactions — batch event ingest.

Pushes to Redis Streams (sub-5ms). DB write is async via drain worker.
Accepts up to 50 events per request.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import get_current_user
from app.schemas.events import InteractionBatch, InteractionBatchResponse
from app.services.event_buffer import publish_events

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/interactions",
    response_model=InteractionBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_interactions(
    body: InteractionBatch,
    current_user=Depends(get_current_user),
):
    """Accept interaction events and enqueue to Redis Streams."""
    user_id: uuid.UUID = current_user.id

    events = [
        {
            "article_id":    str(evt.article_id),
            "event_type":    evt.event_type,
            "dwell_ms":      evt.dwell_ms,
            "scroll_pct":    evt.scroll_pct,
            "source_id":     str(evt.source_id) if evt.source_id else "",
            "interacted_at": (evt.interacted_at or datetime.now(timezone.utc)).isoformat(),
        }
        for evt in body.events
    ]

    accepted = await publish_events(user_id, events)
    rejected = len(events) - accepted

    if accepted == 0 and events:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Event buffer unavailable — try again shortly",
        )

    return InteractionBatchResponse(accepted=accepted, rejected=rejected)
