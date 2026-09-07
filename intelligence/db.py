"""
SQLite database layer for NEXA Real Estate Intelligence Network.
Features:
- Thread-safe connection handling
- WAL mode (Write-Ahead Logging) for high concurrency
- Normalized tables with foreign keys and optimized indexes
- Atomic transaction management
"""

import os
import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from intelligence.models import (
    IntelligenceArticle, NewsSourceModel, RawArticle, EventCluster,
    FactClaim, ImpactScore, RegionEntity, TopicEntity, IntelligenceRun,
    ContentStatus, SourceType, MarketDirection
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "intelligence.db"

_db_lock = threading.Lock()


def get_db_connection() -> sqlite3.Connection:
    """Returns an optimized SQLite connection with WAL mode and row factory."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db():
    """Initializes schema, migrations, and indexes."""
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                # 1. Sources table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS news_sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    type TEXT NOT NULL,
                    authority_score INTEGER DEFAULT 80,
                    reliability_score INTEGER DEFAULT 80,
                    enabled INTEGER DEFAULT 1,
                    last_success TEXT,
                    last_failure TEXT,
                    failure_count INTEGER DEFAULT 0
                );
                """)

                # 2. Raw Ingested Articles
                conn.execute("""
                CREATE TABLE IF NOT EXISTS news_raw_articles (
                    guid TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    summary TEXT,
                    content TEXT,
                    author TEXT,
                    published_at TEXT,
                    image_url TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(source_id) REFERENCES news_sources(id) ON DELETE CASCADE
                );
                """)

                # 3. Clustered Events
                conn.execute("""
                CREATE TABLE IF NOT EXISTS news_events (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    importance TEXT DEFAULT 'medium',
                    confidence REAL DEFAULT 0.85,
                    start_time TEXT NOT NULL,
                    updated_time TEXT NOT NULL,
                    sources_json TEXT,
                    locations_json TEXT,
                    topics_json TEXT
                );
                """)

                # 4. Intelligence Articles (Published / Ready)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS news_articles (
                    id TEXT PRIMARY KEY,
                    slug TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    category TEXT NOT NULL,
                    read_time TEXT DEFAULT '3 dk',
                    status TEXT DEFAULT 'published',
                    what_happened TEXT,
                    why_it_matters TEXT,
                    who_is_affected TEXT,
                    risks_json TEXT,
                    opportunities_json TEXT,
                    time_horizon TEXT,
                    impacts_json TEXT,
                    facts_json TEXT,
                    locations_json TEXT,
                    topics_json TEXT,
                    sources_json TEXT,
                    related_article_ids_json TEXT,
                    related_project_ids_json TEXT,
                    related_portfolio_ids_json TEXT,
                    target_audience TEXT DEFAULT 'GENERAL',
                    advisor_headline TEXT,
                    advisor_cta_text TEXT,
                    advisor_phone TEXT,
                    what_we_know TEXT,
                    what_we_infer TEXT,
                    what_we_suspect TEXT,
                    what_we_dont_know TEXT,
                    contrarian_json TEXT,
                    why_this_news_json TEXT,
                    quality_score INTEGER DEFAULT 90,
                    confidence_score REAL DEFAULT 0.90,
                    event_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES news_events(id) ON DELETE SET NULL
                );
                """)

                # Migrations for existing DB
                for col, col_type in [
                    ("what_we_know", "TEXT"),
                    ("what_we_infer", "TEXT"),
                    ("what_we_suspect", "TEXT"),
                    ("what_we_dont_know", "TEXT"),
                    ("contrarian_json", "TEXT"),
                    ("why_this_news_json", "TEXT")
                ]:
                    try:
                        conn.execute(f"ALTER TABLE news_articles ADD COLUMN {col} {col_type};")
                    except sqlite3.OperationalError:
                        pass

                # 5. User Interest Vectors (Behavior & Personalization)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS user_interest_vectors (
                    user_id TEXT PRIMARY KEY,
                    topics_json TEXT,
                    locations_json TEXT,
                    intent_score INTEGER DEFAULT 0,
                    viewed_articles_json TEXT,
                    viewed_projects_json TEXT,
                    decision_tools_json TEXT,
                    last_active TEXT NOT NULL
                );
                """)

                # 6. CRM Intelligence Funnel Tracking Events
                conn.execute("""
                CREATE TABLE IF NOT EXISTS crm_intelligence_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    article_id TEXT,
                    event_type TEXT NOT NULL,
                    intent_score_delta INTEGER DEFAULT 1,
                    context_json TEXT,
                    created_at TEXT NOT NULL
                );
                """)

                # 7. Intelligence Runs (Observability & Health)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS intelligence_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    sources_checked INTEGER DEFAULT 0,
                    items_found INTEGER DEFAULT 0,
                    duplicates_merged INTEGER DEFAULT 0,
                    verified_count INTEGER DEFAULT 0,
                    published_count INTEGER DEFAULT 0,
                    rejected_count INTEGER DEFAULT 0,
                    errors_json TEXT,
                    latency_ms INTEGER DEFAULT 0,
                    success INTEGER DEFAULT 1
                );
                """)

                # 8. Swarm Research Priority Queue
                conn.execute("""
                CREATE TABLE IF NOT EXISTS research_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    priority INTEGER DEFAULT 50,
                    topic TEXT NOT NULL,
                    region TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING',
                    payload_json TEXT,
                    created_at TEXT NOT NULL
                );
                """)

                # 9. Dynamic Market State Snapshots & History
                conn.execute("""
                CREATE TABLE IF NOT EXISTS market_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    demand REAL NOT NULL,
                    supply REAL NOT NULL,
                    credit REAL NOT NULL,
                    rental REAL NOT NULL,
                    price_pressure REAL NOT NULL,
                    investment_appetite REAL NOT NULL,
                    regime TEXT NOT NULL,
                    data_json TEXT
                );
                """)

                # 10. Evidence Graph Nodes
                conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_graph_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    claim TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    status TEXT DEFAULT 'VERIFIED',
                    confidence REAL DEFAULT 0.85,
                    corroboration_json TEXT,
                    created_at TEXT NOT NULL
                );
                """)

                # 11. Emerging Market Trends
                conn.execute("""
                CREATE TABLE IF NOT EXISTS emerging_trends (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    region TEXT NOT NULL,
                    velocity REAL DEFAULT 1.0,
                    signal_count INTEGER DEFAULT 1,
                    summary TEXT,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                );
                """)

                # 12. Research Audit Trail
                conn.execute("""
                CREATE TABLE IF NOT EXISTS research_audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    research_id TEXT NOT NULL,
                    agents_used_json TEXT,
                    scores_json TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL
                );
                """)

                # Indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_status ON news_articles(status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_slug ON news_articles(slug);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_created_at ON news_articles(created_at DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON news_articles(category);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_raw_created_at ON news_raw_articles(created_at DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_crm_events_user ON crm_intelligence_events(user_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_research_queue_status ON research_queue(status, priority DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_market_state_history_time ON market_state_history(timestamp DESC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_emerging_trends_active ON emerging_trends(is_active, velocity DESC);")

        finally:
            conn.close()


