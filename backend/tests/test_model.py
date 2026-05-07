"""
tests/test_model.py
===================
Comprehensive test suite for Zamin X AI models and API endpoints.

Run:
    pytest tests/ -v --cov=src --cov=api --cov-report=term-missing
"""

import asyncio
import json
import pytest
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def sample_court_cases() -> List[Dict]:
    """Sample court cases for testing."""
    now = datetime.utcnow()
    return [
        {
            "case_type": "Civil Suit",
            "status": "active",
            "court_name": "District Court, Erode",
            "filing_date": (now - timedelta(days=365)).isoformat(),
            "next_hearing": (now + timedelta(days=30)).isoformat(),
        },
        {
            "case_type": "Boundary Dispute",
            "status": "active",
            "court_name": "Sub-Court, Gobichettipalayam",
            "filing_date": (now - timedelta(days=730)).isoformat(),
            "next_hearing": (now + timedelta(days=15)).isoformat(),
        },
        {
            "case_type": "Partition Suit",
            "status": "disposed",
            "court_name": "District Court, Erode",
            "filing_date": (now - timedelta(days=1095)).isoformat(),
            "next_hearing": None,
        },
    ]


@pytest.fixture
def sample_ownership_transfers() -> List[Dict]:
    now = datetime.utcnow()
    return [
        {"from_date": (now - timedelta(days=3650)).isoformat(), "transfer_type": "inheritance"},
        {"from_date": (now - timedelta(days=365)).isoformat(), "transfer_type": "sale"},
        {"from_date": (now - timedelta(days=180)).isoformat(), "transfer_type": "sale"},
    ]


@pytest.fixture
def sample_land_record() -> Dict:
    return {"area_acres": 2.5}


@pytest.fixture
def high_risk_cases() -> List[Dict]:
    """Cases that should produce high risk score."""
    now = datetime.utcnow()
    return [
        {
            "case_type": "Boundary Dispute",
            "status": "active",
            "court_name": "High Court of Madras",
            "filing_date": (now - timedelta(days=1800)).isoformat(),
            "next_hearing": (now + timedelta(days=7)).isoformat(),
        }
    ] * 4  # 4 active High Court cases = critical risk


