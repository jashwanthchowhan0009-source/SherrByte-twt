from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


EventType = Literal[
    "open", "impression", "dwell", "scroll",
    "save", "share", "skip", "hide", "mute_source"
]

POSITIVE_EVENTS = {"open", "dwell", "save", "share"}
NEGATIVE_EVENTS = {"skip", "hide", "mute_source"}


class InteractionEvent(BaseModel):
    article_id: uuid.UUID
    event_type: EventType
    dwell_ms: int = Field(default=0, ge=0, le=3_600_000)
    scroll_pct: int = Field(default=0, ge=0, le=100)
    source_id: Optional[uuid.UUID] = None
    interacted_at: Optional[datetime] = None


class InteractionBatch(BaseModel):
    events: list[InteractionEvent] = Field(min_length=1, max_length=50)


class InteractionBatchResponse(BaseModel):
    accepted: int
    rejected: int