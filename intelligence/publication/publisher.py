"""
Publication and Quality Gate Engine.
Ensures only verified, high-quality, non-hallucinated articles pass into production.
"""

from typing import List, Tuple
from intelligence.models import IntelligenceArticle, ContentStatus
from intelligence.db import save_article, get_published_articles
from intelligence.publication.legacy_exporter import export_to_legacy_json


class Publisher:
    """Gates and publishes intelligence articles."""

    MIN_QUALITY_THRESHOLD = 70

    def publish_articles(self, articles: List[IntelligenceArticle]) -> Tuple[int, int]:
        """
        Validates quality and publishes articles.
        Returns: (published_count, rejected_count)
        """
        published = 0
        rejected = 0

        for art in articles:
            # Quality Gate
            if art.quality_score < self.MIN_QUALITY_THRESHOLD or art.confidence_score < 0.65:
                art.status = ContentStatus.DRAFT
                print(f"[REJECTED] Article '{art.title[:40]}' scored {art.quality_score} (below {self.MIN_QUALITY_THRESHOLD})")
                rejected += 1
            else:
                art.status = ContentStatus.PUBLISHED
                if save_article(art):
                    published += 1
                else:
                    rejected += 1

        # Synchronize legacy JSON cache
        all_published = get_published_articles(limit=50)
        export_to_legacy_json(all_published)

        return published, rejected
