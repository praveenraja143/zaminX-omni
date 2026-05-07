"""
src/court_scrapers/tn_land_records.py
======================================
Tamil Nadu Land Records Fetcher (Patta/Chitta)

Fetches land ownership data from TN eServices portal.
In development mode, uses comprehensive mock data for 5 supported districts.

Data Source: https://eservices.tn.gov.in/eservicesnew/land/chitta_new.html
Note: The official portal has no API — uses Playwright browser automation.
For demo/dev, mock data provides realistic Patta/Chitta records.
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PattaDetails:
    """Patta (ownership certificate) details."""
    patta_number: str
    owner_name: str
    survey_number: str
    sub_division: str
    village: str
    taluk: str
    district: str
    area_acres: float
    area_hectares: float
    land_type: str  # agricultural / residential / commercial
    classification: str  # wet / dry / garden / manavari
    last_updated: str


@dataclass
class ChittaDetails:
    """Chitta (land account) details."""
    chitta_number: str
    survey_number: str
    village: str
    taluk: str
    district: str
    total_area: float
    cultivable_area: float
    classification: str
    soil_type: str
    irrigation_source: str
    revenue_village_code: str
    last_updated: str


# ─────────────────────────────────────────────────────────────────────────────
# Tamil Nadu Administrative Data (5 Supported Districts)
# ─────────────────────────────────────────────────────────────────────────────
TN_DISTRICT_DATA = {
    "Erode": {
        "taluks": ["Erode", "Gobichettipalayam", "Bhavani", "Sathyamangalam", "Perundurai", "Anthiyur"],
        "villages": {
            "Erode": ["Erode Town", "Karungalpalayam", "Veerappanchatram", "Chithode", "Modakkurichi"],
            "Gobichettipalayam": ["Gobichettipalayam", "Bhavanisagar", "Kasipalayam", "Odasaliyur", "Kadambur"],
            "Bhavani": ["Bhavani Town", "Kumarapalayam", "Kavundapalayam", "Salangapalayam"],
            "Sathyamangalam": ["Sathyamangalam", "Thalavadi", "Bannari", "Hasanur"],
            "Perundurai": ["Perundurai", "Vijayamangalam", "Ingur", "Ellapalayam"],
            "Anthiyur": ["Anthiyur", "Ammapettai", "Bargur", "Odhimalai"],
        },
    },
    "Coimbatore": {
        "taluks": ["Coimbatore North", "Coimbatore South", "Pollachi", "Mettupalayam", "Sulur", "Valparai"],
        "villages": {
            "Coimbatore North": ["Coimbatore", "Peelamedu", "Singanallur", "Ganapathypuram", "Thudiyalur"],
            "Coimbatore South": ["R.S. Puram", "Ramanathapuram", "Nanjundapuram", "Vadavalli"],
            "Pollachi": ["Pollachi", "Anaimalai", "Negamam", "Zamin Uthukuli", "Kinathukadavu"],
            "Mettupalayam": ["Mettupalayam", "Annur", "Karamadai", "Sirumugai"],
            "Sulur": ["Sulur", "Irugur", "Perur", "Madukkarai"],
            "Valparai": ["Valparai", "Aliyar Nagar", "Sholayar"],
        },
    },
    "Salem": {
        "taluks": ["Salem", "Mettur", "Omalur", "Attur", "Yercaud", "Sankagiri"],
        "villages": {
            "Salem": ["Salem Town", "Suramangalam", "Hasthampatti", "Kondalampatti", "Ayothiyapattinam"],
            "Mettur": ["Mettur", "Mecheri", "Kolathur", "Nangavalli"],
            "Omalur": ["Omalur", "Thalaivasal", "Kadayampatti", "Valapadi"],
            "Attur": ["Attur", "Gangavalli", "Pethanaickenpalayam", "Narasingapuram"],
            "Yercaud": ["Yercaud", "Shevaroy Hills", "Manjakuttai"],
            "Sankagiri": ["Sankagiri", "Veerapandi", "Edappadi", "Magudanchavadi"],
        },
    },
    "Namakkal": {
        "taluks": ["Namakkal", "Rasipuram", "Tiruchengode", "Paramathi-Velur", "Kolli Hills"],
        "villages": {
            "Namakkal": ["Namakkal Town", "Mohanur", "Erumapalayam", "Puduchatram"],
            "Rasipuram": ["Rasipuram", "Sendamangalam", "Namagiripettai", "Mangalapuram"],
            "Tiruchengode": ["Tiruchengode", "Kumarapalayam", "Pallipalayam", "Sankari"],
            "Paramathi-Velur": ["Paramathi", "Velur", "Jedarpalayam", "Kabilarmalai"],
            "Kolli Hills": ["Semmedu", "Ariyur Nagar", "Valavanthi Nagar"],
        },
    },
    "Tiruppur": {
        "taluks": ["Tiruppur North", "Tiruppur South", "Avinashi", "Palladam", "Dharapuram", "Kangayam", "Udumalaipettai"],
        "villages": {
            "Tiruppur North": ["Tiruppur", "Angeripalayam", "Mangalam", "Nallur"],
            "Tiruppur South": ["Avinashi Road", "Perumanallur", "Uthukuli", "Vellakoil"],
            "Avinashi": ["Avinashi", "Chennimalai", "Gudimangalam"],
            "Palladam": ["Palladam", "Pongalur", "Madathukulam"],
            "Dharapuram": ["Dharapuram", "Mulanur", "Kunnathur"],
            "Kangayam": ["Kangayam", "Vellakovil", "Nathakadaiyur"],
            "Udumalaipettai": ["Udumalaipettai", "Madathukulam", "Gudalur"],
        },
    },
}

# Tamil names for owner generation
TAMIL_FIRST_NAMES = [
    "Murugesan", "Selvam", "Ramasamy", "Govindasamy", "Palaniappan",
    "Senthil", "Karuppaiya", "Lakshmi", "Meena", "Tamilarasi",
    "Rangadurai", "Velmurugan", "Manikandan", "Prabhu", "Anandhi",
    "Krishnan", "Sundaram", "Perumal", "Karuppiah", "Thangam",
]

TAMIL_FATHER_NAMES = [
    "Ramu", "Selvam", "Govindan", "Kannan", "Muthusamy",
    "Palanisamy", "Karuppan", "Chinnan", "Subramani", "Velan",
]

LAND_TYPES = ["Nanjai (Wet)", "Punjai (Dry)", "Garden", "Manavari", "Residential", "Commercial"]
SOIL_TYPES = ["Red Soil", "Black Cotton Soil", "Alluvial", "Laterite", "Sandy Loam"]
IRRIGATION = ["Well", "Canal", "River", "Rain-fed", "Bore Well", "Tank"]


class TNLandRecordsFetcher:
    """
    Fetches Patta/Chitta data for Tamil Nadu land parcels.
    Uses mock data in development, Playwright scraping in production.
    """

    def __init__(self):
        self.mock_mode = True  # Always mock for now; Playwright scraping for Phase 2

    def get_districts(self) -> List[str]:
        """Return supported districts."""
        return list(TN_DISTRICT_DATA.keys())

    def get_taluks(self, district: str) -> List[str]:
        """Return taluks for a district."""
        return TN_DISTRICT_DATA.get(district, {}).get("taluks", [])

    def get_villages(self, district: str, taluk: str) -> List[str]:
        """Return villages for a taluk."""
        return TN_DISTRICT_DATA.get(district, {}).get("villages", {}).get(taluk, [])

    async def get_patta_details(
        self,
        district: str,
        taluk: str,
        village: str,
        survey_no: str,
    ) -> Optional[PattaDetails]:
        """Fetch Patta details for a specific land parcel."""
        if self.mock_mode:
            return self._generate_mock_patta(district, taluk, village, survey_no)

        # TODO Phase 2: Playwright scraping of eservices.tn.gov.in
        return None

    async def get_chitta_details(
        self,
        district: str,
        taluk: str,
        village: str,
        survey_no: str,
    ) -> Optional[ChittaDetails]:
        """Fetch Chitta details for a specific land parcel."""
        if self.mock_mode:
            return self._generate_mock_chitta(district, taluk, village, survey_no)
        return None

    def _generate_mock_patta(
        self, district: str, taluk: str, village: str, survey_no: str
    ) -> PattaDetails:
        """Generate realistic mock Patta data."""
        random.seed(f"patta:{district}:{village}:{survey_no}")

        fname = random.choice(TAMIL_FIRST_NAMES)
        father = random.choice(TAMIL_FATHER_NAMES)
        gender_suffix = "s/o" if fname not in ["Lakshmi", "Meena", "Tamilarasi", "Anandhi", "Thangam"] else "d/o"
        owner_name = f"{fname} {gender_suffix} {father}"

        area_acres = round(random.uniform(0.5, 15.0), 2)

        return PattaDetails(
            patta_number=f"P{random.randint(1000, 9999)}/{random.randint(2015, 2025)}",
            owner_name=owner_name,
            survey_number=survey_no,
            sub_division=random.choice(["A", "B", "1", "2", "1A", "2B", ""]),
            village=village,
            taluk=taluk,
            district=district,
            area_acres=area_acres,
            area_hectares=round(area_acres * 0.4047, 2),
            land_type=random.choice(["Agricultural", "Residential", "Commercial"]),
            classification=random.choice(LAND_TYPES),
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )

    def _generate_mock_chitta(
        self, district: str, taluk: str, village: str, survey_no: str
    ) -> ChittaDetails:
        """Generate realistic mock Chitta data."""
        random.seed(f"chitta:{district}:{village}:{survey_no}")

        total = round(random.uniform(0.5, 15.0), 2)

        return ChittaDetails(
            chitta_number=f"C{random.randint(100, 9999)}",
            survey_number=survey_no,
            village=village,
            taluk=taluk,
            district=district,
            total_area=total,
            cultivable_area=round(total * random.uniform(0.6, 0.95), 2),
            classification=random.choice(LAND_TYPES),
            soil_type=random.choice(SOIL_TYPES),
            irrigation_source=random.choice(IRRIGATION),
            revenue_village_code=f"TN{random.randint(10, 99)}{random.randint(100, 999)}",
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )


# Singleton
tn_land_fetcher = TNLandRecordsFetcher()