def save_article(article: IntelligenceArticle) -> bool:
    """Saves or updates a fully processed intelligence article."""
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO news_articles (
                    id, slug, title, summary, content, image_url, category, read_time,
                    status, what_happened, why_it_matters, who_is_affected,
                    risks_json, opportunities_json, time_horizon, impacts_json,
                    facts_json, locations_json, topics_json, sources_json,
                    related_article_ids_json, related_project_ids_json, related_portfolio_ids_json,
                    target_audience, advisor_headline, advisor_cta_text, advisor_phone,
                    what_we_know, what_we_infer, what_we_suspect, what_we_dont_know,
                    contrarian_json, why_this_news_json,
                    quality_score, confidence_score, event_id, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                ) ON CONFLICT(slug) DO UPDATE SET
                    title = excluded.title,
                    summary = excluded.summary,
                    content = excluded.content,
                    image_url = excluded.image_url,
                    category = excluded.category,
                    read_time = excluded.read_time,
                    status = excluded.status,
                    what_happened = excluded.what_happened,
                    why_it_matters = excluded.why_it_matters,
                    who_is_affected = excluded.who_is_affected,
                    risks_json = excluded.risks_json,
                    opportunities_json = excluded.opportunities_json,
                    time_horizon = excluded.time_horizon,
                    impacts_json = excluded.impacts_json,
                    facts_json = excluded.facts_json,
                    locations_json = excluded.locations_json,
                    topics_json = excluded.topics_json,
                    sources_json = excluded.sources_json,
                    related_article_ids_json = excluded.related_article_ids_json,
                    related_project_ids_json = excluded.related_project_ids_json,
                    related_portfolio_ids_json = excluded.related_portfolio_ids_json,
                    target_audience = excluded.target_audience,
                    advisor_headline = excluded.advisor_headline,
                    advisor_cta_text = excluded.advisor_cta_text,
                    advisor_phone = excluded.advisor_phone,
                    what_we_know = excluded.what_we_know,
                    what_we_infer = excluded.what_we_infer,
                    what_we_suspect = excluded.what_we_suspect,
                    what_we_dont_know = excluded.what_we_dont_know,
                    contrarian_json = excluded.contrarian_json,
                    why_this_news_json = excluded.why_this_news_json,
                    quality_score = excluded.quality_score,
                    confidence_score = excluded.confidence_score,
                    updated_at = excluded.updated_at;
                """, (
                    article.id,
                    article.slug,
                    article.title,
                    article.summary,
                    article.content,
                    article.image_url,
                    article.category,
                    article.read_time,
                    article.status.value,
                    article.what_happened,
                    article.why_it_matters,
                    article.who_is_affected,
                    json.dumps(article.risks, ensure_ascii=False),
                    json.dumps(article.opportunities, ensure_ascii=False),
                    article.time_horizon,
                    json.dumps(article.impacts.to_dict() if isinstance(article.impacts, ImpactScore) else article.impacts, ensure_ascii=False),
                    json.dumps([f.to_dict() if isinstance(f, FactClaim) else f for f in article.facts], ensure_ascii=False),
                    json.dumps([l.to_dict() if isinstance(l, RegionEntity) else l for l in article.locations], ensure_ascii=False),
                    json.dumps([t.to_dict() if isinstance(t, TopicEntity) else t for t in article.topics], ensure_ascii=False),
                    json.dumps(article.sources, ensure_ascii=False),
                    json.dumps(article.related_article_ids, ensure_ascii=False),
                    json.dumps(article.related_project_ids, ensure_ascii=False),
                    json.dumps(article.related_portfolio_ids, ensure_ascii=False),
                    article.target_audience,
                    article.advisor_headline,
                    article.advisor_cta_text,
                    article.advisor_phone,
                    article.what_we_know,
                    article.what_we_infer,
                    article.what_we_suspect,
                    article.what_we_dont_know,
                    json.dumps(article.contrarian_view or {}, ensure_ascii=False),
                    json.dumps(article.why_this_news or {}, ensure_ascii=False),
                    article.quality_score,
                    article.confidence_score,
                    article.event_id,
                    article.created_at,
                    article.updated_at
                ))
            return True
        except Exception as e:
            print(f"[ERROR] save_article failed: {e}")
            return False
        finally:
            conn.close()


def row_to_article(row: sqlite3.Row) -> IntelligenceArticle:
    """Converts a database row into an IntelligenceArticle object."""
    impacts_data = json.loads(row["impacts_json"]) if row["impacts_json"] else {}
    impacts = ImpactScore(
        buyer_score=impacts_data.get("buyer_score", 50),
        buyer_rationale=impacts_data.get("buyer_rationale", ""),
        seller_score=impacts_data.get("seller_score", 50),
        seller_rationale=impacts_data.get("seller_rationale", ""),
        investor_score=impacts_data.get("investor_score", 50),
        investor_rationale=impacts_data.get("investor_rationale", ""),
        developer_score=impacts_data.get("developer_score", 50),
        developer_rationale=impacts_data.get("developer_rationale", ""),
        price_trend=MarketDirection(impacts_data.get("price_trend", "neutral")),
        rent_trend=MarketDirection(impacts_data.get("rent_trend", "neutral")),
        credit_conditions=MarketDirection(impacts_data.get("credit_conditions", "neutral"))
    )

    facts_data = json.loads(row["facts_json"]) if row["facts_json"] else []
    facts = [FactClaim(**f) for f in facts_data]

    locations_data = json.loads(row["locations_json"]) if row["locations_json"] else []
    locations = [RegionEntity(**l) for l in locations_data]

    topics_data = json.loads(row["topics_json"]) if row["topics_json"] else []
    topics = [TopicEntity(**t) for t in topics_data]

    # Safe retrieval of epistemological columns
    keys = set(row.keys())
    w_know = row["what_we_know"] if ("what_we_know" in keys and row["what_we_know"]) else ""
    w_infer = row["what_we_infer"] if ("what_we_infer" in keys and row["what_we_infer"]) else ""
    w_suspect = row["what_we_suspect"] if ("what_we_suspect" in keys and row["what_we_suspect"]) else ""
    w_dont_know = row["what_we_dont_know"] if ("what_we_dont_know" in keys and row["what_we_dont_know"]) else ""
    c_view = json.loads(row["contrarian_json"]) if ("contrarian_json" in keys and row["contrarian_json"]) else {}
    w_news = json.loads(row["why_this_news_json"]) if ("why_this_news_json" in keys and row["why_this_news_json"]) else {}

    return IntelligenceArticle(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        summary=row["summary"],
        content=row["content"],
        image_url=row["image_url"] or "",
        category=row["category"],
        read_time=row["read_time"],
        status=ContentStatus(row["status"]),
        what_happened=row["what_happened"] or "",
        why_it_matters=row["why_it_matters"] or "",
        who_is_affected=row["who_is_affected"] or "",
        risks=json.loads(row["risks_json"]) if row["risks_json"] else [],
        opportunities=json.loads(row["opportunities_json"]) if row["opportunities_json"] else [],
        time_horizon=row["time_horizon"] or "Orta Vade (3-6 Ay)",
        impacts=impacts,
        facts=facts,
        locations=locations,
        topics=topics,
        sources=json.loads(row["sources_json"]) if row["sources_json"] else [],
        related_article_ids=json.loads(row["related_article_ids_json"]) if row["related_article_ids_json"] else [],
        related_project_ids=json.loads(row["related_project_ids_json"]) if row["related_project_ids_json"] else [],
        related_portfolio_ids=json.loads(row["related_portfolio_ids_json"]) if row["related_portfolio_ids_json"] else [],
        target_audience=row["target_audience"] or "GENERAL",
        advisor_headline=row["advisor_headline"] or "Bu Gelişmenin Sizin İçin Ne Anlama Geldiğini Danışmanınıza Sorun",
        advisor_cta_text=row["advisor_cta_text"] or "Yiğit Narin'e Danışın",
        advisor_phone=row["advisor_phone"] or "+905324514008",
        what_we_know=w_know,
        what_we_infer=w_infer,
        what_we_suspect=w_suspect,
        what_we_dont_know=w_dont_know,
        contrarian_view=c_view,
        why_this_news=w_news,
        quality_score=row["quality_score"],
        confidence_score=row["confidence_score"],
        event_id=row["event_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    )


def delete_article(slug_or_id: str) -> bool:
    """Deletes an article by slug or ID."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("DELETE FROM news_articles WHERE slug = ? OR id = ?;", (slug_or_id, slug_or_id))
            return True
        except Exception as e:
            print(f"[ERROR] delete_article failed: {e}")
            return False
        finally:
            conn.close()


