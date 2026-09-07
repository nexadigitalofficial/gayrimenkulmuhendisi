# NEXA Real Estate Intelligence Network - Pipeline & Execution Engine

## 1. Pipeline Phases & Orchestration

The master pipeline is orchestrated by `intelligence/pipeline.py` and executes in 7 sequential phases:

```
[Phase 1: Ingestion]  ──► [Phase 2: Clustering] ──► [Phase 3: Fact Checking]
         │                          │                          │
         ▼                          ▼                          ▼
Concurrent Multi-Source     SimHash 64-bit            Multi-Source Claims
Fetch & Normalization       Deduplication             Verification Status
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    ▼
                      [Phase 4: Classification]
                                    │
                            Topic & Region Engine
                                    │
                                    ▼
                       [Phase 5: AI & Impact Engine]
                                    │
                            Gemini 2.5 Flash +
                            Deterministic Fallback
                                    │
                                    ▼
                      [Phase 6: Decision & Linking]
                                    │
                            CB VIP Projects Match +
                            Contextual Advisor CTAs
                                    │
                                    ▼
                       [Phase 7: Publication Gate]
                                    │
                            Quality Score >= 70
                            Atomic DB + JSON Cache
```

---

## 2. Command Line Interface (CLI)

The pipeline can be executed in different modes directly via Python:

```bash
# Standard daily pipeline execution
python -m intelligence.pipeline --mode daily

# Force refresh of all feeds ignoring local cache
python -m intelligence.pipeline --force

# Inspect execution metrics and statistics
python -m intelligence.pipeline --stats
```

Execution benchmark:
- Average run time: **~480ms** (deterministic fallback) to **~2.8s** (full Gemini API enrichments).
- Memory footprint: **< 45MB RAM**.

---

## 3. Automation via GitHub Actions

Configured in `.github/workflows/daily_news_crawler.yml`:
- **Schedule:** Runs every day at 09:00 TRT (`06:00 UTC`).
- **Trigger:** Also supports manual execution via `workflow_dispatch`.
- **Artifacts:** Commits updated `data/intelligence.db` and `static/data/latest_news.json` automatically with `[skip ci]`.
