"""
api/routers/alerts.py
=====================
POST /api/alerts/subscribe   — Subscribe to SMS/WhatsApp case update alerts
DELETE /api/alerts/unsubscribe/:sub_id — Unsubscribe
GET  /api/alerts/my          — List user's active subscriptions
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from api.auth import require_user
from api.schemas import AlertSubscribeRequest, AlertSubscribeResponse
from src.database import get_db
from src.models import AlertSubscription, LandRecord, User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/subscribe",
    response_model=AlertSubscribeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to Case Update Alerts",
)
async def subscribe_alerts(
    request: AlertSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Subscribe to SMS/WhatsApp alerts for a land parcel.
    Notifications are sent automatically when case hearings or orders are updated.
    """
    # Verify land record exists
    stmt = select(LandRecord).where(LandRecord.survey_id == request.survey_id)
    result = await db.execute(stmt)
    land = result.scalar_one_or_none()
    if not land:
        raise HTTPException(status_code=404, detail="Land record not found. Run /api/search first.")

    # Check existing subscription
    existing_stmt = select(AlertSubscription).where(
        AlertSubscription.user_id == current_user.user_id,
        AlertSubscription.survey_id == request.survey_id,
        AlertSubscription.alert_channel == request.channel,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing:
        return AlertSubscribeResponse(
            subscription_id=existing.sub_id,
            survey_id=request.survey_id,
            channel=request.channel,
            status="already_subscribed",
            message=f"You are already subscribed to {request.channel} alerts for this parcel.",
        )

    sub = AlertSubscription(
        user_id=current_user.user_id,
        survey_id=request.survey_id,
        alert_channel=request.channel,
        is_active=True,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    logger.info(
        "Alert subscription created: user=%s survey=%s channel=%s",
        current_user.user_id, request.survey_id, request.channel,
    )

    return AlertSubscribeResponse(
        subscription_id=sub.sub_id,
        survey_id=request.survey_id,
        channel=request.channel,
        status="subscribed",
        message=f"✅ You will receive {request.channel} alerts when case status changes for survey {land.survey_number}.",
    )


@router.delete(
    "/unsubscribe/{sub_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unsubscribe from Alerts",
)
async def unsubscribe(
    sub_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    stmt = delete(AlertSubscription).where(
        AlertSubscription.sub_id == sub_id,
        AlertSubscription.user_id == current_user.user_id,
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.commit()


@router.get("/my", summary="List My Alert Subscriptions")
async def my_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Return all active alert subscriptions for the current user."""
    stmt = (
        select(AlertSubscription)
        .where(AlertSubscription.user_id == current_user.user_id, AlertSubscription.is_active == True)
    )
    result = await db.execute(stmt)
    subs = result.scalars().all()
    return {
        "subscriptions": [
            {
                "sub_id": str(s.sub_id),
                "survey_id": str(s.survey_id),
                "channel": s.alert_channel,
                "last_notified_at": s.last_notified_at.isoformat() if s.last_notified_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in subs
        ],
        "total": len(subs),
    }