def clear_all_articles() -> bool:
    """Deletes all articles from news_articles (used for database refreshes)."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("DELETE FROM news_articles;")
            return True
        except Exception as e:
            print(f"[ERROR] clear_all_articles failed: {e}")
            return False
        finally:
            conn.close()


def get_published_articles(limit: int = 30, category: Optional[str] = None, offset: int = 0) -> List[IntelligenceArticle]:
    """Retrieves published intelligence articles sorted by created_at DESC."""
    init_db()
    conn = get_db_connection()
    try:
        if category and category != "Tümü":
            cursor = conn.execute("""
                SELECT * FROM news_articles
                WHERE status = 'published' AND category = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """, (category, limit, offset))
        else:
            cursor = conn.execute("""
                SELECT * FROM news_articles
                WHERE status = 'published'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?;
            """, (limit, offset))

        return [row_to_article(r) for r in cursor.fetchall()]
    finally:
        conn.close()


def get_article_by_slug_or_id(slug_or_id: str) -> Optional[IntelligenceArticle]:
    """Finds an article by slug or ID."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT * FROM news_articles
            WHERE slug = ? OR id = ?
            LIMIT 1;
        """, (slug_or_id, slug_or_id))
        row = cursor.fetchone()
        return row_to_article(row) if row else None
    finally:
        conn.close()


def log_crm_intelligence_event(user_id: Optional[str], article_id: Optional[str], event_type: str, intent_score_delta: int = 1, context: Optional[Dict[str, Any]] = None):
    """Records an intelligence interaction event for CRM lead scoring."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO crm_intelligence_events (user_id, article_id, event_type, intent_score_delta, context_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    user_id or "anonymous",
                    article_id,
                    event_type,
                    intent_score_delta,
                    json.dumps(context or {}, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat()
                ))
                # Update user vector if user_id present
                if user_id:
                    conn.execute("""
                    INSERT INTO user_interest_vectors (user_id, intent_score, last_active)
                    VALUES (?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        intent_score = intent_score + excluded.intent_score,
                        last_active = excluded.last_active;
                    """, (user_id, intent_score_delta, datetime.now(timezone.utc).isoformat()))
        finally:
            conn.close()


