"""
api/app.py
==========
Zamin X v2 — FastAPI application.
Serves both the API and the React frontend (in production).
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import settings
from src.database import close_db, init_db

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logger.info("Starting Zamin X API v%s (env=%s)", settings.app_version, settings.environment)
    await init_db()
    logger.info("Database initialized (%s)", "SQLite" if settings.is_sqlite else "PostgreSQL")
    logger.info("Groq LLM: %s", "enabled" if settings.groq_api_key else "disabled")
    logger.info("Indian Kanoon: %s", "enabled" if settings.indian_kanoon_token else "disabled")
    logger.info("Zamin X API ready on %s:%d", settings.api_host, settings.api_port)
    yield
    await close_db()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Zamin X — Land Litigation Intelligence API",
    description="AI-powered land verification platform for India",
    version=settings.app_version,
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


# ── Import and register routers ───────────────────────────────────────────────
from api.routers import search_router, auth_router, land_router, i18n_router

app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(search_router.router, prefix="/api", tags=["Land Search"])
app.include_router(land_router.router, prefix="/api/land", tags=["Land Records"])
app.include_router(i18n_router.router, prefix="/api/i18n", tags=["Translations"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "app": "Zamin X",
        "version": settings.app_version,
        "tagline": "Know your land. Know its truth.",
        "docs": "/docs",
        "status": "operational",
    }


@app.get("/api/health", tags=["Health"])
async def health():
    from datetime import datetime
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "groq_llm": bool(settings.groq_api_key),
            "indian_kanoon": bool(settings.indian_kanoon_token),
            "database": "sqlite" if settings.is_sqlite else "postgresql",
        },
        "supported_districts": settings.supported_districts,
        "supported_languages": settings.supported_languages,
    }
