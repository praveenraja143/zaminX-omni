"""
src/predict.py
==============
Core prediction service for Zamin X.

Orchestrates:
  1. Land record lookup / creation
  2. eCourts case scraping (or cache hit)
  3. AI NLP summarization of case orders
  4. Fraud risk scoring
  5. Blockchain verification (Phase 3)
  6. Response assembly

This is the heart of the system — called by the API on every /search request.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import settings
from src.data_loader import ECourtsScraper, DataPersister, get_village_suggestions
from src.model import model_registry
from src.models import (
    CourtCase, FraudScore, LandRecord, OwnershipChain, BlockchainRecord
)
from src.preprocessing import normalize_survey_number, normalize_village_name
from src.feature_engineering import score_to_risk_level, risk_level_to_label

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Redis Cache Client
# ─────────────────────────────────────────────────────────────────────────────
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def _cache_key(village: str, survey: str, state: str) -> str:
    """Generate cache key for a search query."""
    raw = f"search:{state}:{village}:{survey}".lower()
    return f"zx:{hashlib.md5(raw.encode()).hexdigest()}"


# ─────────────────────────────────────────────────────────────────────────────
# Main Search Service
# ─────────────────────────────────────────────────────────────────────────────
class LandSearchService:
    """
    Orchestrates the complete land litigation search pipeline.
    Entry point for all /search API requests.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scraper = ECourtsScraper()
        self.persister = DataPersister(db)

    async def search(
        self,
        village_name: str,
        survey_number: str,
        state: str = "TN",
        language: str = "ta",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full search pipeline.

        Returns complete land litigation report:
        {
            land_record: {...},
            cases: [...],
            risk_assessment: {...},
            blockchain_badge: {...},
            ownership_chain: [...],
            search_metadata: {...},
        }
        """
        start_time = datetime.utcnow()

        # Normalize inputs
        village = normalize_village_name(village_name)
        survey = normalize_survey_number(survey_number)

        logger.info(
            "Search: village=%s survey=%s state=%s lang=%s user=%s",
            village, survey, state, language, user_id,
        )

        # ── 1. Check Redis cache ────────────────────────────────────────────
        cache_key = _cache_key(village, survey, state)
        cached = await self._get_cached(cache_key)
        if cached:
            cached["search_metadata"]["cache_hit"] = True
            logger.info("Cache HIT for %s", cache_key)
            return cached

        # ── 2. Scrape eCourts ───────────────────────────────────────────────
        raw_cases = await self.scraper.search_by_survey_number(village, survey, state)

        # ── 3. Persist to PostgreSQL ────────────────────────────────────────
        land_record, court_cases = await self.persister.persist_search_result(
            village, survey, state, raw_cases
        )

        # ── 4. AI Summarization ─────────────────────────────────────────────
        summarized_cases = await self._summarize_cases(raw_cases, language)

        # ── 5. Risk Scoring ─────────────────────────────────────────────────
        risk = await self._compute_risk(land_record, court_cases)
        await self._save_risk_score(land_record.survey_id, risk, len(court_cases))

        # ── 6. Blockchain Verification ──────────────────────────────────────
        blockchain_badge = await self._get_blockchain_badge(land_record.survey_id)

        # ── 7. Ownership Chain ──────────────────────────────────────────────
        ownership = await self._get_ownership_chain(land_record.survey_id)

        # ── 8. Assemble Response ────────────────────────────────────────────
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        result = {
            "land_record": self._serialize_land_record(land_record, village, survey),
            "cases": summarized_cases,
            "risk_assessment": risk,
            "blockchain_badge": blockchain_badge,
            "ownership_chain": ownership,
            "search_metadata": {
                "total_cases": len(summarized_cases),
                "active_cases": sum(1 for c in summarized_cases if c.get("status") == "active"),
                "disposed_cases": sum(1 for c in summarized_cases if c.get("status") == "disposed"),
                "searched_at": start_time.isoformat(),
                "response_time_ms": elapsed_ms,
                "language": language,
                "cache_hit": False,
                "data_freshness": "live",
            },
        }

        # ── 9. Cache Result ─────────────────────────────────────────────────
        await self._set_cached(cache_key, result)

        logger.info(
            "Search complete: %d cases, risk=%.1f, elapsed=%dms",
            len(summarized_cases), risk.get("risk_score", 0), elapsed_ms,
        )
        return result

    async def _summarize_cases(
        self, raw_cases: List, language: str
    ) -> List[Dict]:
        """Run NLP summarizer on each case's orders."""
        results = []
        for raw in raw_cases:
            case_dict = {
                "case_number": raw.case_number,
                "court_name": raw.court_name,
                "case_type": raw.case_type,
                "petitioner": raw.petitioner,
                "respondent": raw.respondent,
                "filing_date": raw.filing_date.isoformat() if raw.filing_date else None,
                "next_hearing": raw.next_hearing.isoformat() if raw.next_hearing else None,
                "status": raw.status,
                "stage": raw.stage,
                "judge_name": raw.judge_name,
                "orders": [],
            }

            # Summarize each order
            for order in raw.orders:
                order_text = order.get("order_text_raw", "")
                if order_text:
                    summary = model_registry.nlp_summarizer.summarize(order_text, language)
                else:
                    summary = {"summary_tamil": "", "summary_hindi": "", "key_issue": "", "urgency_level": "low"}

                case_dict["orders"].append({
                    "order_date": order.get("order_date"),
                    "judge_name": order.get("judge_name"),
                    "next_date": order.get("next_date"),
                    "summary_tamil": summary.get("summary_tamil"),
                    "summary_hindi": summary.get("summary_hindi"),
                    "key_issue": summary.get("key_issue"),
                    "urgency_level": summary.get("urgency_level"),
                })

            results.append(case_dict)
        return results

    async def _compute_risk(
        self, land_record: LandRecord, court_cases: List[CourtCase]
    ) -> Dict[str, Any]:
        """Compute XGBoost fraud risk score."""
        # Serialize ORM objects to dicts for feature extractor
        cases_dicts = [
            {
                "case_type": cc.case_type,
                "status": cc.status,
                "court_name": cc.court_name,
                "filing_date": cc.filing_date.isoformat() if cc.filing_date else None,
                "next_hearing": cc.next_hearing.isoformat() if cc.next_hearing else None,
            }
            for cc in court_cases
        ]

        # Fetch ownership transfers from DB
        stmt = select(OwnershipChain).where(OwnershipChain.survey_id == land_record.survey_id)
        result = await self.db.execute(stmt)
        transfers = result.scalars().all()
        transfers_dicts = [
            {
                "from_date": t.from_date.isoformat() if t.from_date else None,
                "transfer_type": t.transfer_type,
            }
            for t in transfers
        ]

        land_dict = {"area_acres": land_record.area_acres or 0}
        risk_result = model_registry.risk_scorer.score(cases_dicts, transfers_dicts, land_dict)
        return risk_result

    async def _save_risk_score(
        self, survey_id: UUID, risk: Dict, case_count: int
    ) -> None:
        """Persist computed risk score to DB."""
        from sqlalchemy import delete
        # Remove stale score
        await self.db.execute(
            delete(FraudScore).where(FraudScore.survey_id == survey_id)
        )
        score_record = FraudScore(
            survey_id=survey_id,
            risk_score=risk["risk_score"],
            risk_level=risk["risk_level"],
            case_count=case_count,
            active_case_count=int(risk.get("feature_vector", {}).get("active_case_count", 0)),
            rapid_transfer_flag=bool(risk.get("feature_vector", {}).get("rapid_transfer_flag", 0)),
            feature_vector=risk.get("feature_vector"),
            model_version=risk.get("model_version", "v1"),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        self.db.add(score_record)
        await self.db.commit()

    async def _get_blockchain_badge(self, survey_id: UUID) -> Dict[str, Any]:
        """
        Check if land record has blockchain verification.
        Phase 1: Returns placeholder (blockchain not yet live).
        Phase 3: Query Hyperledger Fabric + Polygon.
        """
        if not settings.feature_blockchain:
            return {
                "verified": False,
                "status": "not_anchored",
                "message": "Blockchain verification coming in Phase 3",
                "polygon_tx_hash": None,
                "fabric_block_id": None,
            }

        stmt = select(BlockchainRecord).where(
            BlockchainRecord.survey_id == survey_id,
            BlockchainRecord.anchor_type == "case_record",
        ).order_by(BlockchainRecord.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if record:
            return {
                "verified": True,
                "status": "anchored",
                "polygon_tx_hash": record.polygon_tx_hash,
                "fabric_block_id": record.fabric_block_id,
                "anchored_at": record.anchored_at.isoformat() if record.anchored_at else None,
                "polygonscan_url": f"https://polygonscan.com/tx/{record.polygon_tx_hash}" if record.polygon_tx_hash else None,
            }
        return {"verified": False, "status": "pending_anchor"}

    async def _get_ownership_chain(self, survey_id: UUID) -> List[Dict]:
        """Fetch ownership history for a land parcel."""
        stmt = (
            select(OwnershipChain)
            .where(OwnershipChain.survey_id == survey_id)
            .order_by(OwnershipChain.from_date.asc())
        )
        result = await self.db.execute(stmt)
        chain = result.scalars().all()
        return [
            {
                "owner_name": t.owner_name,
                "from_date": t.from_date.isoformat() if t.from_date else None,
                "to_date": t.to_date.isoformat() if t.to_date else None,
                "transfer_type": t.transfer_type,
                "deed_number": t.deed_number,
                "is_current": t.is_current,
                "blockchain_hash": t.blockchain_hash,
            }
            for t in chain
        ]

    @staticmethod
    def _serialize_land_record(
        record: LandRecord, village: str, survey: str
    ) -> Dict:
        return {
            "survey_id": str(record.survey_id),
            "state": record.state,
            "district": record.district,
            "taluk": record.taluk,
            "village_name": record.village_name or village,
            "survey_number": record.survey_number or survey,
            "area_acres": record.area_acres,
            "patta_number": record.patta_number,
            "land_type": record.land_type,
            "last_synced_at": record.last_synced_at.isoformat() if record.last_synced_at else None,
        }

    async def _get_cached(self, key: str) -> Optional[Dict]:
        try:
            redis = await get_redis()
            data = await redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("Redis GET failed: %s", e)
        return None

    async def _set_cached(self, key: str, data: Dict) -> None:
        try:
            redis = await get_redis()
            await redis.setex(key, settings.redis_search_result_ttl_seconds if hasattr(settings, 'redis_search_result_ttl_seconds') else 21600, json.dumps(data, default=str))
        except Exception as e:
            logger.warning("Redis SET failed: %s", e)
