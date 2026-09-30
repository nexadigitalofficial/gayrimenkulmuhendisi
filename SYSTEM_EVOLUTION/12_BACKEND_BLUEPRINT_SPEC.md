# 🧱 SPECIFICATION: FLASK BLUEPRINT MODULARIZATION
**Document Code:** SYS-EVO-12-ARCH-SPEC  
**Scope:** Phase 1 Implementation (P-001)

### 1. Blueprint Structure
`
blueprints/
  ├── __init__.py
  ├── portal.py         # Routes: /, /site, /ilanlar, /projeler, /haberler
  ├── crm.py            # Routes: /crm, /dashboard, /testcrm, /api/leads
  ├── intelligence.py   # Routes: /api/portfolio/persona-intelligence, /api/valuation
  ├── scrapers.py       # Routes: /api/start, /api/status/<job_id>, /api/stop
  └── webhooks.py       # Routes: /api/whatsapp/webhook, /api/track
`
- Total URL and route backward compatibility guaranteed; no broken links or client disruption.
