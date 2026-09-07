"""
Client Interest Vector & Personalization Engine.
Ranks feeds naturally based on user reading habits, target locations, and decision tools used.
Follows the principle: 'Personalization without creepiness' (e.g. 'İlgi Alanlarınıza Göre').
"""

from typing import Dict, List, Any
from intelligence.models import IntelligenceArticle, UserInterestVector


class PersonalizationEngine:
    """Calculates article relevance against client interest profile."""

    def rank_feed_for_user(
        self,
        articles: List[IntelligenceArticle],
        user_vector: Dict[str, Any] = None
    ) -> List[IntelligenceArticle]:
        """Ranks articles based on importance, freshness, and client profile."""
        if not user_vector or not articles:
            return articles

        fav_topics = user_vector.get("topics", {})
        fav_locs = user_vector.get("locations", {})

        def compute_score(art: IntelligenceArticle) -> float:
            score = 1.0  # Base weight
            # Topic affinity
            for t in art.topics:
                if t.name in fav_topics:
                    score += fav_topics[t.name] * 1.5
            # Location affinity
            for loc in art.locations:
                if loc.name in fav_locs:
                    score += fav_locs[loc.name] * 2.0
            # Quality & confidence factor
            score *= (art.quality_score / 100.0)
            return score

        return sorted(articles, key=compute_score, reverse=True)
