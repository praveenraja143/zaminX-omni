"""
src/config.py
=============
Loads application settings from environment variables.
Uses Pydantic Settings for type-safe configuration with .env support.
Supports both SQLite (dev) and PostgreSQL (prod).
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Master application settings."""

    # App
    app_name: str = "Zamin X"
    app_version: str = "2.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = True
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, alias="PORT")
    secret_key: str = Field(default="dev-secret-change-in-prod", alias="SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    rate_limit_per_minute: int = 60

    # Allowed origins for CORS
    allowed_origins: List[str] = ["*"]

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./zaminx_dev.db",
        alias="DATABASE_URL",
    )

    # Groq AI
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = "llama-3.3-70b-versatile"

    # Indian Kanoon
    indian_kanoon_token: str = Field(default="", alias="INDIAN_KANOON_TOKEN")
    indian_kanoon_base_url: str = "https://api.indiankanoon.org"

    # Polygon Blockchain
    polygon_rpc_url: str = Field(default="https://rpc-mumbai.maticvigil.com", alias="POLYGON_RPC_URL")
    polygon_chain_id: int = Field(default=80001, alias="POLYGON_CHAIN_ID")

    # Feature Flags
    feature_blockchain: bool = False
    feature_voice_input: bool = False
    feature_b2b_api: bool = True

    # Supported languages
    supported_languages: List[str] = ["en", "ta", "hi", "ml"]
    default_language: str = "en"

    # Supported cities (Phase 1: 5 TN cities)
    supported_districts: List[str] = [
        "Erode", "Coimbatore", "Salem", "Namakkal", "Tiruppur"
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def db_url(self) -> str:
        return self.database_url


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance — called once per process."""
    return Settings()


# Convenience alias used throughout the codebase
settings = get_settings()
