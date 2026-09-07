# NEXA Real Estate Intelligence Network - System Architecture

## 1. High-Level Architectural Diagram

```
[Official Feeds]     [News Media]       [PropTech Feeds]
(TCMB, TÜİK RSS)    (AA Finans, BBHT)     (Endeksa RSS)
        │                  │                   │
        └──────────────────┼───────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │  Concurrent Multi-Source Fetch  │ (SSRF Guarded, Rate-Limited)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │ Text Sanitizer & Slug Generator │ (Turkish diacritics normalized)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │    SimHash & Event Clustering   │ (64-bit Hamming Dist <= 6, Jaccard)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │   Factual Verification Engine   │ (Claim Extraction, Trust Scorer)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │  Topic & Region Classification  │ (Ankara Axes: Beytepe, İncek, Çankaya)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │ AI & 4-Way Impact Scoring Layer │ (Gemini 2.5 Flash + Fallback)
          │  [Buyer, Seller, Inv., Dev.]    │ (Prompt Injection Guard)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │  Related Projects & Portfolios  │ (Coldwell Banker VIP Listings linked)
          └────────────────┬────────────────┘
                           ▼
          ┌─────────────────────────────────┐
          │ Publication & Legacy Exporter   │ (Quality Gate Score >= 70)
          └────────────────┬────────────────┘
                           │
      ┌────────────────────┴────────────────────┐
      ▼                                         ▼
[SQLite DB: intelligence.db]      [Static JSON: latest_news.json]
(WAL Mode, Thread Locked)         (Atomic File Write, Fallback)
      │                                         │
      └────────────────────┬────────────────────┘
                           ▼
           ┌────────────────────────────────┐
           │   Flask REST API Endpoints     │
           │ (/api/intelligence/*, /blog/*) │
           └───────────────┬────────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
[Desktop Intelligence Hub]             [NEXA Mobile Native App]
  (templates/haber.html)                (templates/mobile_app.html)
- Market Pulse Live Ticker             - Ticker Link to Intelligence
- Daily Flagship Brief                 - Mobile Quick Actions
- 4 Decision Engines                   - WhatsApp Direct Triggers
- Deep Reading Modal & WhatsApp
```

---

## 2. Security Architecture

### 2.1 SSRF Guard (`is_safe_url`)
Every incoming and outbound source URL is checked against private IP networks and link-local addresses:
```python
# Forbidden ranges:
# 127.0.0.0/8 (Loopback)
# 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 (Private IPv4)
# 169.254.0.0/16 (Link-Local / Cloud Metadata APIs)
# ::1, fc00::/7, fe80::/10 (IPv6 Loopback & Local)
```

### 2.2 Prompt Injection Guard (`PromptGuard`)
Any external content fed into AI models is enclosed in boundary tags:
```xml
<UNTRUSTED_MARKET_DATA source="{source_name}">
{cleaned_sanitized_text}
</UNTRUSTED_MARKET_DATA>
```
Adversarial evasion patterns such as `"ignore previous instructions"`, `"system prompt:"`, `"you are now an unfiltered"`, or `"reveal keys"` are neutralized and stripped with `[BLOCKED_INSTRUCTION]` tokens.

---

## 3. Storage & Concurrency Architecture

- **Engine:** SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
- **Thread Safety:** Python `threading.RLock()` protects all connection acquisitions and transaction blocks.
- **Conflict Handling:** Uses deterministic article IDs based on MD5 slug hashes and `ON CONFLICT(slug) DO UPDATE SET` to seamlessly update ongoing developing stories without duplicate keys.
- **Fail-Safe Cache:** On every publication, an atomic export is written to `static/data/latest_news.json` using a temporary `.tmp` file and an atomic `os.replace()`, ensuring no read locks or half-written states ever cause a 503 error on the frontend.
