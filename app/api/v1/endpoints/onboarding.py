"""Onboarding endpoints — topic picker + source opt-out.

Step 1: POST /v1/onboarding/topics        (min 5 slugs → unlocks feed)
Step 2: POST /v1/onboarding/source-optout (optional)
GET    /v1/onboarding/status              (poll current state)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_session
from app.models.interactions import OnboardingState
from app.schemas.feed import OnboardingStatus, SourceOptOut, TopicSelection
from app.services.affinity import seed_explicit_weights

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_or_create(uid: uuid.UUID, db: AsyncSession) -> OnboardingState:
    ob = await db.get(OnboardingState, uid)
    if not ob:
        ob = OnboardingState(user_id=uid, step=0, raw_selections={})
        db.add(ob)
        await db.commit()
        await db.refresh(ob)
    return ob


@router.post("/onboarding/topics", status_code=status.HTTP_200_OK)
async def set_topics(
    body: TopicSelection,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    uid: uuid.UUID = current_user.id

    # Validate slugs exist in taxonomy
    rows = await db.execute(
        text("SELECT slug, pillar_id FROM microtopics WHERE slug = ANY(:slugs)"),
        {"slugs": body.topic_slugs},
    )
    found = {r[0]: r[1] for r in rows}
    invalid = [s for s in body.topic_slugs if s not in found]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown topic slugs: {invalid[:5]}",
        )

    ob = await _get_or_create(uid, db)
    ob.step = max(ob.step, 1)
    ob.raw_selections = {**(ob.raw_selections or {}), "topics": body.topic_slugs}
    await db.commit()

    await seed_explicit_weights(uid, body.topic_slugs, found, db)
    return {"status": "ok", "topics_saved": len(body.topic_slugs)}


@router.post("/onboarding/source-optout", status_code=status.HTTP_200_OK)
async def set_source_optout(
    body: SourceOptOut,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    uid: uuid.UUID = current_user.id
    ob = await _get_or_create(uid, db)
    ob.step = max(ob.step, 2)
    ob.raw_selections = {
        **(ob.raw_selections or {}),
        "opted_out_sources": [str(s) for s in body.source_ids],
    }
    ob.completed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok", "opted_out": len(body.source_ids)}


@router.get("/onboarding/status", response_model=OnboardingStatus)
async def get_status(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    uid: uuid.UUID = current_user.id
    ob = await db.get(OnboardingState, uid)
    if not ob:
        return OnboardingStatus(step=0, is_complete=False, selected_topics=[], opted_out_sources=[])
    sel = ob.raw_selections or {}
    return OnboardingStatus(
        step=ob.step,
        is_complete=ob.step >= 1,
        selected_topics=sel.get("topics", []),
        opted_out_sources=[uuid.UUID(s) for s in sel.get("opted_out_sources", [])],
    )
