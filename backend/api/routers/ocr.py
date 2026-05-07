"""
api/routers/ocr.py
==================
POST /api/ocr/extract — Upload patta/chitta image, extract survey number via OCR.
GET  /api/ocr/job/:job_id — Poll OCR job status.
"""

import logging
import tempfile
import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.auth import require_user
from api.schemas import OCRJobResponse
from src.database import get_db
from src.model import model_registry
from src.models import OCRJob, User

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_IMAGE_SIZE_MB = 10


@router.post(
    "/extract",
    response_model=OCRJobResponse,
    summary="Extract Survey Number from Document Image",
    description=(
        "Upload a photo of a patta, chitta, or adangal document. "
        "The OCR engine extracts the survey number automatically. "
        "Supports JPEG, PNG, PDF. Max size: 10MB."
    ),
)
async def extract_survey_number(
    file: UploadFile = File(..., description="Patta/chitta document image"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    OCR extraction pipeline:
    1. Validate image size/type
    2. Save to temp file
    3. Run Tesseract with OpenCV preprocessing
    4. Return extracted survey number + confidence
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Use JPEG, PNG, or PDF.",
        )

    # Read and validate size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {size_mb:.1f}MB. Maximum allowed: {MAX_IMAGE_SIZE_MB}MB.",
        )

    # Create OCR job record
    job = OCRJob(
        user_id=current_user.user_id,
        status="processing",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Save to temp file and run OCR
    try:
        suffix = ".jpg" if "jpeg" in (file.content_type or "") else ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        ocr_result = model_registry.ocr_extractor.extract(tmp_path)

        # Update job record
        job.status = "completed" if ocr_result.get("success") else "failed"
        job.extracted_survey_number = ocr_result.get("survey_number")
        job.extracted_village_name = ocr_result.get("village_name")
        job.confidence_score = ocr_result.get("confidence")
        job.raw_text = (ocr_result.get("raw_text") or "")[:2000]  # cap length
        job.error_message = ocr_result.get("error")

        await db.commit()
        await db.refresh(job)

        logger.info(
            "OCR job %s completed: survey=%s confidence=%.1f",
            job.job_id, job.extracted_survey_number, job.confidence_score or 0,
        )

    except Exception as e:
        logger.error("OCR job %s failed: %s", job.job_id, e)
        job.status = "failed"
        job.error_message = str(e)
        await db.commit()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return OCRJobResponse.model_validate(job)


@router.get(
    "/job/{job_id}",
    response_model=OCRJobResponse,
    summary="Get OCR Job Status",
)
async def get_ocr_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Poll status of a background OCR job."""
    stmt = select(OCRJob).where(
        OCRJob.job_id == job_id,
        OCRJob.user_id == current_user.user_id,
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="OCR job not found")

    return OCRJobResponse.model_validate(job)
