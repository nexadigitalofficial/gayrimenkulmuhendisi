"""
Concurrent multi-source ingestion engine.
Fetches from all registered sources with timeout controls and failure isolation.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Tuple
from intelligence.models import RawArticle, NewsSourceModel
from intelligence.sources import get_default_sources
from intelligence.sources.base import NewsSource
from intelligence.db import get_db_connection, _db_lock


class IngestionEngine:
    """Manages fetching across all configured source adapters."""

    def __init__(self, sources: List[NewsSource] = None, timeout: int = 15):
        self.sources = sources or get_default_sources()
        self.timeout = timeout

    def run_ingestion(self) -> Tuple[List[RawArticle], List[str]]:
        """
        Executes parallel fetches across all sources.
        Returns: (collected_articles, error_messages)
        """
        collected: List[RawArticle] = []
        errors: List[str] = []

        with ThreadPoolExecutor(max_workers=min(len(self.sources), 5)) as executor:
            future_to_source = {
                executor.submit(source.fetch): source for source in self.sources
            }
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                now_str = datetime.now(timezone.utc).isoformat()
                try:
                    articles = future.result(timeout=self.timeout)
                    collected.extend(articles)
                    self._record_source_success(source.model.id, now_str)
                    print(f"[{source.model.name}] Successfully fetched {len(articles)} articles.")
                except Exception as e:
                    err_msg = f"[{source.model.name}] Ingestion failed: {str(e)}"
                    print(f"[ERROR] {err_msg}")
                    errors.append(err_msg)
                    self._record_source_failure(source.model.id, now_str)

        # Save raw articles to SQLite
        self._persist_raw_articles(collected)
        return collected, errors

    def _record_source_success(self, source_id: str, timestamp: str):
        try:
            with _db_lock:
                conn = get_db_connection()
                try:
                    with conn:
                        conn.execute("""
                        INSERT INTO news_sources (id, name, url, type, last_success, failure_count)
                        VALUES (?, ?, ?, 'auto', ?, 0)
                        ON CONFLICT(id) DO UPDATE SET
                            last_success = excluded.last_success,
                            failure_count = 0;
                        """, (source_id, source_id, "https://", timestamp))
                finally:
                    conn.close()
        except Exception:
            pass

    def _record_source_failure(self, source_id: str, timestamp: str):
        try:
            with _db_lock:
                conn = get_db_connection()
                try:
                    with conn:
                        conn.execute("""
                        INSERT INTO news_sources (id, name, url, type, last_failure, failure_count)
                        VALUES (?, ?, ?, 'auto', ?, 1)
                        ON CONFLICT(id) DO UPDATE SET
                            last_failure = excluded.last_failure,
                            failure_count = failure_count + 1;
                        """, (source_id, source_id, "https://", timestamp))
                finally:
                    conn.close()
        except Exception:
            pass

    def _persist_raw_articles(self, articles: List[RawArticle]):
        """Saves raw articles into news_raw_articles table."""
        now_str = datetime.now(timezone.utc).isoformat()
        try:
            with _db_lock:
                conn = get_db_connection()
                try:
                    with conn:
                        for art in articles:
                            guid = art.guid or art.url or f"{art.source_id}_{art.title[:30]}"
                            conn.execute("""
                            INSERT INTO news_raw_articles (
                                guid, source_id, source_name, title, url, summary, content, author, published_at, image_url, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(guid) DO NOTHING;
                            """, (
                                guid, art.source_id, art.source_name, art.title, art.url,
                                art.summary, art.content, art.author, art.published_at, art.image_url, now_str
                            ))
                finally:
                    conn.close()
        except Exception as e:
            print(f"[ERROR] _persist_raw_articles: {e}")