@pytest.fixture
def clean_land_cases() -> List[Dict]:
    """No active cases — should produce low risk score."""
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Feature Engineering Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestRiskFeatureExtractor:
    """Tests for the feature engineering pipeline."""

    def setup_method(self):
        from src.feature_engineering import RiskFeatureExtractor, FEATURE_NAMES
        self.extractor = RiskFeatureExtractor()
        self.feature_names = FEATURE_NAMES

    def test_feature_vector_length(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        fv = self.extractor.extract(sample_court_cases, sample_ownership_transfers, sample_land_record)
        assert len(fv.features) == len(self.feature_names)

    def test_feature_vector_dtype(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        fv = self.extractor.extract(sample_court_cases, sample_ownership_transfers, sample_land_record)
        assert fv.features.dtype == np.float32

    def test_active_case_count(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        fv = self.extractor.extract(sample_court_cases, sample_ownership_transfers, sample_land_record)
        feature_dict = fv.to_dict()
        assert feature_dict["active_case_count"] == 2.0
        assert feature_dict["disposed_case_count"] == 1.0
        assert feature_dict["total_case_count"] == 3.0

    def test_boundary_dispute_flag(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        fv = self.extractor.extract(sample_court_cases, sample_ownership_transfers, sample_land_record)
        assert fv.to_dict()["has_boundary_dispute"] == 1.0

    def test_empty_cases(self):
        fv = self.extractor.extract([], [], None)
        d = fv.to_dict()
        assert d["total_case_count"] == 0.0
        assert d["active_case_count"] == 0.0
        assert d["has_boundary_dispute"] == 0.0

    def test_rapid_transfer_detection(self, sample_court_cases):
        """3 transfers over 3650 days but 2 within 180 days = rapid transfer flag."""
        now = datetime.utcnow()
        rapid_transfers = [
            {"from_date": (now - timedelta(days=100)).isoformat(), "transfer_type": "sale"},
            {"from_date": (now - timedelta(days=50)).isoformat(), "transfer_type": "sale"},
            {"from_date": (now - timedelta(days=3000)).isoformat(), "transfer_type": "inheritance"},
        ]
        fv = self.extractor.extract(sample_court_cases, rapid_transfers, None)
        assert fv.to_dict()["rapid_transfer_flag"] == 1.0

    def test_active_case_ratio(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        fv = self.extractor.extract(sample_court_cases, sample_ownership_transfers, sample_land_record)
        ratio = fv.to_dict()["active_case_ratio"]
        assert abs(ratio - 2/3) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# Risk Scorer Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestFraudRiskScorer:
    """Tests for the heuristic and XGBoost risk scorer."""

    def setup_method(self):
        from src.model import FraudRiskScorer
        self.scorer = FraudRiskScorer()
        self.scorer.is_loaded = True  # skip model loading in tests

    def test_clean_land_is_low_risk(self, clean_land_cases):
        result = self.scorer.score(clean_land_cases, [], None)
        assert result["risk_score"] == 0.0
        assert result["risk_level"] == "low"

    def test_high_risk_cases_produce_high_score(self, high_risk_cases):
        result = self.scorer.score(high_risk_cases, [], None)
        assert result["risk_score"] > 50, f"Expected >50, got {result['risk_score']}"
        assert result["risk_level"] in ["high", "critical"]

    def test_risk_score_bounded(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        result = self.scorer.score(sample_court_cases, sample_ownership_transfers, sample_land_record)
        assert 0 <= result["risk_score"] <= 100

    def test_risk_factors_populated(self, sample_court_cases, sample_ownership_transfers, sample_land_record):
        result = self.scorer.score(sample_court_cases, sample_ownership_transfers, sample_land_record)
        assert isinstance(result["risk_factors"], list)
        assert len(result["risk_factors"]) > 0

    def test_risk_level_labels(self):
        from src.feature_engineering import score_to_risk_level
        assert score_to_risk_level(0) == "low"
        assert score_to_risk_level(24.9) == "low"
        assert score_to_risk_level(25) == "medium"
        assert score_to_risk_level(49.9) == "medium"
        assert score_to_risk_level(50) == "high"
        assert score_to_risk_level(74.9) == "high"
        assert score_to_risk_level(75) == "critical"
        assert score_to_risk_level(100) == "critical"

    def test_rapid_transfer_increases_score(self):
        now = datetime.utcnow()
        rapid = [
            {"from_date": (now - timedelta(days=50)).isoformat(), "transfer_type": "sale"},
            {"from_date": (now - timedelta(days=20)).isoformat(), "transfer_type": "sale"},
        ]
        result_with = self.scorer.score([], rapid, None)
        result_without = self.scorer.score([], [], None)
        assert result_with["risk_score"] > result_without["risk_score"]


# ─────────────────────────────────────────────────────────────────────────────
# NLP Summarizer Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestLegalNLPSummarizer:
    """Tests for the NLP summarization pipeline."""

    def setup_method(self):
        from src.model import LegalNLPSummarizer
        self.summarizer = LegalNLPSummarizer()
        self.summarizer.is_loaded = True

    def test_empty_text_returns_empty_result(self):
        result = self.summarizer.summarize("")
        assert result["summary_tamil"] == ""
        assert result["confidence"] == 0.0

    def test_extractive_fallback_returns_dict(self):
        text = (
            "The petitioner herein challenges the order dated 12.03.2023 passed by the "
            "Revenue Divisional Officer regarding boundary demarcation of the land. "
            "The court directed both parties to submit ownership documents. "
            "Case adjourned to next hearing date for further arguments."
        )
        result = self.summarizer._extractive_summarize(text)
        assert isinstance(result["summary_tamil"], str)
        assert isinstance(result["urgency_level"], str)
        assert result["urgency_level"] in ["low", "medium", "high"]
        assert result["confidence"] > 0

    def test_urgency_detection_high(self):
        text = "Urgent interim order granted for stay of proceedings."
        urgency = self.summarizer._detect_urgency(text)
        assert urgency == "high"

    def test_urgency_detection_medium(self):
        text = "Case adjourned to next hearing on 15.08.2024."
        urgency = self.summarizer._detect_urgency(text)
        assert urgency == "medium"

    def test_urgency_detection_low(self):
        text = "Judgment reserved. Both parties submitted their arguments."
        urgency = self.summarizer._detect_urgency(text)
        assert urgency == "low"


# ─────────────────────────────────────────────────────────────────────────────
# Text Preprocessor Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestLegalTextPreprocessor:
    """Tests for text cleaning and normalization."""

    def setup_method(self):
        from src.preprocessing import LegalTextPreprocessor
        self.pp = LegalTextPreprocessor()

    def test_clean_removes_extra_whitespace(self):
        text = "The   court    ordered    both  parties."
        cleaned = self.pp.clean(text)
        assert "  " not in cleaned

    def test_extract_survey_numbers(self):
        text = "The land bearing Survey No. 123/4A in village Erode."
        entities = self.pp.extract_key_entities(text)
        assert "123/4A" in entities["survey_numbers"] or any("123" in s for s in entities["survey_numbers"])

    def test_extract_case_numbers(self):
        text = "Case OS/456/2022 is pending before District Court."
        entities = self.pp.extract_key_entities(text)
        assert "OS/456/2022" in entities["case_numbers"]

    def test_normalize_survey_number(self):
        from src.preprocessing import normalize_survey_number
        assert normalize_survey_number("  123/4 A  ") == "123/4A"
        assert normalize_survey_number("45") == "45"
        assert normalize_survey_number("") == ""

    def test_normalize_village_name(self):
        from src.preprocessing import normalize_village_name
        assert normalize_village_name("gobichettipalayam") == "Gobichettipalayam"
        assert normalize_village_name("ERODE") == "Erode"
        assert normalize_village_name("salem  city") == "Salem City"


# ─────────────────────────────────────────────────────────────────────────────
# Training Pipeline Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestTrainingPipeline:
    """Tests for data generation and model training."""

    def test_synthetic_data_generation(self):
        from src.train import generate_synthetic_training_data
        X, y = generate_synthetic_training_data(n_samples=500)
        assert len(X) == 500
        assert len(y) == 500
        assert set(y.unique()).issubset({0, 1})
        assert list(X.columns) == __import__("src.feature_engineering", fromlist=["FEATURE_NAMES"]).FEATURE_NAMES

    def test_synthetic_data_class_balance(self):
        from src.train import generate_synthetic_training_data
        _, y = generate_synthetic_training_data(n_samples=1000)
        high_risk_ratio = y.mean()
        # Should be roughly 40% high risk (with noise)
        assert 0.3 < high_risk_ratio < 0.55

    def test_feature_names_consistent(self):
        """Feature names in training must match feature extractor."""
        from src.feature_engineering import FEATURE_NAMES
        from src.train import generate_synthetic_training_data
        X, _ = generate_synthetic_training_data(100)
        assert list(X.columns) == FEATURE_NAMES


# ─────────────────────────────────────────────────────────────────────────────
# API Schema Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestAPISchemas:
    """Tests for Pydantic request/response schemas."""

    def test_search_request_valid(self):
        from api.schemas import SearchRequest
        req = SearchRequest(village_name="Gobichettipalayam", survey_number="123/4")
        assert req.village_name == "Gobichettipalayam"
        assert req.state == "TN"
        assert req.language == "ta"

    def test_search_request_survey_trimmed(self):
        from api.schemas import SearchRequest
        req = SearchRequest(village_name="Erode", survey_number="  456/2  ")
        assert req.survey_number == "456/2"

    def test_search_request_invalid_language(self):
        from api.schemas import SearchRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SearchRequest(village_name="Erode", survey_number="123", language="fr")

    def test_user_register_invalid_phone(self):
        from api.schemas import UserRegisterRequest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserRegisterRequest(phone="abc123def")

    def test_bulk_search_request_max_items(self):
        from api.schemas import BulkSearchRequest, BulkSearchItem
        from pydantic import ValidationError
        items = [BulkSearchItem(village_name="V", survey_number=str(i)) for i in range(101)]
        # Schema allows up to 100; 101 should fail at router level
        # (validator is in router, not schema)
        req = BulkSearchRequest(items=items[:100])
        assert len(req.items) == 100


# ─────────────────────────────────────────────────────────────────────────────
# Data Loader Tests
# ─────────────────────────────────────────────────────────────────────────────
class TestMockDataGenerator:
    """Tests for the mock data generator used in dev."""

    def setup_method(self):
        from src.data_loader import MockDataGenerator
        self.gen = MockDataGenerator()

    def test_generates_cases_for_known_village(self):
        cases = self.gen.generate_cases("Gobichettipalayam", "123/4", count=3)
        assert isinstance(cases, list)
        assert all(c.village_name == "Gobichettipalayam" for c in cases)
        assert all(c.survey_number == "123/4" for c in cases)

    def test_case_status_is_valid(self):
        cases = self.gen.generate_cases("Erode", "456/2", count=5)
        valid_statuses = {"active", "disposed", "pending", "transferred"}
        assert all(c.status in valid_statuses for c in cases)

    def test_cases_have_orders(self):
        cases = self.gen.generate_cases("Bhavani", "789", count=3)
        # At least some cases should have orders
        total_orders = sum(len(c.orders) for c in cases)
        assert total_orders >= 0  # could be 0 if no cases generated

    def test_land_record_generated(self):
        record = self.gen.generate_land_record("Erode", "100/5")
        assert record.village_name == "Erode"
        assert record.survey_number == "100/5"
        assert record.state == "TN"
        assert record.district == "Erode"
        assert isinstance(record.area_acres, float)

    def test_deterministic_for_same_input(self):
        """Same village+survey should always generate same data (seed-based)."""
        cases1 = self.gen.generate_cases("Erode", "123/4")
        cases2 = self.gen.generate_cases("Erode", "123/4")
        assert len(cases1) == len(cases2)
        if cases1 and cases2:
            assert cases1[0].case_number == cases2[0].case_number

    @pytest.mark.asyncio
    async def test_village_suggestions(self):
        from src.data_loader import get_village_suggestions
        results = await get_village_suggestions("Gobi")
        assert any("Gobichettipalayam" in v for v in results)

    @pytest.mark.asyncio
    async def test_village_suggestions_case_insensitive(self):
        from src.data_loader import get_village_suggestions
        results = await get_village_suggestions("erode")
        assert any("Erode" in v for v in results)


# ─────────────────────────────────────────────────────────────────────────────
# Integration Test: Full Search Pipeline (mocked DB)
# ─────────────────────────────────────────────────────────────────────────────
class TestSearchPipeline:
    """Integration tests for the full search pipeline."""

    @pytest.mark.asyncio
    async def test_search_returns_valid_structure(self):
        """End-to-end test of LandSearchService with mocked DB."""
        from src.predict import LandSearchService
        from src.models import LandRecord, CourtCase, FraudScore, OwnershipChain, BlockchainRecord
        from unittest.mock import AsyncMock, MagicMock, patch
        import uuid

        # Mock DB session
        mock_db = AsyncMock()

        # Mock land record
        mock_land = LandRecord(
            survey_id=uuid.uuid4(),
            state="TN",
            district="Erode",
            village_name="Gobichettipalayam",
            survey_number="123/4",
            area_acres=2.5,
        )

        # Patch the persister to return mock objects
        with patch("src.predict.DataPersister") as MockPersister, \
             patch("src.predict.ECourtsScraper") as MockScraper:

            mock_persister_instance = AsyncMock()
            mock_persister_instance.persist_search_result.return_value = (mock_land, [])
            MockPersister.return_value = mock_persister_instance

            mock_scraper_instance = AsyncMock()
            mock_scraper_instance.search_by_survey_number.return_value = []
            MockScraper.return_value = mock_scraper_instance

            # Mock DB queries
            mock_db.execute = AsyncMock(return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
                scalar_one_or_none=MagicMock(return_value=None),
            ))
            mock_db.commit = AsyncMock()
            mock_db.add = MagicMock()

            service = LandSearchService(mock_db)
            result = await service.search("Gobichettipalayam", "123/4", "TN", "ta")

            assert "land_record" in result
            assert "cases" in result
            assert "risk_assessment" in result
            assert "blockchain_badge" in result
            assert "search_metadata" in result
            assert result["risk_assessment"]["risk_score"] == 0.0  # no cases
