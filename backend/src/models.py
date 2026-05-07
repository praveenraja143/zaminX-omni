"""
src/models.py
=============
SQLAlchemy ORM models for Zamin X.
Supports both SQLite (dev) and PostgreSQL (prod).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint, JSON, func,
)
from sqlalchemy.orm import relationship

from src.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    user_id = Column(String(36), primary_key=True, default=gen_uuid)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=True)
    password_hash = Column(String(200), nullable=True)
    state = Column(String(50), default="TN")
    language = Column(String(5), default="en")
    subscription_tier = Column(String(20), default="free")
    is_active = Column(Boolean, default=True)
    searches_this_month = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class LandRecord(Base):
    __tablename__ = "land_records"
    __table_args__ = (
        UniqueConstraint("state", "district", "village_name", "survey_number", name="uq_land_parcel"),
    )
    survey_id = Column(String(36), primary_key=True, default=gen_uuid)
    state = Column(String(50), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    taluk = Column(String(100), nullable=True)
    village_name = Column(String(200), nullable=False)
    survey_number = Column(String(50), nullable=False)
    sub_division = Column(String(50), nullable=True)
    area_acres = Column(Float, nullable=True)
    land_type = Column(String(100), nullable=True)
    patta_number = Column(String(100), nullable=True)
    owner_name = Column(String(300), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    court_cases = relationship("CourtCase", back_populates="land_record", cascade="all, delete-orphan")
    fraud_scores = relationship("FraudScore", back_populates="land_record", cascade="all, delete-orphan")


class CourtCase(Base):
    __tablename__ = "court_cases"
    case_id = Column(String(36), primary_key=True, default=gen_uuid)
    survey_id = Column(String(36), ForeignKey("land_records.survey_id"), nullable=False, index=True)
    case_number = Column(String(100), nullable=False)
    court_name = Column(String(300), nullable=False)
    case_type = Column(String(100), nullable=True)
    petitioner = Column(String(500), nullable=True)
    respondent = Column(String(500), nullable=True)
    filing_date = Column(String(50), nullable=True)
    next_hearing = Column(String(50), nullable=True)
    status = Column(String(20), default="active", index=True)
    stage = Column(String(200), nullable=True)
    judge_name = Column(String(300), nullable=True)
    state = Column(String(50), nullable=True)
    district = Column(String(100), nullable=True)
    source = Column(String(50), default="mock")
    doc_id = Column(String(200), nullable=True)
    headline = Column(Text, nullable=True)
    order_text = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    ai_summary_ta = Column(Text, nullable=True)
    ai_summary_hi = Column(Text, nullable=True)
    ai_summary_ml = Column(Text, nullable=True)
    risk_contribution = Column(Float, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    land_record = relationship("LandRecord", back_populates="court_cases")


class FraudScore(Base):
    __tablename__ = "fraud_scores"
    score_id = Column(String(36), primary_key=True, default=gen_uuid)
    survey_id = Column(String(36), ForeignKey("land_records.survey_id"), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)
    case_count = Column(Integer, default=0)
    active_case_count = Column(Integer, default=0)
    risk_factors = Column(JSON, nullable=True)
    risk_summary = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    is_safe_to_buy = Column(Boolean, nullable=True)
    model_version = Column(String(20), default="v2")
    computed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    land_record = relationship("LandRecord", back_populates="fraud_scores")


class SearchHistory(Base):
    __tablename__ = "search_history"
    search_id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    owner_name = Column(String(300), nullable=True)
    district = Column(String(100), nullable=True)
    taluk = Column(String(100), nullable=True)
    village = Column(String(200), nullable=True)
    survey_number = Column(String(50), nullable=True)
    mobile_number = Column(String(15), nullable=True)
    language = Column(String(5), default="en")
    cases_found = Column(Integer, default=0)
    risk_score = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    searched_at = Column(DateTime, default=datetime.utcnow)


class BlockchainRecord(Base):
    __tablename__ = "blockchain_records"
    bc_id = Column(String(36), primary_key=True, default=gen_uuid)
    survey_id = Column(String(36), nullable=True, index=True)
    data_hash = Column(String(66), nullable=False)
    tx_hash = Column(String(66), nullable=True, index=True)
    chain = Column(String(50), default="polygon_mumbai")
    status = Column(String(20), default="pending")
    anchored_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
