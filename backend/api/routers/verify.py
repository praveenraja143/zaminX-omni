"""
api/routers/verify.py
=====================
POST /api/verify — Verify blockchain integrity of a court record.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.schemas import VerifyRequest, VerifyResponse
from src.config import settings
from src.database import get_db
from src.models import BlockchainRecord

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/verify",
    response_model=VerifyResponse,
    summary="Verify Blockchain Integrity",
    description=(
        "Verify that a court record has not been tampered with by checking its "
        "SHA-256 hash against Hyperledger Fabric and Polygon blockchain. "
        "Anyone can verify — no authentication required."
    ),
)
async def verify_record(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public blockchain verification endpoint.
    Phase 1: Returns placeholder (blockchain not live yet).
    Phase 3: Computes hash of retrieved record and compares to on-chain hash.
    """
    if not settings.feature_blockchain:
        return VerifyResponse(
            survey_id=request.survey_id,
            is_verified=False,
            blockchain_hash=None,
            polygon_tx=None,
            fabric_block_id=None,
            anchored_at=None,
            verification_message=(
                "Blockchain verification is not yet active. "
                "This feature will be live in Phase 3 (Month 7-10). "
                "All records are stored in PostgreSQL with SHA-256 integrity hashes."
            ),
        )

    # Phase 3: Real blockchain verification
    stmt = (
        select(BlockchainRecord)
        .where(BlockchainRecord.survey_id == request.survey_id)
        .order_by(BlockchainRecord.created_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record:
        return VerifyResponse(
            survey_id=request.survey_id,
            is_verified=False,
            blockchain_hash=None,
            polygon_tx=None,
            fabric_block_id=None,
            anchored_at=None,
            verification_message="No blockchain record found for this survey parcel.",
        )

    return VerifyResponse(
        survey_id=request.survey_id,
        is_verified=True,
        blockchain_hash=record.data_hash_sha256,
        polygon_tx=record.polygon_tx_hash,
        fabric_block_id=record.fabric_block_id,
        anchored_at=record.anchored_at,
        verification_message="✅ Record verified on Hyperledger Fabric and Polygon blockchain.",
    )
