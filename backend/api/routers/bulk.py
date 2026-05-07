"""
api/routers/bulk.py
===================
GET /api/bulk/cases — B2B bulk land litigation lookup (100 parcels at once).
Requires B2B API key (subscription_tier = "b2b").
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import require_b2b
from api.schemas import BulkSearchRequest, BulkSearchResponse, BulkSearchResultItem
from src.database import get_db
from src.models import User
from src.predict import LandSearchService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/cases",
    response_model=BulkSearchResponse,
    summary="Bulk Land Litigation Lookup (B2B)",
    description=(
        "**B2B only.** Submit up to 100 survey numbers in one request. "
        "Ideal for real estate firms, banks doing agricultural loan due diligence, "
        "or industrial companies acquiring rural land. "
        "Returns risk score and active case count per parcel."
    ),
)
async def bulk_search(
    request: BulkSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_b2b),
):
    """
    Bulk search pipeline:
    - Processes up to 100 parcels concurrently (semaphore-limited to 10 parallel)
    - Returns lightweight results (not full case details)
    - Full details available via individual /api/search calls
    """
    if len(request.items) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 items per bulk request.")

    service = LandSearchService(db)
    semaphore = asyncio.Semaphore(10)  # max 10 concurrent eCourts requests

    async def process_one(item) -> BulkSearchResultItem:
        async with semaphore:
            try:
                result = await service.search(
                    village_name=item.village_name,
                    survey_number=item.survey_number,
                    state=item.state,
                    language=request.language,
                    user_id=str(current_user.user_id),
                )
                meta = result.get("search_metadata", {})
                risk = result.get("risk_assessment", {})
                return BulkSearchResultItem(
                    village_name=item.village_name,
                    survey_number=item.survey_number,
                    total_cases=meta.get("total_cases", 0),
                    active_cases=meta.get("active_cases", 0),
                    risk_score=risk.get("risk_score", 0),
                    risk_level=risk.get("risk_level", "low"),
                    status="success",
                )
            except Exception as e:
                logger.error("Bulk search failed for %s/%s: %s", item.village_name, item.survey_number, e)
                return BulkSearchResultItem(
                    village_name=item.village_name,
                    survey_number=item.survey_number,
                    total_cases=0,
                    active_cases=0,
                    risk_score=0,
                    risk_level="unknown",
                    status="error",
                    error=str(e),
                )

    results = await asyncio.gather(*[process_one(item) for item in request.items])
    successful = sum(1 for r in results if r.status == "success")

    logger.info(
        "Bulk search complete: user=%s requested=%d processed=%d",
        current_user.user_id, len(request.items), successful,
    )

    return BulkSearchResponse(
        total_requested=len(request.items),
        total_processed=successful,
        results=list(results),
        processed_at=datetime.utcnow(),
    )
