# NEXA Real Estate Intelligence Network - Operations & Incident Runbook

## 1. Daily Operations & Verification

### 1.1 Triggering an On-Demand Intelligence Run
If major macroeconomic news breaks (e.g. TCMB interest rate hike/cut or TÜİK inflation print):
```bash
# Option A: Run directly via Python module
python -m intelligence.pipeline --mode daily

# Option B: Trigger via Admin API endpoint
curl -X POST http://localhost:5000/api/admin/intelligence/run
```

### 1.2 Verifying Database Health & Stats
```bash
python -c "
from intelligence.db import get_published_articles
arts = get_published_articles(limit=100)
print('Total Published Articles in DB:', len(arts))
for a in arts[:5]:
    print(f'[{a.category}] {a.title} ({a.slug})')
"
```

### 1.3 Verifying Cache Sync
Ensure that `static/data/latest_news.json` is updated and matches the database:
```bash
python -c "
import json
with open('static/data/latest_news.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print('Cached articles count:', len(data))
"
```

---

## 2. Incident Response & Troubleshooting

### Scenario A: Gemini API Rate Limit or Network Outage
- **Symptom:** AI generation fails or throws quota errors.
- **System Behavior:** Automatic fallback to `AiIntelligenceEngine._deterministic_analysis()`. The pipeline completes with confidence score adjusted to `0.80`, logging a non-blocking warning.
- **Action:** No emergency action needed; system operates continuously without interruption.

### Scenario B: RSS Feed Down or 403 Forbidden
- **Symptom:** A source adapter (e.g. Bloomberg HT or Endeksa) cannot reach remote endpoints.
- **System Behavior:** Handled inside `try...except` within `fetch()`. The source returns an empty list, and the multi-source aggregator continues processing remaining sources.
- **Action:** Inspect source URL status; the pipeline will re-attempt on next scheduled execution.

### Scenario C: Corrupt SQLite Database File
- **Recovery Command:**
```bash
python -c "
from intelligence.db import init_db
init_db()
print('Tables initialized and verified.')
from intelligence.pipeline import IntelligencePipeline
IntelligencePipeline().run()
"
```
This restores all tables and re-populates the verified news and event corpus.
