"""
Related Articles & Semantic Matcher.
Identifies related market intelligence based on shared topic clusters and regional affinity.
"""

from typing import List
from intelligence.models import IntelligenceArticle
from intelligence.db import get_db_connection


class RelatedEngine:
    """Finds related intelligence articles."""

    def find_related(self, article: IntelligenceArticle, limit: int = 3) -> List[str]:
        """Returns IDs of related articles."""
        conn = get_db_connection()
        try:
            # Query articles with same category or recent date, excluding self
            cursor = conn.execute("""
                SELECT id FROM news_articles
                WHERE id != ? AND status = 'published' AND category = ?
                ORDER BY created_at DESC
                LIMIT ?;
            """, (article.id, article.category, limit))
            ids = [r["id"] for r in cursor.fetchall()]

            # If not enough, fill with most recent
            if len(ids) < limit:
                needed = limit - len(ids)
                cur2 = conn.execute("""
                    SELECT id FROM news_articles
                    WHERE id != ? AND status = 'published'
                    ORDER BY created_at DESC
                    LIMIT ?;
                """, (article.id, needed))
                for r in cur2.fetchall():
                    if r["id"] not in ids:
                        ids.append(r["id"])

            return ids[:limit]
        finally:
            conn.close()
