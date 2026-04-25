from __future__ import annotations
import logging, uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from app.deps import get_current_user
from app.schemas.events import InteractionBatch, InteractionBatchResponse
from app.services.event_buffer import publish_events

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/interactions", response_model=InteractionBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_interactions(body: InteractionBatch, current_user=Depends(get_current_user)):
    user_id: uuid.UUID = current_user.id
    events = [{"article_id": str(e.article_id), "event_type": e.event_type,
               "dwell_ms": e.dwell_ms, "scroll_pct": e.scroll_pct,
               "source_id": str(e.source_id) if e.source_id else "",
               "interacted_at": (e.interacted_at or datetime.now(timezone.utc)).isoformat()}
              for e in body.events]
    accepted = await publish_events(user_id, events)
    if accepted == 0 and events:
        raise HTTPException(status_code=503, detail="Event buffer unavailable")
    return InteractionBatchResponse(accepted=accepted, rejected=len(events)-accepted)