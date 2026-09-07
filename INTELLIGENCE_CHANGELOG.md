# NEXA Real Estate Intelligence Network - Changelog

All notable changes to the Gayrimenkul Mühendisi platform under the **NEXA Real Estate Intelligence Network Transformation** are documented below.

---

## [Version 2.0.0] - March 2026

### Added
- **Core Architecture Subsystem (`intelligence/`):**
  - Normalized domain models in `intelligence/models.py`.
  - SQLite database layer with WAL mode and conflict resolution in `intelligence/db.py`.
  - SSRF-guarded sources adapters for TCMB, TÜİK, AA Finans, Bloomberg HT, Endeksa in `intelligence/sources/`.
  - Concurrent multi-source fetcher with thread pool in `intelligence/ingestion/fetcher.py`.
  - Turkish diacritics sanitizer and slug generator in `intelligence/ingestion/normalizer.py`.
  - 64-bit SimHash and Jaccard deduplication in `intelligence/deduplication/simhash.py`.
  - Event clustering aggregator in `intelligence/deduplication/event_clustering.py`.
  - Factual claim extraction and multi-source corroboration in `intelligence/verification/fact_checker.py`.
  - Dynamic topic classifier in `intelligence/classification/topic_engine.py`.
  - Ankara prime location entity extractor in `intelligence/classification/region_engine.py`.
  - Explainable 4-way impact scoring engine (Buyer, Seller, Investor, Developer) in `intelligence/analysis/impact_engine.py`.
  - Prompt injection defense layer with untrusted data isolation in `intelligence/analysis/prompt_guard.py`.
  - Gemini 2.5 Flash analytical layer with deterministic fallback in `intelligence/analysis/ai_engine.py`.
  - 4 Interactive Decision Support engines (Buying, Selling, Project, Rent vs Buy) in `intelligence/decisions/engine.py`.
  - Connected Coldwell Banker VIP Ankara project linking in `intelligence/related/property_linker.py`.
  - Client interest vector ranking and proactive market alerts in `intelligence/personalization/`.
  - Context-aware advisor CTAs and WhatsApp consultation generator in `intelligence/advisor/`.
  - Telemetry lead intent tracking (+1 to +25 score delta) in `intelligence/analytics/funnel_tracker.py`.
  - Atomic legacy cache exporter in `intelligence/publication/legacy_exporter.py`.
  - Daily flagship brief generator in `intelligence/publication/daily_brief.py`.
  - Master pipeline orchestrator in `intelligence/pipeline.py`.
- **Frontend Hub Transformation:**
  - `templates/haber.html` completely rebuilt as the **NEXA Real Estate Intelligence Hub**.
  - Dynamic Market Pulse scrolling ticker.
  - Interactive Decision Center calculators with real-time API calculation.
  - Deep reading modal with 4-way impact meters, fact claims, and direct WhatsApp inquiry flow.
- **API Endpoints in `app.py`:**
  - `GET /api/intelligence/feed`
  - `GET /api/intelligence/article/<slug_or_id>`
  - `GET /api/intelligence/daily-brief`
  - `GET /api/intelligence/market-pulse`
  - `POST /api/intelligence/decisions/buying`
  - `POST /api/intelligence/decisions/selling`
  - `POST /api/intelligence/decisions/project`
  - `POST /api/intelligence/decisions/rent-vs-buy`
  - `POST /api/intelligence/advisor/ask`
  - `POST /api/intelligence/track`
  - `GET /api/intelligence/prospects`
  - `GET /api/admin/intelligence/stats`
  - `POST /api/admin/intelligence/run`
- **Testing & CI:**
  - Test suite in `tests/test_intelligence.py` covering unit, integration, and chaos scenarios (10/10 passed).
  - Upgraded `.github/workflows/daily_news_crawler.yml` to execute the full pipeline.

### Changed
- `crawl_daily_news.py`: Replaced naive synthetic text generation with master pipeline execution.
- `templates/mobile_app.html`: Connected ticker pill and app profile settings to `/intelligence`.
- `templates/site.html`: Updated navigation bar link to `/intelligence` with "Piyasa Zekası".

### Removed
- Unverified, synthetic dummy news generation logic.
