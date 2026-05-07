"""
api/routers/risk.py
===================
GET /api/risk-score/:survey_id — Get pre-computed fraud risk score for a land parcel.
"""

import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.auth import get_current_user
from api.schemas import RiskScoreResponse
from src.database import get_db
from src.models import FraudScore, User

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/risk-score/{survey_id}",
    response_model=RiskScoreResponse,
    summary="Get Fraud Risk Score",
    description=(
        "Returns the pre-computed AI fraud risk score for a land parcel. "
        "Scores are cached for 24 hours. Run /api/search first to generate the score."
    ),
)
async def get_risk_score(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Retrieve latest fraud risk score for a survey parcel."""
    stmt = (
        select(FraudScore)
        .where(FraudScore.survey_id == survey_id)
        .order_by(FraudScore.computed_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    score = result.scalar_one_or_none()

    if not score:
        raise HTTPException(
            status_code=404,
            detail=f"No risk score found for survey_id={survey_id}. Run /api/search first.",
        )

    return RiskScoreResponse.model_validate(score)
