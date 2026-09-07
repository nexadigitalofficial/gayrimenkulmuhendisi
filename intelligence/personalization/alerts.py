"""
Proactive Intelligence Alerts Engine.
Surfaces urgent market signals and location-based opportunities without spamming.
"""

from typing import List, Dict, Any
from intelligence.models import IntelligenceArticle


class ProactiveAlertsEngine:
    """Generates non-intrusive, high-relevance alert cards for users."""

    def generate_alerts(self, articles: List[IntelligenceArticle], target_location: str = "Beytepe") -> List[Dict[str, Any]]:
        alerts = []
        target_lower = target_location.lower()

        for art in articles:
            # Check if high impact or matches target location
            is_loc_match = any(target_lower in loc.name.lower() for loc in art.locations)
            is_high_impact = art.impacts.investor_score >= 80 or art.impacts.buyer_score >= 80

            if is_loc_match or is_high_impact:
                loc_badge = art.locations[0].name.upper() if art.locations else "PİYASA SİNYALİ"
                alerts.append({
                    "id": f"alert_{art.id}",
                    "article_id": art.id,
                    "slug": art.slug,
                    "badge": loc_badge,
                    "title": art.title,
                    "summary": art.why_it_matters or art.summary[:140],
                    "impact_level": "YÜKSEK" if is_high_impact else "ORTA",
                    "confidence_percent": int(art.confidence_score * 100),
                    "cta_text": "Analizi İncele →"
                })

            if len(alerts) >= 3:
                break

        return alerts
