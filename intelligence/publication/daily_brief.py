"""
Daily Real Estate Intelligence Brief Generator.
Produces:
- 3 Critical Developments
- 3 Important Signals
- 2 Opportunities
- 1 Risk
- Market Pulse indicators (Demand, Supply, Credit, Price, Rent)
"""

from typing import Dict, Any, List
from intelligence.models import IntelligenceArticle
from intelligence.db import get_published_articles


class DailyBriefGenerator:
    """Compiles the daily flagship briefing for Ankara and Turkish real estate."""

    def generate_brief(self, articles: List[IntelligenceArticle] = None) -> Dict[str, Any]:
        if articles is None:
            articles = get_published_articles(limit=10)

        critical_devs = []
        important_signals = []
        opportunities = []
        risks = []

        for art in articles:
            item = {
                "id": art.id,
                "slug": art.slug,
                "title": art.title,
                "summary": art.why_it_matters or art.summary[:150],
                "category": art.category,
                "location": art.locations[0].name if art.locations else "Ankara",
                "impact": "Yüksek" if art.impacts.investor_score >= 80 else "Orta"
            }

            if art.impacts.buyer_score >= 80 or art.impacts.investor_score >= 85:
                if len(critical_devs) < 3:
                    critical_devs.append(item)
                elif len(important_signals) < 3:
                    important_signals.append(item)
            else:
                if len(important_signals) < 3:
                    important_signals.append(item)

            # Collect unique opportunities & risks
            for opp in art.opportunities:
                if opp not in opportunities and len(opportunities) < 2:
                    opportunities.append(opp)
            for rk in art.risks:
                if rk not in risks and len(risks) < 1:
                    risks.append(rk)

        # Fallbacks if quiet news day
        if not critical_devs and articles:
            critical_devs.append({
                "id": articles[0].id,
                "slug": articles[0].slug,
                "title": articles[0].title,
                "summary": articles[0].summary[:140],
                "category": articles[0].category,
                "location": "Ankara",
                "impact": "Önemli"
            })

        if not opportunities:
            opportunities = [
                "Lansman aşamasındaki konut projelerinde doğrudan geliştirici vadeli alım avantajı",
                "Altyapı yatırımları hızlanan batı aksında değer artışı potansiyeli"
            ]
        if not risks:
            risks = ["Yüksek faiz ortamında plansız kredi borçlanması riski"]

        # Market pulse indicators
        market_pulse = {
            "credit_condition": "Temkinli / Yüksek Faiz (Doğrudan Vadeli Seçenekler Önde)",
            "housing_demand": "Canlı (Özellikle Beytepe, İncek, Çankaya Lüks Segment)",
            "price_trend": "Nominal Artış / Reel Dengelenme",
            "rental_yield": "%6.8 - %7.5 Brüt Getiri (Doluluk %98)",
            "land_interest": "Güçlü (Gölbaşı - İncek - Alacaatlı Villa Parselleri)"
        }

        return {
            "date_display": "Bugün",
            "headline": "Bugün Gayrimenkul Piyasasında Bilmeniz Gerekenler",
            "summary_card": f"Bugün piyasada {len(critical_devs)} kritik gelişme ve {len(important_signals)} önemli piyasa sinyali izleniyor.",
            "critical_developments": critical_devs,
            "important_signals": important_signals,
            "key_opportunities": opportunities,
            "primary_risk": risks[0] if risks else "Piyasa dalgalanmaları",
            "market_pulse": market_pulse
        }
