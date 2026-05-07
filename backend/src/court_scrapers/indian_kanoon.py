"""
src/court_scrapers/indian_kanoon.py
====================================
Indian Kanoon API Client — Primary source for court case data.

API: https://api.indiankanoon.org
Auth: Token-based (shared API token)
Pricing: ₹0.50/search, ₹0.20/doc — Free ₹500 credits on signup
         Non-commercial: ₹10,000/month free

Endpoints used:
  POST /search/           → Search cases by keywords
  GET  /doc/{doc_id}/     → Get full case document
  GET  /docfragment/{id}/ → Get document snippet
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class IndianKanoonClient:
    """
    Client for Indian Kanoon legal database API.
    Searches for court cases related to land parcels.
    """

    BASE_URL = "https://api.indiankanoon.org"

    def __init__(self):
        self.token = settings.indian_kanoon_token
        self.is_available = bool(self.token)
        if not self.is_available:
            logger.warning("Indian Kanoon token not set. Court search will use mock data.")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token {self.token}",
            "Accept": "application/json",
        }

    async def search(
        self,
        query: str,
        pagenum: int = 0,
    ) -> Dict[str, Any]:
        """
        Search Indian Kanoon for cases matching the query.
        Returns raw API response with docs list.
        """
        if not self.is_available:
            return {"docs": [], "total": 0}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/search/",
                    data={"formInput": query, "pagenum": pagenum},
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Indian Kanoon search HTTP error: %s %s", e.response.status_code, e.response.text[:200])
            return {"docs": [], "total": 0, "error": str(e)}
        except Exception as e:
            logger.error("Indian Kanoon search failed: %s", e)
            return {"docs": [], "total": 0, "error": str(e)}

    async def get_document(self, doc_id: str) -> Dict[str, Any]:
        """Fetch a full case document by its Indian Kanoon doc ID."""
        if not self.is_available:
            return {}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/doc/{doc_id}/",
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error("Indian Kanoon doc fetch failed for %s: %s", doc_id, e)
            return {}

    async def search_land_cases(
        self,
        owner_name: str = "",
        village: str = "",
        survey_no: str = "",
        district: str = "",
        state: str = "Tamil Nadu",
    ) -> List[Dict[str, Any]]:
        """
        Search for land-related court cases using multiple query strategies.
        Returns normalized list of case data.
        """
        all_cases = []
        queries = self._build_search_queries(owner_name, village, survey_no, district, state)

        for query in queries[:3]:  # Max 3 queries to conserve credits
            logger.info("Indian Kanoon search: '%s'", query)
            result = await self.search(query)

            if "docs" in result:
                for doc in result["docs"][:10]:  # Max 10 results per query
                    case = self._parse_doc_to_case(doc, village, survey_no, district)
                    if case:
                        all_cases.append(case)

        # Deduplicate by title
        seen_titles = set()
        unique_cases = []
        for case in all_cases:
            title_key = case.get("case_number", "") + case.get("court_name", "")
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_cases.append(case)

        logger.info("Indian Kanoon found %d unique cases", len(unique_cases))
        return unique_cases[:15]  # Cap at 15 results

    def _build_search_queries(
        self,
        owner_name: str,
        village: str,
        survey_no: str,
        district: str,
        state: str,
    ) -> List[str]:
        """Build optimized search queries for land case lookup."""
        queries = []

        # Query 1: Survey number + village (most specific)
        if survey_no and village:
            queries.append(f'survey number "{survey_no}" "{village}" land')

        # Query 2: Owner name + land (if provided)
        if owner_name:
            queries.append(f'"{owner_name}" land property {district or state}')

        # Query 3: Village + district land dispute
        if village and district:
            queries.append(f'"{village}" "{district}" land dispute property')

        # Query 4: Generic district land cases
        if district:
            queries.append(f'land dispute {district} {state} property survey')

        # Fallback
        if not queries:
            queries.append(f"land dispute {state} property survey")

        return queries

    def _parse_doc_to_case(
        self,
        doc: Dict[str, Any],
        village: str,
        survey_no: str,
        district: str,
    ) -> Optional[Dict[str, Any]]:
        """Parse an Indian Kanoon document result into a normalized case dict."""
        try:
            title = doc.get("title", "")
            doc_id = str(doc.get("tid", ""))

            # Extract case number from title
            case_number = self._extract_case_number(title)
            court_name = self._extract_court_name(title)

            # Get headline/snippet
            headline = doc.get("headline", "")
            # Strip HTML tags
            headline_clean = re.sub(r"<[^>]+>", "", headline)

            # Determine case type
            case_type = self._classify_case_type(title + " " + headline_clean)

            # Determine status
            status = "disposed"
            status_keywords_active = ["pending", "next hearing", "adjourned", "posted"]
            if any(kw in headline_clean.lower() for kw in status_keywords_active):
                status = "active"

            # Extract date
            docsource = doc.get("docsource", "")
            filing_date = self._extract_date(docsource) or self._extract_date(title)

            return {
                "case_number": case_number or title[:50],
                "court_name": court_name or "Unknown Court",
                "case_type": case_type,
                "petitioner": self._extract_party(title, "petitioner"),
                "respondent": self._extract_party(title, "respondent"),
                "filing_date": filing_date,
                "next_hearing": None,
                "status": status,
                "stage": "",
                "judge_name": "",
                "survey_number": survey_no,
                "village_name": village,
                "district": district,
                "source": "indian_kanoon",
                "doc_id": doc_id,
                "headline": headline_clean[:500],
                "order_text": headline_clean,
            }
        except Exception as e:
            logger.warning("Failed to parse IK doc: %s", e)
            return None

    @staticmethod
    def _extract_case_number(title: str) -> str:
        """Extract case number from Indian Kanoon title."""
        patterns = [
            r"((?:Civil|Criminal|Writ|OS|SA|AS|CRP|CMP|OP|WP|SLP)\s*(?:No\.?|Appeal|Petition|Suit)?\s*\.?\s*\d+[\w/\-]*(?:\s*of\s*\d{4})?)",
            r"(\d+\s*/\s*\d{4})",
            r"(Case\s+No\.?\s*[\d/\-]+)",
        ]
        for p in patterns:
            m = re.search(p, title, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _extract_court_name(title: str) -> str:
        """Extract court name from title."""
        court_patterns = [
            r"((?:High Court of|Supreme Court|District Court|Sessions Court|Munsif Court|Sub Court|Revenue Court|Civil Court)\s*[,\w\s]*)",
            r"(Madras High Court)",
            r"((?:Principal\s+)?District\s+(?:and\s+Sessions\s+)?Court[,\s]*\w+)",
        ]
        for p in court_patterns:
            m = re.search(p, title, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    @staticmethod
    def _extract_party(title: str, party_type: str) -> str:
        """Extract petitioner/respondent from 'X vs Y' pattern."""
        vs_match = re.search(
            r"(.{3,80}?)\s+(?:vs?\.?|versus)\s+(.{3,80})",
            title,
            re.IGNORECASE,
        )
        if vs_match:
            if party_type == "petitioner":
                return vs_match.group(1).strip()[:100]
            return vs_match.group(2).strip()[:100]
        return ""

    @staticmethod
    def _extract_date(text: str) -> Optional[str]:
        """Extract date from text."""
        patterns = [
            r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})",
            r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})",
            r"(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def _classify_case_type(text: str) -> str:
        """Classify the type of land case from text."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["boundary", "demarcation"]):
            return "Boundary Dispute"
        if any(kw in text_lower for kw in ["partition", "division"]):
            return "Partition Suit"
        if any(kw in text_lower for kw in ["title", "ownership", "possession"]):
            return "Title Dispute"
        if any(kw in text_lower for kw in ["mortgage", "loan", "bank"]):
            return "Mortgage Suit"
        if any(kw in text_lower for kw in ["injunction", "restraining"]):
            return "Injunction Suit"
        if any(kw in text_lower for kw in ["revenue", "patta", "chitta"]):
            return "Revenue Case"
        if any(kw in text_lower for kw in ["writ", "petition"]):
            return "Writ Petition"
        return "Civil Suit"


# Singleton instance
indian_kanoon_client = IndianKanoonClient()
