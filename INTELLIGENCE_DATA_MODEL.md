# NEXA Real Estate Intelligence Network - Data Model & Schema Specification

## 1. Database Schema (`data/intelligence.db`)

### 1.1 `news_sources`
Tracks trusted institutions and market intelligence publishers.
```sql
CREATE TABLE IF NOT EXISTS news_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'OFFICIAL', 'NEWS_MEDIA', 'SECTOR_RESEARCH', 'SCRAPED'
    base_url TEXT NOT NULL,
    feed_url TEXT,
    trust_score REAL DEFAULT 0.85,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 1.2 `news_raw_articles`
Raw, un-deduplicated items fetched from active feeds.
```sql
CREATE TABLE IF NOT EXISTS news_raw_articles (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    summary TEXT,
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    simhash_fingerprint INTEGER,
    is_processed INTEGER DEFAULT 0,
    FOREIGN KEY(source_id) REFERENCES news_sources(id)
);
```

### 1.3 `news_events` (Clustered Stories)
Aggregated clusters linking multi-source reporting of identical macroeconomic or regional events.
```sql
CREATE TABLE IF NOT EXISTS news_events (
    id TEXT PRIMARY KEY,
    cluster_title TEXT NOT NULL,
    primary_topic TEXT NOT NULL,
    primary_region TEXT NOT NULL,
    article_ids_json TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.80
);
```

### 1.4 `news_articles` (Published Intelligence)
The fully enriched, scored, and verified flagship intelligence articles.
```sql
CREATE TABLE IF NOT EXISTS news_articles (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    primary_source TEXT NOT NULL,
    source_urls_json TEXT NOT NULL,
    hero_image TEXT,
    
    -- 4-Way Audience Impact Scores (0 - 100)
    impact_buyer_score INTEGER DEFAULT 65,
    impact_buyer_rationale TEXT,
    impact_seller_score INTEGER DEFAULT 60,
    impact_seller_rationale TEXT,
    impact_investor_score INTEGER DEFAULT 75,
    impact_investor_rationale TEXT,
    impact_developer_score INTEGER DEFAULT 55,
    impact_developer_rationale TEXT,
    
    -- Fact Claims & Verification
    fact_claims_json TEXT NOT NULL,
    verification_status TEXT DEFAULT 'VERIFIED',
    confidence_score REAL DEFAULT 0.85,
    
    -- Entity Associations
    topics_json TEXT NOT NULL,
    locations_json TEXT NOT NULL,
    related_article_ids_json TEXT,
    connected_listing_ids_json TEXT,
    
    -- Context-Aware Advisor CTAs
    advisor_headline TEXT,
    advisor_cta_text TEXT,
    advisor_prefill_msg TEXT,
    advisor_phone TEXT DEFAULT '+905324514008',
    
    status TEXT DEFAULT 'PUBLISHED',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### 1.5 `user_interest_vectors`
Stores personalized client preferences for dynamic content ranking.
```sql
CREATE TABLE IF NOT EXISTS user_interest_vectors (
    client_id TEXT PRIMARY KEY,
    topics_json TEXT NOT NULL,
    regions_json TEXT NOT NULL,
    audience_type TEXT DEFAULT 'GENERAL',
    last_active TEXT NOT NULL
);
```

### 1.6 `crm_intelligence_events`
Lead intent tracking event store.
```sql
CREATE TABLE IF NOT EXISTS crm_intelligence_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    article_id TEXT,
    event_type TEXT NOT NULL,
    intent_score_delta INTEGER NOT NULL,
    context_json TEXT,
    timestamp TEXT NOT NULL
);
```

---

## 2. Intent Score Calibration Matrix

| Action | Event Type | Intent Delta | Funnel Stage |
| :--- | :--- | :--- | :--- |
| Browsing Intelligence Feed | `article_view` | **+1** | Cold Prospect |
| Reading Related Market Story | `related_article_click` | **+2** | Engaged Reader |
| Inspecting Connected VIP Project | `property_link_click` | **+4** | Qualified Buyer/Seller |
| Running Interactive Decision Engine | `decision_tool_run` | **+5** | High-Intent Decision Maker |
| Clicking Contextual Advisor CTA | `advisor_cta_click` | **+10** | Warm Lead |
| Launching Pre-filled WhatsApp Inquiry | `whatsapp_click` | **+15** | Hot VIP Opportunity |
| Requesting VIP Portfolio Consultation | `appointment_click` | **+25** | Direct Advisory Booking |
