"""
Event clustering engine.
Groups overlapping news reports from multiple sources into consolidated Market Events.
"""

import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from intelligence.models import RawArticle, EventCluster
from intelligence.deduplication.simhash import is_near_duplicate
from intelligence.db import get_db_connection, _db_lock


class EventClusteringEngine:
    """Clusters articles into unified market events."""

    def cluster_articles(self, articles: List[RawArticle]) -> List[EventCluster]:
        """
        Groups articles with similar topics/titles into single canonical EventClusters.
        """
        clusters: List[Dict[str, Any]] = []

        for art in articles:
            text_to_compare = f"{art.title} {art.summary or art.content[:200]}"
            matched_cluster = None

            for cl in clusters:
                if is_near_duplicate(cl["comparison_text"], text_to_compare, threshold=0.45):
                    matched_cluster = cl
                    break

            source_entry = {
                "source_id": art.source_id,
                "source_name": art.source_name,
                "url": art.url,
                "title": art.title,
                "published_at": art.published_at or datetime.now(timezone.utc).isoformat()
            }

            if matched_cluster:
                # Add to existing cluster
                matched_cluster["articles"].append(art)
                matched_cluster["sources"].append(source_entry)
                # Keep the longest or highest quality content
                if len(art.content) > len(matched_cluster["best_article"].content):
                    matched_cluster["best_article"] = art
            else:
                clusters.append({
                    "id": f"event_{uuid.uuid4().hex[:12]}",
                    "comparison_text": text_to_compare,
                    "best_article": art,
                    "articles": [art],
                    "sources": [source_entry]
                })

        # Build EventCluster objects
        event_objects: List[EventCluster] = []
        now_str = datetime.now(timezone.utc).isoformat()

        for cl in clusters:
            best = cl["best_article"]
            event_obj = EventCluster(
                id=cl["id"],
                title=best.title,
                summary=best.summary or best.content[:300],
                start_time=best.published_at or now_str,
                updated_time=now_str,
                sources=cl["sources"],
                importance="high" if len(cl["sources"]) > 1 else "medium",
                confidence=min(0.70 + (0.10 * len(cl["sources"])), 0.99)
            )
            event_objects.append(event_obj)

        self._persist_events(event_objects)
        return event_objects

    def _persist_events(self, events: List[EventCluster]):
        """Saves events into news_events table."""
        try:
            with _db_lock:
                conn = get_db_connection()
                try:
                    with conn:
                        for ev in events:
                            conn.execute("""
                            INSERT INTO news_events (
                                id, title, summary, importance, confidence, start_time, updated_time, sources_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                updated_time = excluded.updated_time,
                                sources_json = excluded.sources_json,
                                confidence = excluded.confidence;
                            """, (
                                ev.id, ev.title, ev.summary, ev.importance, ev.confidence,
                                ev.start_time, ev.updated_time, json.dumps(ev.sources, ensure_ascii=False)
                            ))
                finally:
                    conn.close()
        except Exception as e:
            print(f"[ERROR] _persist_events: {e}")
