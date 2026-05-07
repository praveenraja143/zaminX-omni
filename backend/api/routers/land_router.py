"""
api/routers/land_router.py
===========================
Land records API — districts, taluks, villages dropdown data.
"""

from fastapi import APIRouter
from src.court_scrapers.tn_land_records import tn_land_fetcher

router = APIRouter()


@router.get("/districts")
async def get_districts():
    return {"districts": tn_land_fetcher.get_districts()}


@router.get("/taluks/{district}")
async def get_taluks(district: str):
    return {"district": district, "taluks": tn_land_fetcher.get_taluks(district)}


@router.get("/villages/{district}/{taluk}")
async def get_villages(district: str, taluk: str):
    return {"district": district, "taluk": taluk, "villages": tn_land_fetcher.get_villages(district, taluk)}
