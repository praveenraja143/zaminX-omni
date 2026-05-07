"""
api/routers/i18n_router.py
===========================
Translation endpoint for the frontend.
"""

from fastapi import APIRouter
from src.i18n.translations import get_all_translations, TRANSLATIONS

router = APIRouter()


@router.get("/translations/{lang}")
async def get_translations(lang: str):
    if lang not in ["en", "ta", "hi", "ml"]:
        lang = "en"
    return {"language": lang, "translations": get_all_translations(lang)}


@router.get("/languages")
async def get_languages():
    return {
        "languages": [
            {"code": "en", "name": "English", "native": "English"},
            {"code": "ta", "name": "Tamil", "native": "தமிழ்"},
            {"code": "hi", "name": "Hindi", "native": "हिन्दी"},
            {"code": "ml", "name": "Malayalam", "native": "മലയാളം"},
        ]
    }