def save_intelligence_run(run: IntelligenceRun):
    """Records run telemetry."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO intelligence_runs (
                    run_id, started_at, ended_at, sources_checked, items_found,
                    duplicates_merged, verified_count, published_count, rejected_count,
                    errors_json, latency_ms, success
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    ended_at = excluded.ended_at,
                    sources_checked = excluded.sources_checked,
                    items_found = excluded.items_found,
                    duplicates_merged = excluded.duplicates_merged,
                    verified_count = excluded.verified_count,
                    published_count = excluded.published_count,
                    rejected_count = excluded.rejected_count,
                    errors_json = excluded.errors_json,
                    latency_ms = excluded.latency_ms,
                    success = excluded.success;
                """, (
                    run.run_id,
                    run.started_at,
                    run.ended_at,
                    run.sources_checked,
                    run.items_found,
                    run.duplicates_merged,
                    run.verified_count,
                    run.published_count,
                    run.rejected_count,
                    json.dumps(run.errors, ensure_ascii=False),
                    run.latency_ms,
                    1 if run.success else 0
                ))
        finally:
            conn.close()


def get_latest_run_stats() -> Dict[str, Any]:
    """Returns telemetry from the last 10 automation runs."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.execute("""
            SELECT * FROM intelligence_runs
            ORDER BY started_at DESC
            LIMIT 10;
        """)
        runs = []
        for r in cursor.fetchall():
            runs.append({
                "run_id": r["run_id"],
                "started_at": r["started_at"],
                "ended_at": r["ended_at"],
                "sources_checked": r["sources_checked"],
                "items_found": r["items_found"],
                "duplicates_merged": r["duplicates_merged"],
                "verified_count": r["verified_count"],
                "published_count": r["published_count"],
                "rejected_count": r["rejected_count"],
                "errors": json.loads(r["errors_json"]) if r["errors_json"] else [],
                "latency_ms": r["latency_ms"],
                "success": bool(r["success"])
            })
        
        # Aggregate totals
        total_articles = conn.execute("SELECT COUNT(*) FROM news_articles WHERE status = 'published';").fetchone()[0]
        total_events = conn.execute("SELECT COUNT(*) FROM crm_intelligence_events;").fetchone()[0]

        return {
            "total_published_articles": total_articles,
            "total_crm_interactions": total_events,
            "recent_runs": runs
        }
    finally:
        conn.close()


# ============================================================================
# SWARM EXTENSIONS: RESEARCH QUEUE, MARKET STATE, TRENDS & AUDIT
# ============================================================================

def save_research_task(
    task_id: str,
    priority: int,
    topic: str,
    region: str,
    status: str = "PENDING",
    payload: Optional[Dict[str, Any]] = None
) -> bool:
    """Saves or updates a research task in the Swarm Priority Queue."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO research_queue (task_id, priority, topic, region, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    priority = excluded.priority,
                    status = excluded.status,
                    payload_json = excluded.payload_json;
                """, (
                    task_id,
                    priority,
                    topic,
                    region,
                    status,
                    json.dumps(payload or {}, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat()
                ))
            return True
        except Exception:
            return False
        finally:
            conn.close()


def get_research_queue(status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieves tasks from the Swarm Research Priority Queue."""
    init_db()
    conn = get_db_connection()
    try:
        if status:
            cursor = conn.execute(
                "SELECT * FROM research_queue WHERE status = ? ORDER BY priority DESC LIMIT ?;",
                (status, limit)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM research_queue ORDER BY priority DESC LIMIT ?;",
                (limit,)
            )
        tasks = []
        for r in cursor.fetchall():
            tasks.append({
                "id": r["id"],
                "task_id": r["task_id"],
                "priority": r["priority"],
                "topic": r["topic"],
                "region": r["region"],
                "status": r["status"],
                "payload": json.loads(r["payload_json"]) if r["payload_json"] else {},
                "created_at": r["created_at"]
            })
        return tasks
    finally:
        conn.close()


