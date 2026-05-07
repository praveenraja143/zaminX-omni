"""
src/celery_tasks.py
===================
Celery background tasks for Zamin X.

Tasks:
1. scrape_ecourts_district   — Periodic eCourts data refresh (every 6 hours)
2. send_case_update_alerts   — Notify subscribers of case changes (daily)
3. compute_risk_scores       — Batch risk score computation
4. anchor_to_blockchain      — Daily Polygon blockchain anchor (Phase 3)
5. process_ocr_job           — Async OCR processing

Setup:
    celery -A src.celery_tasks worker --loglevel=info
    celery -A src.celery_tasks beat --loglevel=info
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from uuid import UUID

from celery import Celery
from celery.schedules import crontab

from src.config import settings

logger = logging.getLogger(__name__)

# ── Celery App ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "zaminx",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # re-queue on worker crash
    worker_prefetch_multiplier=1,  # fairness for long tasks
    task_soft_time_limit=300,      # 5 min soft limit
    task_time_limit=600,           # 10 min hard limit
)

# ── Beat Schedule (periodic tasks) ────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "scrape-ecourts-every-6-hours": {
        "task": "src.celery_tasks.scrape_ecourts_all_districts",
        "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
        "args": (["Erode", "Coimbatore", "Salem"],),
    },
    "send-alert-notifications-daily": {
        "task": "src.celery_tasks.send_case_update_alerts",
        "schedule": crontab(minute=0, hour=8),  # 8 AM IST daily
    },
    "blockchain-daily-anchor": {
        "task": "src.celery_tasks.anchor_to_blockchain",
        "schedule": crontab(minute=0, hour=0),  # midnight IST
    },
    "compute-risk-scores-batch": {
        "task": "src.celery_tasks.compute_batch_risk_scores",
        "schedule": crontab(minute=30, hour="*/12"),  # every 12 hours
    },
}


# ── Helper: run async code inside Celery task ─────────────────────────────────
def run_async(coro):
    """Run an async coroutine from a synchronous Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: eCourts Scraper
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(
    name="src.celery_tasks.scrape_ecourts_all_districts",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
def scrape_ecourts_all_districts(self, districts: List[str]):
    """
    Scrape eCourts data for specified districts.
    Updates court_cases table with fresh data.
    """
    logger.info("Starting eCourts scrape for districts: %s", districts)

    async def _scrape():
        from src.data_loader import ECourtsScraper
        from src.database import AsyncSessionLocal

        scraper = ECourtsScraper()
        total_cases = 0

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, text
            from src.models import LandRecord

            # Re-scrape all known land records to refresh case data
            stmt = select(LandRecord).where(LandRecord.district.in_(districts))
            result = await db.execute(stmt)
            records = result.scalars().all()

            logger.info("Re-scraping %d land records across %d districts", len(records), len(districts))

            from src.data_loader import DataPersister
            persister = DataPersister(db)

            for record in records:
                try:
                    new_cases = await scraper.search_by_survey_number(
                        record.village_name, record.survey_number, record.state
                    )
                    _, saved = await persister.persist_search_result(
                        record.village_name, record.survey_number, record.state, new_cases
                    )
                    total_cases += len(saved)
                    record.last_synced_at = datetime.utcnow()
                except Exception as e:
                    logger.error("Scrape failed for survey %s: %s", record.survey_number, e)

            await db.commit()

        await scraper.close()
        return total_cases

    try:
        count = run_async(_scrape())
        logger.info("eCourts scrape complete. Upserted %d cases.", count)
        return {"status": "success", "cases_upserted": count}
    except Exception as exc:
        logger.error("eCourts scrape task failed: %s", exc)
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: Alert Notifications
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(
    name="src.celery_tasks.send_case_update_alerts",
    bind=True,
)
def send_case_update_alerts(self):
    """
    Find subscriptions where case data changed since last notification.
    Send SMS/WhatsApp alerts via Twilio.
    """
    logger.info("Processing alert notifications...")

    async def _notify():
        from src.database import AsyncSessionLocal
        from src.models import AlertSubscription, CourtCase, LandRecord, User
        from sqlalchemy import select
        from src.notifications import NotificationService

        notifier = NotificationService()
        sent_count = 0

        async with AsyncSessionLocal() as db:
            # Find active subscriptions
            stmt = select(AlertSubscription).where(AlertSubscription.is_active == True)
            result = await db.execute(stmt)
            subs = result.scalars().all()

            for sub in subs:
                try:
                    # Check if any case was updated since last notification
                    last_notified = sub.last_notified_at or (datetime.utcnow() - timedelta(days=1))

                    cases_stmt = (
                        select(CourtCase)
                        .where(
                            CourtCase.survey_id == sub.survey_id,
                            CourtCase.last_updated > last_notified,
                            CourtCase.status == "active",
                        )
                        .limit(3)
                    )
                    cases_result = await db.execute(cases_stmt)
                    updated_cases = cases_result.scalars().all()

                    if not updated_cases:
                        continue

                    # Fetch user phone
                    user_stmt = select(User).where(User.user_id == sub.user_id)
                    user_result = await db.execute(user_stmt)
                    user = user_result.scalar_one_or_none()
                    if not user:
                        continue

                    # Fetch land record for display
                    land_stmt = select(LandRecord).where(LandRecord.survey_id == sub.survey_id)
                    land_result = await db.execute(land_stmt)
                    land = land_result.scalar_one_or_none()

                    # Send notification
                    message = _build_alert_message(land, updated_cases, user.language)
                    success = await notifier.send(sub.alert_channel, user.phone, message)

                    if success:
                        sub.last_notified_at = datetime.utcnow()
                        sent_count += 1

                except Exception as e:
                    logger.error("Alert failed for sub %s: %s", sub.sub_id, e)

            await db.commit()
        return sent_count

    count = run_async(_notify())
    logger.info("Alerts sent: %d", count)
    return {"status": "success", "alerts_sent": count}


def _build_alert_message(land, cases, language: str) -> str:
    """Build localized alert message."""
    if language == "ta":
        return (
            f"⚠️ Zamin X அறிவிப்பு\n"
            f"கிராமம்: {land.village_name if land else 'N/A'}\n"
            f"கணக்கு எண்: {land.survey_number if land else 'N/A'}\n"
            f"{len(cases)} வழக்கு(கள்) புதுப்பிக்கப்பட்டன.\n"
            f"விவரங்களுக்கு app திறக்கவும்."
        )
    elif language == "hi":
        return (
            f"⚠️ Zamin X सूचना\n"
            f"गांव: {land.village_name if land else 'N/A'}\n"
            f"सर्वे नं: {land.survey_number if land else 'N/A'}\n"
            f"{len(cases)} मामले अपडेट हुए।\n"
            f"विवरण के लिए ऐप खोलें।"
        )
    else:
        return (
            f"⚠️ Zamin X Alert\n"
            f"Village: {land.village_name if land else 'N/A'}\n"
            f"Survey: {land.survey_number if land else 'N/A'}\n"
            f"{len(cases)} case(s) updated.\n"
            f"Open the app for details."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: Batch Risk Score Computation
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(name="src.celery_tasks.compute_batch_risk_scores")
def compute_batch_risk_scores():
    """
    Recompute risk scores for land parcels where score is expired or missing.
    """
    logger.info("Starting batch risk score computation...")

    async def _compute():
        from src.database import AsyncSessionLocal
        from src.models import FraudScore, LandRecord
        from sqlalchemy import select
        from src.model import model_registry

        updated = 0
        async with AsyncSessionLocal() as db:
            # Find parcels without recent scores
            cutoff = datetime.utcnow() - timedelta(hours=24)
            stmt = (
                select(LandRecord)
                .outerjoin(FraudScore, FraudScore.survey_id == LandRecord.survey_id)
                .where(
                    (FraudScore.score_id == None) | (FraudScore.computed_at < cutoff)
                )
                .limit(500)
            )
            result = await db.execute(stmt)
            records = result.scalars().all()

            logger.info("Recomputing risk scores for %d parcels", len(records))

            for land in records:
                try:
                    risk = model_registry.risk_scorer.score([], [], {"area_acres": land.area_acres or 0})
                    score = FraudScore(
                        survey_id=land.survey_id,
                        risk_score=risk["risk_score"],
                        risk_level=risk["risk_level"],
                        case_count=0,
                        active_case_count=0,
                        model_version=risk.get("model_version", "v1"),
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                    )
                    db.add(score)
                    updated += 1
                except Exception as e:
                    logger.error("Risk score failed for survey %s: %s", land.survey_id, e)

            await db.commit()
        return updated

    count = run_async(_compute())
    logger.info("Batch risk scores updated: %d", count)
    return {"status": "success", "updated": count}


# ─────────────────────────────────────────────────────────────────────────────
# Task 4: Blockchain Daily Anchor (Phase 3)
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(name="src.celery_tasks.anchor_to_blockchain")
def anchor_to_blockchain():
    """
    Phase 3: Compute Merkle root of all today's new court records.
    Anchor it to Polygon mainnet via DailyAnchor.sol smart contract.
    """
    if not settings.feature_blockchain:
        logger.info("Blockchain feature disabled. Skipping anchor task.")
        return {"status": "skipped", "reason": "blockchain_disabled"}

    logger.info("Starting blockchain daily anchor...")
    # Phase 3 implementation: see blockchain/anchor_service.py
    return {"status": "pending", "phase": 3}


# ─────────────────────────────────────────────────────────────────────────────
# Task 5: OCR Processing (async via Celery)
# ─────────────────────────────────────────────────────────────────────────────
@celery_app.task(
    name="src.celery_tasks.process_ocr_job",
    bind=True,
    max_retries=2,
)
def process_ocr_job(self, job_id: str, image_path: str):
    """
    Process an OCR job asynchronously.
    Updates OCRJob record in DB with results.
    """
    logger.info("Processing OCR job: %s", job_id)

    async def _process():
        from src.database import AsyncSessionLocal
        from src.models import OCRJob
        from src.model import model_registry
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            stmt = select(OCRJob).where(OCRJob.job_id == UUID(job_id))
            result = await db.execute(stmt)
            job = result.scalar_one_or_none()
            if not job:
                return

            ocr_result = model_registry.ocr_extractor.extract(image_path)
            job.status = "completed" if ocr_result.get("success") else "failed"
            job.extracted_survey_number = ocr_result.get("survey_number")
            job.extracted_village_name = ocr_result.get("village_name")
            job.confidence_score = ocr_result.get("confidence")
            job.raw_text = (ocr_result.get("raw_text") or "")[:2000]
            job.error_message = ocr_result.get("error")
            job.completed_at = datetime.utcnow()
            await db.commit()

    try:
        run_async(_process())
        return {"status": "success", "job_id": job_id}
    except Exception as exc:
        logger.error("OCR job %s failed: %s", job_id, exc)
        raise self.retry(exc=exc)
