"""
api/routers/search.py
=====================
POST /api/search  — Core land litigation search endpoint.
GET  /api/case/:case_id — Fetch detailed case info.

This is the PRIMARY endpoint of Zamin X.
A user enters village_name + survey_number → gets full litigation report.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.auth import check_search_quota, get_current_user
from api.schemas import CaseOrderSummary, CourtCaseSummary, SearchRequest, SearchResponse
from src.database import get_db
from src.models import CaseOrder, CourtCase, User
from src.predict import LandSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search Land Litigation Status",
    description=(
        "**Core endpoint.** Enter a village name and survey number to instantly check:\n"
        "- Active and disposed court cases\n"
        "- AI-generated Tamil/Hindi summaries of case orders\n"
        "- Fraud risk score (0-100)\n"
        "- Blockchain verification badge\n"
        "- Ownership chain history\n\n"
        "**Free users**: 3 searches/month. **Premium**: unlimited."
    ),
    responses={
        200: {"description": "Land litigation report returned successfully"},
        402: {"description": "Monthly search quota exceeded"},
        422: {"description": "Invalid village name or survey number"},
        503: {"description": "Data source temporarily unavailable"},
    },
)
async def search_land(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Primary land litigation search.

    - Checks Redis cache first (6-hour TTL)
    - Scrapes eCourts if cache miss
    - Runs NLP summarization on case orders
    - Computes fraud risk score
    - Returns blockchain badge status

    Rate limits: 60 req/min for anonymous, 500 req/min for B2B.
    """
    # Enforce freemium quota
    check_search_quota(current_user)

    # Increment usage counter
    if current_user:
        current_user.searches_this_month = (current_user.searches_this_month or 0) + 1
        await db.commit()

    try:
        service = LandSearchService(db)
        result = await service.search(
            village_name=request.village_name,
            survey_number=request.survey_number,
            state=request.state,
            language=request.language,
            user_id=str(current_user.user_id) if current_user else None,
        )
        return result

    except Exception as e:
        logger.error("Search failed for village=%s survey=%s: %s", request.village_name, request.survey_number, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch court data. Please try again in a few seconds.",
        )


@router.get(
    "/case/{case_id}",
    summary="Get Full Case Details",
    description="Get complete details for a specific court case including all orders and AI summaries.",
)
async def get_case_detail(
    case_id: UUID,
    language: str = Query(default="ta", pattern="^(ta|hi|en)$"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Fetch a single court case with all its orders and AI-generated summaries."""
    stmt = select(CourtCase).where(CourtCase.case_id == case_id)
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    # Fetch all orders
    orders_stmt = (
        select(CaseOrder)
        .where(CaseOrder.case_id == case_id)
        .order_by(CaseOrder.order_date.desc())
    )
    orders_result = await db.execute(orders_stmt)
    orders = orders_result.scalars().all()

    return {
        "case_id": str(case.case_id),
        "case_number": case.case_number,
        "court_name": case.court_name,
        "case_type": case.case_type,
        "petitioner": case.petitioner,
        "respondent": case.respondent,
        "filing_date": case.filing_date.isoformat() if case.filing_date else None,
        "next_hearing": case.next_hearing.isoformat() if case.next_hearing else None,
        "status": case.status,
        "stage": case.stage,
        "judge_name": case.judge_name,
        "orders": [
            {
                "order_id": str(o.order_id),
                "order_date": o.order_date.isoformat() if o.order_date else None,
                "judge_name": o.judge_name,
                "summary_tamil": o.order_summary_tamil,
                "summary_hindi": o.order_summary_hindi,
                "key_issue": o.key_issue,
                "urgency_level": o.urgency_level,
                "next_date": o.next_date.isoformat() if o.next_date else None,
            }
            for o in orders
        ],
        "total_orders": len(orders),
    }