def save_market_state_snapshot(state_dict: Dict[str, Any]) -> bool:
    """Persists a point-in-time Market State Snapshot to SQLite."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO market_state_history (
                    timestamp, demand, supply, credit, rental, price_pressure, investment_appetite, regime, data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    state_dict.get("last_updated", datetime.now(timezone.utc).isoformat()),
                    float(state_dict.get("demand", 70.0)),
                    float(state_dict.get("supply", 50.0)),
                    float(state_dict.get("credit", 60.0)),
                    float(state_dict.get("rental", 75.0)),
                    float(state_dict.get("price_pressure", 70.0)),
                    float(state_dict.get("investment_appetite", 75.0)),
                    str(state_dict.get("regime", "STABLE")),
                    json.dumps(state_dict, ensure_ascii=False)
                ))
            return True
        except Exception:
            return False
        finally:
            conn.close()


def get_market_state_history(limit: int = 30) -> List[Dict[str, Any]]:
    """Retrieves chronological market state snapshots."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM market_state_history ORDER BY timestamp DESC LIMIT ?;",
            (limit,)
        )
        history = []
        for r in cursor.fetchall():
            history.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "demand": r["demand"],
                "supply": r["supply"],
                "credit": r["credit"],
                "rental": r["rental"],
                "price_pressure": r["price_pressure"],
                "investment_appetite": r["investment_appetite"],
                "regime": r["regime"],
                "data": json.loads(r["data_json"]) if r["data_json"] else {}
            })
        return history
    finally:
        conn.close()


