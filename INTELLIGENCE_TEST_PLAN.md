# NEXA Real Estate Intelligence Network - Test Plan & Verification Matrix

## 1. Test Strategy & Coverage Scope

The test suite is divided into 10 key categories located in `tests/test_intelligence.py` and `test_buyer_engine.py`:

| Test ID | Test Function | Target Subsystem | Assertions Verified |
| :--- | :--- | :--- | :--- |
| **TEST-01** | `test_database_init_and_crud` | `intelligence/db.py` | SQLite schema, WAL mode, table creation, article query & conflict resolution. |
| **TEST-02** | `test_normalization_and_turkish_slug` | `intelligence/ingestion/normalizer.py` | Turkish char mapping, slug URL validity, HTML tag stripping. |
| **TEST-03** | `test_simhash_fingerprint_and_distance` | `intelligence/deduplication/simhash.py` | 64-bit fingerprint computation, Hamming distance, near-duplicate detection. |
| **TEST-04** | `test_event_clustering` | `intelligence/deduplication/event_clustering.py` | Multi-source article clustering into unified events. |
| **TEST-05** | `test_classification_engines` | `intelligence/classification/*.py` | Topic classification (Konut, Arsa, Faiz), Ankara region entity extraction. |
| **TEST-06** | `test_impact_engine_and_prompt_guard` | `intelligence/analysis/*.py` | Injection block tags, untrusted data wrapper, 4-way impact scoring bounds. |
| **TEST-07** | `test_decision_intelligence_engines` | `intelligence/decisions/engine.py` | 4 Decision engines (Buying, Selling, Project, Rent vs Buy) output bounds. |
| **TEST-08** | `test_advisor_and_crm_funnel` | `intelligence/advisor/*.py`, `analytics/*.py` | Tailored CTAs, pre-filled WhatsApp links, intent delta tracking (+1, +5, +15). |
| **TEST-09** | `test_api_endpoints_integration` | `app.py` REST API | `/feed`, `/daily-brief`, `/market-pulse`, `/decisions/buying`, `/track` status codes. |
| **TEST-10** | `test_pipeline_chaos_resilience` | Pipeline & Fallbacks | Missing Gemini API key falls back to deterministic analysis, bad feeds handled. |

---

## 2. Execution Command

To run the full suite:
```bash
pytest test_buyer_engine.py tests/test_intelligence.py -v
```

Verification Outcome:
- **Total Tests:** 19
- **Passed:** 19
- **Failed:** 0
- **Duration:** ~21.2 seconds
- **Pass Rate:** **100%**
