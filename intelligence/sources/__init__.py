"""
Source registry and factory.
"""

from typing import List
from intelligence.sources.base import NewsSource
from intelligence.sources.official_sources import OfficialInstitutionalSource
from intelligence.sources.news_sources import FinancialNewsSource
from intelligence.sources.sector_sources import SectorAnalyticsSource, SpkFundIntelligenceSource


def get_default_sources() -> List[NewsSource]:
    """Returns the prioritized list of active data sources."""
    return [
        OfficialInstitutionalSource(),  # Priority 1: Official / Primary
        SpkFundIntelligenceSource(),    # Priority 2: SPK, TEFAS & Capital Markets Real Estate Radar
        FinancialNewsSource(),          # Priority 3: Established Financial & Market News
        SectorAnalyticsSource()         # Priority 4: Specialist PropTech & Valuation
    ]