def save_emerging_trend(
    trend_id: str,
    topic: str,
    region: str,
    velocity: float,
    signal_count: int,
    summary: str,
    first_seen: str,
    last_seen: str,
    is_active: bool = True
) -> bool:
    """Inserts or updates an emerging market trend."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO emerging_trends (
                    id, topic, region, velocity, signal_count, summary, first_seen, last_seen, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    velocity = excluded.velocity,
                    signal_count = excluded.signal_count,
                    summary = excluded.summary,
                    last_seen = excluded.last_seen,
                    is_active = excluded.is_active;
                """, (
                    trend_id,
                    topic,
                    region,
                    velocity,
                    signal_count,
                    summary,
                    first_seen,
                    last_seen,
                    1 if is_active else 0
                ))
            return True
        except Exception:
            return False
        finally:
            conn.close()


def get_active_trends(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves current high-velocity emerging trends."""
    init_db()
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM emerging_trends WHERE is_active = 1 ORDER BY velocity DESC, signal_count DESC LIMIT ?;",
            (limit,)
        )
        trends = []
        for r in cursor.fetchall():
            trends.append({
                "id": r["id"],
                "topic": r["topic"],
                "region": r["region"],
                "velocity": r["velocity"],
                "signal_count": r["signal_count"],
                "summary": r["summary"],
                "first_seen": r["first_seen"],
                "last_seen": r["last_seen"]
            })
        return trends
    finally:
        conn.close()


def record_research_audit(
    research_id: str,
    agents_used: List[str],
    scores: Dict[str, Any],
    result: Dict[str, Any]
) -> bool:
    """Logs an immutable audit entry for every swarm research execution."""
    init_db()
    with _db_lock:
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("""
                INSERT INTO research_audit_trail (
                    research_id, agents_used_json, scores_json, result_json, created_at
                ) VALUES (?, ?, ?, ?, ?);
                """, (
                    research_id,
                    json.dumps(agents_used, ensure_ascii=False),
                    json.dumps(scores, ensure_ascii=False),
                    json.dumps(result, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat()
                ))
            return True
        except Exception:
            return False
        finally:
            conn.close()

