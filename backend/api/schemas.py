"""
api/schemas.py
==============
Pydantic v2 request and response schemas for all API endpoints.
Strict typing ensures clean API contracts and auto-generated Swagger docs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Common
# ─────────────────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────
class UserRegisterRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15, description="Mobile number with country code")
    name: Optional[str] = Field(None, max_length=200)
    state: str = Field(default="TN", max_length=50)
    language: str = Field(default="ta", pattern="^(ta|hi|en)$")
    firebase_token: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        import re
        cleaned = re.sub(r"[^0-9+]", "", v)
        if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
            raise ValueError("Invalid phone number format")
        return cleaned


class UserResponse(BaseModel):
    user_id: UUID
    phone: str
    name: Optional[str]
    state: str
    language: str
    subscription_tier: str
    searches_this_month: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


# ─────────────────────────────────────────────────────────────────────────────
# Search
# ─────────────────────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    village_name: str = Field(
        ..., min_length=2, max_length=200,
        description="Village name (Tamil Nadu, India)",
        examples=["Gobichettipalayam", "Erode", "Bhavani"],
    )
    survey_number: str = Field(
        ..., min_length=1, max_length=50,
        description="Land survey number (e.g. 123/4A)",
        examples=["123/4", "456/2A", "789"],
    )
    state: str = Field(default="TN", max_length=5, description="State code")
    language: str = Field(default="ta", pattern="^(ta|hi|en)$")

    @field_validator("survey_number")
    @classmethod
    def validate_survey(cls, v: str) -> str:
        import re
        if not re.match(r"^[0-9A-Za-z/\-\.]{1,50}$", v.strip()):
            raise ValueError("Invalid survey number format")
        return v.strip()

    @field_validator("village_name")
    @classmethod
    def validate_village(cls, v: str) -> str:
        return v.strip()


class CaseOrderSummary(BaseModel):
    order_date: Optional[str]
    judge_name: Optional[str]
    next_date: Optional[str]
    summary_tamil: Optional[str]
    summary_hindi: Optional[str]
    key_issue: Optional[str]
    urgency_level: str = "low"


class CourtCaseSummary(BaseModel):
    case_number: str
    court_name: str
    case_type: Optional[str]
    petitioner: Optional[str]
    respondent: Optional[str]
    filing_date: Optional[str]
    next_hearing: Optional[str]
    status: str
    stage: Optional[str]
    judge_name: Optional[str]
    orders: List[CaseOrderSummary] = []


class RiskAssessment(BaseModel):
    risk_score: float = Field(..., ge=0, le=100, description="Risk score 0-100")
    risk_level: str = Field(..., description="low | medium | high | critical")
    risk_factors: List[str] = []
    model_version: str = "v1"


class BlockchainBadge(BaseModel):
    verified: bool
    status: str
    polygon_tx_hash: Optional[str] = None
    fabric_block_id: Optional[int] = None
    anchored_at: Optional[str] = None
    polygonscan_url: Optional[str] = None
    message: Optional[str] = None


class OwnershipRecord(BaseModel):
    owner_name: str
    from_date: Optional[str]
    to_date: Optional[str]
    transfer_type: Optional[str]
    deed_number: Optional[str]
    is_current: bool
    blockchain_hash: Optional[str]


class LandRecordInfo(BaseModel):
    survey_id: str
    state: str
    district: Optional[str]
    taluk: Optional[str]
    village_name: str
    survey_number: str
    area_acres: Optional[float]
    patta_number: Optional[str]
    land_type: Optional[str]
    last_synced_at: Optional[str]


class SearchMetadata(BaseModel):
    total_cases: int
    active_cases: int
    disposed_cases: int
    searched_at: str
    response_time_ms: int
    language: str
    cache_hit: bool
    data_freshness: str


class SearchResponse(BaseModel):
    land_record: LandRecordInfo
    cases: List[CourtCaseSummary]
    risk_assessment: RiskAssessment
    blockchain_badge: BlockchainBadge
    ownership_chain: List[OwnershipRecord] = []
    search_metadata: SearchMetadata


# ─────────────────────────────────────────────────────────────────────────────
# OCR
# ─────────────────────────────────────────────────────────────────────────────
class OCRJobResponse(BaseModel):
    job_id: UUID
    status: str
    survey_number: Optional[str] = None
    village_name: Optional[str] = None
    patta_number: Optional[str] = None
    confidence_score: Optional[float] = None
    raw_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Risk Score
# ─────────────────────────────────────────────────────────────────────────────
class RiskScoreResponse(BaseModel):
    survey_id: UUID
    risk_score: float
    risk_level: str
    risk_factors: List[str]
    case_count: int
    active_case_count: int
    rapid_transfer_flag: bool
    model_version: str
    computed_at: datetime
    expires_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Blockchain Verification
# ─────────────────────────────────────────────────────────────────────────────
class VerifyRequest(BaseModel):
    survey_id: UUID
    case_id: Optional[UUID] = None


class VerifyResponse(BaseModel):
    survey_id: UUID
    is_verified: bool
    blockchain_hash: Optional[str]
    polygon_tx: Optional[str]
    fabric_block_id: Optional[int]
    anchored_at: Optional[datetime]
    verification_message: str


# ─────────────────────────────────────────────────────────────────────────────
# Alert Subscriptions
# ─────────────────────────────────────────────────────────────────────────────
class AlertSubscribeRequest(BaseModel):
    survey_id: UUID
    channel: str = Field(..., pattern="^(sms|whatsapp|push)$")


class AlertSubscribeResponse(BaseModel):
    subscription_id: UUID
    survey_id: UUID
    channel: str
    status: str
    message: str


# ─────────────────────────────────────────────────────────────────────────────
# B2B Bulk API
# ─────────────────────────────────────────────────────────────────────────────
class BulkSearchItem(BaseModel):
    village_name: str
    survey_number: str
    state: str = "TN"


class BulkSearchRequest(BaseModel):
    items: List[BulkSearchItem] = Field(..., min_length=1, max_length=100)
    language: str = Field(default="en", pattern="^(ta|hi|en)$")


class BulkSearchResultItem(BaseModel):
    village_name: str
    survey_number: str
    total_cases: int
    active_cases: int
    risk_score: float
    risk_level: str
    status: str  # "success" | "error"
    error: Optional[str] = None


class BulkSearchResponse(BaseModel):
    total_requested: int
    total_processed: int
    results: List[BulkSearchResultItem]
    processed_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Village Suggestions
# ─────────────────────────────────────────────────────────────────────────────
class VillageSuggestResponse(BaseModel):
    query: str
    suggestions: List[str]
    total: int
