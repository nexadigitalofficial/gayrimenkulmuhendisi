# ⚙️ AUDIT: SOFTWARE ARCHITECTURE & BACKEND EVOLUTION
**Document Code:** SYS-EVO-04-ARCH  
**Authors:** Software Architecture Company + Performance & Scale Company  
**Target:** pp.py, i_listing.py, uyer_engine.py, intelligence/

---

### 1. Monolith Structural Analysis
pp.py currently encapsulates 16,473 lines, combining:
1. HTTP route declarations (127 endpoints).
2. Coldwell Banker HTML scraping and regex parsing.
3. WhatsApp Cloud API webhooks and message dispatchers.
4. Telegram notification hooks.
5. In-memory data caches and file write utilities.
6. Jinja2 context processors and template helpers.
7. Background scheduler jobs.

---

### 2. The Blueprint Decomposition Strategy
To guarantee stability without breaking existing URLs or deployments, the monolithic backend should be decomposed into Flask Blueprints:

`mermaid
flowchart TD
    MAIN[app.py - Master Application Factory 500 LOC]
    BP1[blueprints/core_routes.py - Landing, About, Contact]
    BP2[blueprints/listings_routes.py - Portfolio, CB Sync, Details]
    BP3[blueprints/crm_routes.py - Broker Cockpit, Kanban, Leads]
    BP4[blueprints/intelligence_routes.py - Persona Swarm, Valuation]
    BP5[blueprints/api_routes.py - REST Endpoints, Webhooks]

    MAIN --> BP1
    MAIN --> BP2
    MAIN --> BP3
    MAIN --> BP4
    MAIN --> BP5
`

---

### 3. Concurrency & Data Resilience Layer
- **Problem:** Direct writes to .json files risk concurrent write collisions.
- **Solution:** Introduce an AtomicJSONStore class:
  1. Writes payload to a temporary file (ile.json.tmp.<pid>).
  2. Flushes and syncs OS buffers (.flush(), os.fsync()).
  3. Executes atomic filesystem rename (os.replace()).
  4. Wraps mutations in an in-process thread-lock (	hreading.Lock()).
