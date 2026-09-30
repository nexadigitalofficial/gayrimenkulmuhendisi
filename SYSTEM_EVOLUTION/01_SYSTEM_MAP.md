# 🗺️ SYSTEM MAP & ARCHITECTURAL TOPOLOGY
**Document Code:** SYS-EVO-01-MAP  
**Platform:** Gayrimenkul Mühendisi (Yiğit Narin / Coldwell Banker VIP Ankara)  
**Board Review Date:** September 2026

---

### 1. High-Level Topology & Flow
`mermaid
flowchart TB
    subgraph Clients [Clients & Channels]
        C1[Luxury Buyers / Investors]
        C2[Property Sellers / Owners]
        C3[Broker / Agent: Yiğit Narin]
        C4[Telegram / WhatsApp Subscribers]
    end

    subgraph CDN_Gateway [Edge & Presentation Layer]
        GW[Render Cloud Reverse Proxy / Gunicorn WSGI]
        SW[Service Worker PWA Cache: nexa-native-v2]
    end

    subgraph Frontend_Templates [Jinja2 + Reactive Islands]
        T1[site.html - Luxury Portal 11.3k LOC]
        T2[crm.html - Broker Cockpit 8.5k LOC]
        T3[ilanlar.html - Portfolio Showcase 3.2k LOC]
        T4[projeler.html - Project Catalog 8.0k LOC]
        T5[sunum.html - Interactive Deck 7.6k LOC]
        T6[haber.html - Real Estate News 2.9k LOC]
    end

    subgraph Application_Core [Monolith Core]
        APP[app.py - Flask Monolith 16.4k LOC / 127 Routes]
        AI_ENGINE[ai_listing.py & nexa_ai_engine.py]
        BUYER_ENG[buyer_engine.py & matcher_engine.py]
        VAL_ENG[valuation.py - Valuation Algorithms]
        MAIL_WA[mailer.py & wa_cloud.py]
    end

    subgraph Intelligence_Subsystem [Autonomous Daemon & RAG]
        AUTONOMIC[intelligence/autonomic_daemon.py]
        SWARM[intelligence/swarm/]
        PIPELINE[intelligence/pipeline.py]
        RAG[nexa_rag.py & nexa_vector_rag.py]
    end

    subgraph Data_Storage [Hybrid Storage Layer]
        SQLITE[(intelligence.db SQLite)]
        JSON_STORE[static/data/*.json 16 Flat Datasets]
        MEDIA[static/projeler/ & static/images/]
    end

    subgraph External_Ecosystem [External Integrations]
        CB[Coldwell Banker TR Scraper]
        GEMINI[Google Gemini 2.5 Flash API]
        GDRIVE[Google Drive Sync Engine]
        RENDER[Render Cloud Platform]
        TELEGRAM[Telegram Bot Dispatcher]
    end

    Clients --> GW
    GW --> SW
    SW --> Frontend_Templates
    Frontend_Templates --> APP
    APP --> AI_ENGINE
    APP --> BUYER_ENG
    APP --> VAL_ENG
    APP --> MAIL_WA
    APP --> Intelligence_Subsystem
    APP --> Data_Storage
    APP --> External_Ecosystem
    Intelligence_Subsystem --> SQLITE
`

---

### 2. File & Module Density Map
- **Monolith Core (pp.py):** 16,473 lines, handles auth, CRM Kanban, listings, news crawling, image OCR, WhatsApp webhooks, and PDF exports.
- **Frontend Templates (	emplates/):** Total 47,400+ lines of HTML/Vue/Tailwind.
  - site.html: Client landing, valuation wizard, portfolio filter, persona card modals, newsletter.
  - crm.html: Agent workspace, deal pipelines, buyer matchmaking, Coldwell Banker scraper controls.
  - ilanlar.html: Granular listing view, responsive filter matrix, Persona Swarm insights.
  - projeler.html: Interactive Leaflet map, Ankara branded project profiles, price per m² metrics.
- **Data Stores (static/data/ & SQLite):**
  - cached_cb_listings.json: Scraped Coldwell Banker listings.
  - portfolio_persona_intelligence.json: Swarm-generated buyer persona models.
  - projects_map.json: Geocoded coordinates for luxury developments across Çankaya, İncek, Çayyolu, Beytepe.
  - intelligence.db: SQLite database storing relational intelligence events, articles, and logs.
