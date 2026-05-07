"""
src/data_loader.py
==================
Data ingestion layer for Zamin X.

Responsibilities:
- Scrape court case data from eCourts / NJDG
- Fetch land records from Bhoomi / DILRMP APIs (when available)
- Serve mock data during development
- Persist raw data to PostgreSQL

NOTE: Web scraping eCourts is done politely with rate-limiting.
In production, integrate with the official eCourts Data API (Suomoto CIS)
after obtaining MoU / government data sharing agreement.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models import CourtCase, LandRecord

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Transfer Objects
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class RawCaseData:
    """Raw data scraped from eCourts before normalization."""
    case_number: str
    court_name: str
    case_type: str
    petitioner: str
    respondent: str
    filing_date: Optional[datetime]
    next_hearing: Optional[datetime]
    status: str
    stage: str
    judge_name: str
    survey_number: str
    village_name: str
    district: str
    state: str = "TN"
    orders: List[Dict] = field(default_factory=list)
    ecourts_case_id: Optional[str] = None


@dataclass
class RawLandData:
    """Raw land record data from Bhoomi / DILRMP."""
    survey_number: str
    village_name: str
    district: str
    taluk: str
    state: str = "TN"
    area_acres: Optional[float] = None
    patta_number: Optional[str] = None
    land_type: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Mock Data Generator (for development / demo)
# ─────────────────────────────────────────────────────────────────────────────
class MockDataGenerator:
    """
    Generates realistic mock court case and land record data.
    Used in development when live APIs are unavailable.
    Matches the schema of real eCourts data.
    """

    SAMPLE_VILLAGES = [
        "Gobichettipalayam", "Erode", "Bhavani", "Anthiyur", "Sathyamangalam",
        "Perundurai", "Kangayam", "Dharapuram", "Tiruppur", "Palladam",
    ]

    CASE_TYPES = [
        "Civil Suit", "Partition Suit", "Title Dispute", "Boundary Dispute",
        "Mortgage Suit", "Revenue Case", "Injunction Suit",
    ]

    COURTS = [
        "District Court, Erode", "Sub-Court, Gobichettipalayam",
        "Principal District Court, Coimbatore", "District Munsif Court, Tiruppur",
        "High Court of Madras", "Revenue Divisional Officer Court, Erode",
    ]

    JUDGE_NAMES = [
        "Hon. K. Ramasamy", "Hon. M. Selvakumar", "Hon. S. Priya",
        "Hon. R. Venkataraman", "Hon. A. Muthukrishnan",
    ]

    PETITIONERS = [
        "Murugesan s/o Ramu", "Lakshmi w/o Selvam", "Rangadurai s/o Govindan",
        "Tamil Nadu Housing Board", "Erode District Cooperative Bank",
    ]

    def generate_cases(self, village_name: str, survey_number: str, count: int = 3) -> List[RawCaseData]:
        """Generate mock cases for a given land parcel."""
        import random
        random.seed(f"{village_name}:{survey_number}")

        cases = []
        num_cases = random.randint(0, count)

        for i in range(num_cases):
            filing = datetime.now() - timedelta(days=random.randint(30, 1825))
            cases.append(RawCaseData(
                case_number=f"OS/{random.randint(100, 999)}/{filing.year}",
                court_name=random.choice(self.COURTS),
                case_type=random.choice(self.CASE_TYPES),
                petitioner=random.choice(self.PETITIONERS),
                respondent=random.choice(self.PETITIONERS),
                filing_date=filing,
                next_hearing=datetime.now() + timedelta(days=random.randint(7, 120)),
                status=random.choice(["active", "active", "active", "disposed"]),
                stage=random.choice(["Arguments", "Evidence", "Cross-Examination", "Final Hearing"]),
                judge_name=random.choice(self.JUDGE_NAMES),
                survey_number=survey_number,
                village_name=village_name,
                district="Erode",
                state="TN",
                ecourts_case_id=f"TN{random.randint(10000, 99999)}",
                orders=self._generate_orders(random.randint(1, 5)),
            ))

        return cases

    def _generate_orders(self, count: int) -> List[Dict]:
        orders = []
        for _ in range(count):
            days_ago = __import__("random").randint(10, 500)
            orders.append({
                "order_date": (datetime.now() - timedelta(days=days_ago)).isoformat(),
                "order_text_raw": (
                    "The petitioner herein challenges the order dated passed by the "
                    "Revenue Divisional Officer regarding boundary demarcation of the "
                    "land bearing survey number. The court directed both parties to "
                    "submit documents related to ownership. Case adjourned to next hearing date."
                ),
                "judge_name": __import__("random").choice(self.JUDGE_NAMES),
                "next_date": (datetime.now() + timedelta(days=30)).isoformat(),
            })
        return orders

    def generate_land_record(self, village_name: str, survey_number: str) -> RawLandData:
        import random
        random.seed(f"land:{village_name}:{survey_number}")
        return RawLandData(
            survey_number=survey_number,
            village_name=village_name,
            district="Erode",
            taluk="Gobichettipalayam",
            state="TN",
            area_acres=round(random.uniform(0.5, 10.0), 2),
            patta_number=f"P{random.randint(1000, 9999)}",
            land_type=random.choice(["agricultural", "residential", "commercial"]),
        )


# ─────────────────────────────────────────────────────────────────────────────
# eCourts Scraper
# ─────────────────────────────────────────────────────────────────────────────
class ECourtsScraper:
    """
    Scrapes court case data from eCourts India portal.

    IMPORTANT: In production, replace with official eCourts Data API
    after obtaining a government data sharing MoU.
    Current implementation: NJDG public data + respectful scraping.
    """

    BASE_URL = "https://ecourts.gov.in"
    NJDG_URL = "https://njdg.ecourts.gov.in"
    REQUEST_DELAY = 2  # seconds between requests (polite scraping)

    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=30,
            headers={
                "User-Agent": "ZaminX-LandLitigationChecker/1.0 (Research; contact@zaminx.in)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def search_by_survey_number(
        self, village_name: str, survey_number: str, state: str = "TN"
    ) -> List[RawCaseData]:
        """
        Search eCourts for cases linked to a survey number.

        In Phase 1 (MVP): returns mock data.
        In Phase 2+: integrates with live eCourts API.
        """
        logger.info(
            "Searching eCourts for village=%s survey=%s state=%s",
            village_name, survey_number, state,
        )

        # TODO Phase 2: Replace with live eCourts API call
        # For now, use mock data generator
        mock_gen = MockDataGenerator()
        cases = mock_gen.generate_cases(village_name, survey_number)

        await asyncio.sleep(self.REQUEST_DELAY)  # polite delay even for mock
        logger.info("Found %d cases for survey %s", len(cases), survey_number)
        return cases

    async def _parse_case_list_html(self, html: str, survey_number: str, village: str) -> List[RawCaseData]:
        """Parse eCourts HTML response into RawCaseData objects."""
        soup = BeautifulSoup(html, "lxml")
        cases = []

        for row in soup.select("table.case-table tbody tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 6:
                continue
            try:
                cases.append(RawCaseData(
                    case_number=cells[0],
                    court_name=cells[1],
                    case_type=cells[2],
                    petitioner=cells[3],
                    respondent=cells[4],
                    filing_date=self._parse_date(cells[5]),
                    next_hearing=self._parse_date(cells[6]) if len(cells) > 6 else None,
                    status="active",
                    stage=cells[7] if len(cells) > 7 else "",
                    judge_name=cells[8] if len(cells) > 8 else "",
                    survey_number=survey_number,
                    village_name=village,
                    district="",
                    state="TN",
                ))
            except Exception as e:
                logger.warning("Failed to parse case row: %s", e)

        return cases

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None

    async def close(self):
        await self.session.aclose()


# ─────────────────────────────────────────────────────────────────────────────
# Data Persistence Layer
# ─────────────────────────────────────────────────────────────────────────────
class DataPersister:
    """
    Saves raw scraped data into PostgreSQL.
    Handles upsert logic to avoid duplicates on re-scrape.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_land_record(self, raw: RawLandData) -> LandRecord:
        """Insert or return existing land record."""
        from sqlalchemy import select

        stmt = select(LandRecord).where(
            LandRecord.state == raw.state,
            LandRecord.district == raw.district,
            LandRecord.village_name == raw.village_name,
            LandRecord.survey_number == raw.survey_number,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        record = LandRecord(
            state=raw.state,
            district=raw.district,
            taluk=raw.taluk,
            village_name=raw.village_name,
            survey_number=raw.survey_number,
            area_acres=raw.area_acres,
            patta_number=raw.patta_number,
            land_type=raw.land_type,
            last_synced_at=datetime.utcnow(),
        )
        self.db.add(record)
        await self.db.flush()
        logger.info("Created land record survey_id=%s", record.survey_id)
        return record

    async def upsert_court_case(self, raw: RawCaseData, survey_id: UUID) -> CourtCase:
        """Insert or update court case; avoid duplicates by case_number + court_name."""
        from sqlalchemy import select

        stmt = select(CourtCase).where(
            CourtCase.survey_id == survey_id,
            CourtCase.case_number == raw.case_number,
            CourtCase.court_name == raw.court_name,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update mutable fields
            existing.status = raw.status
            existing.next_hearing = raw.next_hearing
            existing.stage = raw.stage
            existing.judge_name = raw.judge_name
            existing.last_updated = datetime.utcnow()
            return existing

        case = CourtCase(
            survey_id=survey_id,
            case_number=raw.case_number,
            court_name=raw.court_name,
            case_type=raw.case_type,
            petitioner=raw.petitioner,
            respondent=raw.respondent,
            filing_date=raw.filing_date,
            next_hearing=raw.next_hearing,
            status=raw.status,
            stage=raw.stage,
            judge_name=raw.judge_name,
            state=raw.state,
            district=raw.district,
            ecourts_case_id=raw.ecourts_case_id,
            last_updated=datetime.utcnow(),
        )
        self.db.add(case)
        await self.db.flush()
        return case

    async def persist_search_result(
        self,
        village_name: str,
        survey_number: str,
        state: str,
        cases: List[RawCaseData],
    ) -> tuple[LandRecord, List[CourtCase]]:
        """
        Full pipeline: land record → court cases → flush all.
        Returns the persisted objects.
        """
        mock_land = MockDataGenerator().generate_land_record(village_name, survey_number)
        land = await self.upsert_land_record(mock_land)

        court_cases = []
        for raw_case in cases:
            cc = await self.upsert_court_case(raw_case, land.survey_id)
            court_cases.append(cc)

        await self.db.commit()
        return land, court_cases


# ─────────────────────────────────────────────────────────────────────────────
# Village Auto-Suggest Data
# ─────────────────────────────────────────────────────────────────────────────
TAMIL_NADU_VILLAGES = [
    # Erode District
    "Gobichettipalayam", "Erode", "Bhavani", "Anthiyur", "Sathyamangalam",
    "Perundurai", "Kangayam", "Dharapuram", "Tiruppur", "Palladam",
    "Kadambur", "Bhavanisagar", "Modakkurichi", "Chennimalai", "Kodumudi",
    # Coimbatore District
    "Coimbatore", "Pollachi", "Mettupalayam", "Anaimalai", "Valparai",
    "Sulur", "Kinathukadavu", "Madukkarai", "Thondamuthur",
    # Salem District
    "Salem", "Mettur", "Omalur", "Yercaud", "Attur", "Sankagiri",
    # Namakkal District
    "Namakkal", "Rasipuram", "Tiruchengode", "Paramathi-Velur",
]


async def get_village_suggestions(query: str, limit: int = 10) -> List[str]:
    """Simple prefix-based village name suggestions. Replace with DB query at scale."""
    query_lower = query.lower()
    return [v for v in TAMIL_NADU_VILLAGES if query_lower in v.lower()][:limit]
