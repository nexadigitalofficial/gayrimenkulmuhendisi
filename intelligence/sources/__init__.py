"""
Source registry and factory.
"""

from typing import List
from intelligence.sources.base import NewsSource
from intelligence.sources.official_sources import OfficialInstitutionalSource
from intelligence.sources.news_sources import FinancialNewsSource
from intelligence.sources.sector_sources import SectorAnalyticsSource


def get_default_sources() -> List[NewsSource]:
    """Returns the prioritized list of active data sources."""
    return [
        OfficialInstitutionalSource(),  # Priority 1: Official / Primary
        FinancialNewsSource(),          # Priority 2: Established Financial & Market News
        SectorAnalyticsSource()         # Priority 3: Specialist PropTech & Valuation
    ]
