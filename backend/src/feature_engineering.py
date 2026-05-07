"""
src/feature_engineering.py
===========================
Feature engineering for the XGBoost fraud/litigation risk scorer.

Features capture:
  - Case volume and types
  - Ownership transfer frequency (rapid transfers = fraud signal)
  - Case age and duration
  - Dispute category encoding
  - Boundary dispute flags
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Feature vector schema (must match model training)
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_NAMES = [
    # Case counts
    "total_case_count",
    "active_case_count",
    "disposed_case_count",
    # Case types (one-hot)
    "has_civil_suit",
    "has_partition_suit",
    "has_boundary_dispute",
    "has_mortgage_suit",
    "has_revenue_case",
    "has_criminal",
    # Case age features
    "max_case_age_days",
    "avg_case_age_days",
    "oldest_case_age_days",
    # Hearing features
    "avg_days_to_next_hearing",
    "has_imminent_hearing",          # hearing within 30 days
    # Ownership features
    "ownership_transfer_count",
    "rapid_transfer_flag",           # 2+ transfers within 12 months
    "transfer_frequency_per_year",
    # Area features
    "area_acres",
    # Court level
    "has_high_court_case",
    "has_district_court_case",
    # Derived features
    "active_case_ratio",             # active / total
    "unique_courts_count",
]


@dataclass
class RiskFeatureVector:
    """Typed feature vector for the risk model."""
    # Raw data
    survey_id: Optional[UUID]
    village_name: str
    survey_number: str

    # Computed features (index-matched to FEATURE_NAMES)
    features: np.ndarray

    # Metadata
    feature_names: List[str]
    computed_at: datetime

    def to_dict(self) -> Dict[str, float]:
        return dict(zip(self.feature_names, self.features.tolist()))

    def to_dataframe(self) -> "pd.DataFrame":
        return pd.DataFrame([self.features], columns=self.feature_names)


# ─────────────────────────────────────────────────────────────────────────────
# Feature Extractor
# ─────────────────────────────────────────────────────────────────────────────
class RiskFeatureExtractor:
    """
    Extracts features from court case and ownership data for risk scoring.

    Inputs:
        - List of court cases for a survey number
        - List of ownership transfers for that survey number
        - Land record metadata

    Output:
        - RiskFeatureVector with 22 features
    """

    RAPID_TRANSFER_WINDOW_MONTHS = 12
    RAPID_TRANSFER_COUNT_THRESHOLD = 2
    IMMINENT_HEARING_DAYS = 30

    def extract(
        self,
        cases: List[Dict],
        ownership_transfers: List[Dict],
        land_record: Optional[Dict] = None,
    ) -> RiskFeatureVector:
        """
        Main extraction method. Takes raw dicts (from ORM serialization).
        Returns a feature vector ready for XGBoost inference.
        """
        now = datetime.utcnow()
        features = np.zeros(len(FEATURE_NAMES), dtype=np.float32)
        idx = {name: i for i, name in enumerate(FEATURE_NAMES)}

        # ── Case count features ──────────────────────────────────────────────
        total = len(cases)
        active = sum(1 for c in cases if c.get("status") == "active")
        disposed = sum(1 for c in cases if c.get("status") == "disposed")

        features[idx["total_case_count"]] = total
        features[idx["active_case_count"]] = active
        features[idx["disposed_case_count"]] = disposed

        # ── Case type features ───────────────────────────────────────────────
        case_types_lower = [str(c.get("case_type", "")).lower() for c in cases]

        features[idx["has_civil_suit"]] = float(any("civil suit" in t for t in case_types_lower))
        features[idx["has_partition_suit"]] = float(any("partition" in t for t in case_types_lower))
        features[idx["has_boundary_dispute"]] = float(any("boundary" in t for t in case_types_lower))
        features[idx["has_mortgage_suit"]] = float(any("mortgage" in t for t in case_types_lower))
        features[idx["has_revenue_case"]] = float(any("revenue" in t for t in case_types_lower))
        features[idx["has_criminal"]] = float(any("criminal" in t for t in case_types_lower))

        # ── Case age features ────────────────────────────────────────────────
        case_ages = []
        for c in cases:
            filing = c.get("filing_date")
            if filing:
                if isinstance(filing, str):
                    try:
                        filing = datetime.fromisoformat(filing)
                    except ValueError:
                        continue
                case_ages.append((now - filing).days)

        if case_ages:
            features[idx["max_case_age_days"]] = max(case_ages)
            features[idx["avg_case_age_days"]] = float(np.mean(case_ages))
            features[idx["oldest_case_age_days"]] = max(case_ages)
        else:
            features[idx["max_case_age_days"]] = 0
            features[idx["avg_case_age_days"]] = 0
            features[idx["oldest_case_age_days"]] = 0

        # ── Hearing features ─────────────────────────────────────────────────
        hearing_gaps = []
        has_imminent = False
        for c in cases:
            if c.get("status") != "active":
                continue
            nh = c.get("next_hearing")
            if nh:
                if isinstance(nh, str):
                    try:
                        nh = datetime.fromisoformat(nh)
                    except ValueError:
                        continue
                gap = (nh - now).days
                if 0 <= gap <= self.IMMINENT_HEARING_DAYS:
                    has_imminent = True
                hearing_gaps.append(max(gap, 0))

        features[idx["avg_days_to_next_hearing"]] = float(np.mean(hearing_gaps)) if hearing_gaps else 365
        features[idx["has_imminent_hearing"]] = float(has_imminent)

        # ── Ownership features ───────────────────────────────────────────────
        transfer_count = len(ownership_transfers)
        features[idx["ownership_transfer_count"]] = transfer_count

        # Rapid transfer detection: 2+ transfers within 12 months
        rapid = self._detect_rapid_transfers(ownership_transfers)
        features[idx["rapid_transfer_flag"]] = float(rapid)

        # Transfer frequency per year (over last 5 years)
        recent_transfers = [
            t for t in ownership_transfers
            if t.get("from_date") and
            (now - self._parse_date(t["from_date"])).days <= 365 * 5
        ]
        years = 5.0
        features[idx["transfer_frequency_per_year"]] = len(recent_transfers) / years

        # ── Land area ────────────────────────────────────────────────────────
        features[idx["area_acres"]] = float(land_record.get("area_acres", 0) or 0) if land_record else 0

        # ── Court level ──────────────────────────────────────────────────────
        court_names_lower = [str(c.get("court_name", "")).lower() for c in cases]
        features[idx["has_high_court_case"]] = float(any("high court" in n for n in court_names_lower))
        features[idx["has_district_court_case"]] = float(any("district court" in n for n in court_names_lower))

        # ── Derived features ─────────────────────────────────────────────────
        features[idx["active_case_ratio"]] = (active / total) if total > 0 else 0.0
        features[idx["unique_courts_count"]] = float(len(set(c.get("court_name", "") for c in cases)))

        return RiskFeatureVector(
            survey_id=None,
            village_name="",
            survey_number="",
            features=features,
            feature_names=FEATURE_NAMES,
            computed_at=now,
        )

    def _detect_rapid_transfers(self, transfers: List[Dict]) -> bool:
        """Return True if 2+ transfers happened within RAPID_TRANSFER_WINDOW_MONTHS."""
        dates = []
        for t in transfers:
            d = t.get("from_date")
            if d:
                parsed = self._parse_date(d)
                if parsed:
                    dates.append(parsed)

        dates.sort()
        window = timedelta(days=self.RAPID_TRANSFER_WINDOW_MONTHS * 30)
        for i in range(len(dates)):
            count = sum(1 for d in dates[i:] if d - dates[i] <= window)
            if count >= self.RAPID_TRANSFER_COUNT_THRESHOLD:
                return True
        return False

    @staticmethod
    def _parse_date(d) -> Optional[datetime]:
        if isinstance(d, datetime):
            return d
        if isinstance(d, str):
            try:
                return datetime.fromisoformat(d)
            except ValueError:
                return None
        return None


# Allow import of timedelta used in _detect_rapid_transfers
from datetime import timedelta  # noqa: E402 (intentional)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Level Thresholds
# ─────────────────────────────────────────────────────────────────────────────
def score_to_risk_level(score: float) -> str:
    """Map numeric risk score 0-100 to categorical risk level."""
    if score < 25:
        return "low"
    elif score < 50:
        return "medium"
    elif score < 75:
        return "high"
    else:
        return "critical"


def risk_level_to_label(level: str, language: str = "en") -> str:
    """Return localized risk level label."""
    LABELS = {
        "en": {"low": "Low Risk", "medium": "Medium Risk", "high": "High Risk", "critical": "Critical Risk"},
        "ta": {"low": "குறைந்த அபாயம்", "medium": "நடுத்தர அபாயம்", "high": "அதிக அபாயம்", "critical": "மிக அதிக அபாயம்"},
        "hi": {"low": "कम जोखिम", "medium": "मध्यम जोखिम", "high": "उच्च जोखिम", "critical": "गंभीर जोखिम"},
    }
    return LABELS.get(language, LABELS["en"]).get(level, level)
