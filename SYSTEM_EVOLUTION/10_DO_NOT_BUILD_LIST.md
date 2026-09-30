# 🛑 DO NOT BUILD LIST & STRATEGIC DISCIPLINE
**Document Code:** SYS-EVO-10-DO-NOT-BUILD  
**Authors:** Strategy & Futures Company + Ethics / Risk / Governance Office  
**Target:** Development Scope Constraints & Anti-Patterns

---

### 1. The Strict 'DO NOT BUILD' Charter
To prevent feature bloat, technical debt explosion, and resource misallocation, the Digital Holding has formally prohibited the following development directions:

1. **❌ DO NOT BUILD: Full Single-Page App (SPA) Complete Rewrite:**
   - *Rationale:* Rewriting the entire frontend in React/Next.js or Vue CLI from scratch will introduce massive delivery delays, break delicate Jinja-rendered dynamic elements, and jeopardize live client operations.
   - *Approved Direction:* Incremental Vue 3 componentization inside existing Jinja templates.

2. **❌ DO NOT BUILD: Synchronous On-the-Fly Video Rendering in Flask:**
   - *Rationale:* Generating heavy MP4/WebM promotional videos inside web worker threads will exhaust server CPU/RAM and freeze HTTP request handling.
   - *Approved Direction:* Pre-generated cinematic media or offloaded cloud generation.

3. **❌ DO NOT BUILD: Uncached Raw Gemini Calls on Listing Card Render:**
   - *Rationale:* Invoking generative AI on every card hover or listing visit creates unacceptable latency and cost spirals.
   - *Approved Direction:* Asynchronous background swarm profiling with persistent JSON caching.

4. **❌ DO NOT BUILD: Monolithic Bloat Additions to pp.py:**
   - *Rationale:* Adding more thousand-line functions into pp.py exacerbates the architectural gravity hazard.
   - *Approved Direction:* All future features must reside in isolated service modules or Flask Blueprints.
