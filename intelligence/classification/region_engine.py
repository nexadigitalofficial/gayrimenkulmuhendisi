"""
Regional and Location Intelligence Engine.
Detects mentions of provinces, districts, and neighborhoods with a primary focus on Ankara and luxury corridors.
"""

import re
from typing import List
from intelligence.models import RegionEntity


# Ankara and surrounding primary regions with hierarchy
LOCATIONS_DB = {
    # Districts & Key Luxury Hubs
    "Beytepe": {"type": "district", "parent": "Çankaya"},
    "İncek": {"type": "district", "parent": "Gölbaşı"},
    "Çayyolu": {"type": "district", "parent": "Çankaya"},
    "Yaşamkent": {"type": "district", "parent": "Çankaya"},
    "Alacaatlı": {"type": "district", "parent": "Çankaya"},
    "GOP": {"type": "neighborhood", "parent": "Çankaya"},
    "Gaziosmanpaşa": {"type": "neighborhood", "parent": "Çankaya"},
    "Çankaya": {"type": "district", "parent": "Ankara"},
    "Gölbaşı": {"type": "district", "parent": "Ankara"},
    "Etimesgut": {"type": "district", "parent": "Ankara"},
    "Batı Sitesi": {"type": "neighborhood", "parent": "Yenimahalle"},
    "Yenimahalle": {"type": "district", "parent": "Ankara"},
    "Sincan": {"type": "district", "parent": "Ankara"},
    "Çubuk": {"type": "district", "parent": "Ankara"},
    "Ankara": {"type": "province", "parent": "Türkiye"},
    "İstanbul": {"type": "province", "parent": "Türkiye"},
    "İzmir": {"type": "province", "parent": "Türkiye"},
    "Antalya": {"type": "province", "parent": "Türkiye"},
    "Muğla": {"type": "province", "parent": "Türkiye"},
    "Eskişehir": {"type": "province", "parent": "Türkiye"},
    "Kırıkkale": {"type": "province", "parent": "Türkiye"},
    "Türkiye": {"type": "country", "parent": None}
}


class RegionEngine:
    """Extracts geographic entities and assigns relevance scores."""

    def extract_locations(self, text: str) -> List[RegionEntity]:
        text_lower = text.lower()
        extracted: List[RegionEntity] = []

        for name, meta in LOCATIONS_DB.items():
            pattern = r'\b' + re.escape(name.lower()) + r'\b'
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                # District gets higher specific weight than broad province
                type_weight = 1.0 if meta["type"] in ("district", "neighborhood") else 0.75
                relevance = min((0.50 + (matches * 0.15)) * type_weight, 1.0)
                extracted.append(RegionEntity(
                    name=name,
                    type=meta["type"],
                    relevance=round(relevance, 2)
                ))

        # Default to Ankara if no specific location detected
        if not extracted:
            extracted.append(RegionEntity(name="Ankara", type="province", relevance=0.85))

        # Sort by relevance descending
        extracted.sort(key=lambda r: r.relevance, reverse=True)
        return extracted
