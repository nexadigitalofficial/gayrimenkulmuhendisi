# 🔧 TEKNİK DOKÜMANTASYON - ENTEGRELİ SİSTEM

## 📋 SİSTEM MİMARİSİ

```
┌─────────────────────────────────────────────────────────┐
│               a.py (UNIFIED SYSTEM)                     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │          1. WEB SCRAPER                         │   │
│  │  CB.com.tr → BeautifulSoup → 600+ ilan         │   │
│  │  Output: JSON, CSV, Markdown                    │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │     2. WHATSAPP PARSER (Turkish NLP)            │   │
│  │  WhatsApp TXT → ARAYIŞ + PORTFÖY                │   │
│  │  NLP Patterns: Districts, Types, Prices        │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │      3. AI MATCHER (6-Factor Scoring)           │   │
│  │  Arayış × Portföy → Score (0-100)              │   │
│  │  Fallback: Score only (Ollama olmadan)         │   │
│  │  AI Mode: + Ollama/Qwen2.5 analysis            │   │
│  └─────────────────────────────────────────────────┘   │
│                       ↓                                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │      4. REPORT GENERATION                       │   │
│  │  JSON, Markdown, Recommendations                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 DOSYA YAPISI

```
a.py (1800+ lines)
├── Konfigürasyon (lines 1-50)
├── Enums & Data Models (lines 52-350)
│   ├── PropertyType
│   ├── TransactionType
│   ├── ArayisRecord
│   ├── PortfoyRecord
│   ├── Match
│   └── MatchReason
│
├── Turkish NLP Patterns (lines 352-400)
│   ├── Property types regex
│   ├── Transaction types regex
│   ├── Districts (Ankara focused)
│   ├── Neighborhoods
│   └── Features
│
├── CBScraper Class (lines 402-700)
│   ├── fetch_page()
│   ├── parse_listing()
│   ├── scrape_page()
│   ├── scrape_all()
│   ├── save_json()
│   ├── save_csv()
│   └── save_markdown()
│
├── WhatsAppCBParser Class (lines 702-1200)
│   ├── parse_file()
│   ├── _split_messages()
│   ├── _is_arayis()
│   ├── _is_portfoy()
│   ├── _parse_arayis()
│   ├── _parse_portfoy()
│   ├── _extract_*() (districts, types, prices, rooms, area, features)
│   └── _calculate_*_confidence()
│
├── OllamaMatcher Class (lines 1202-1550)
│   ├── match_arayis_portfoy()
│   ├── match_all()
│   ├── _score_*() (price, rooms, location, type, features, urgency)
│   ├── _compile_reasons()
│   ├── _generate_recommendation()
│   ├── export_json()
│   └── generate_report()
│
├── Utility Functions (lines 1552-1650)
│   ├── run_full_system()
│   ├── _detect_property_type()
│   └── _parse_area()
│
└── CLI & Main (lines 1652-1800)
    ├── argparse
    ├── main() execution
    └── Exception handling
```

---

## 🎯 SÖZ DİZİMİ (SYNTAX)

### 1. CBScraper - Web Scraping

```python
from a import CBScraper

scraper = CBScraper()
listings = scraper.scrape_all()  # 600+ ilan
scraper.save_all()               # JSON + CSV + Markdown

# Veya manuel
soup = scraper.fetch_page(1)
page_listings = scraper.scrape_page(1)
listing_dict = scraper.parse_listing(card_element)
```

**Çıktı Formatı:**

```python
{
    'id': '358156',
    'title': 'ÇAMLIDERE\'DE MÜSTAKİL 2+1...',
    'type': 'Villa',
    'city': 'ANKARA',
    'district': 'ÇAMLIDERE',
    'neighborhood': 'BEYLER',
    'area': '120',
    'rooms': '2+1',
    'price': '₺5.350.000',
    'consultant': 'Yiğit Narin',
    'office': 'CB VIP',
    'url': 'https://...',
    'latitude': '40,510168',
    'longitude': '32,477800',
    'scraped_at': '2026-07-10T12:34:56.789123'
}
```

### 2. WhatsAppCBParser - Turkish NLP

```python
from a import WhatsAppCBParser

parser = WhatsAppCBParser()
arayislar, portfoyler = parser.parse_file("whatsapp.txt")

for arayis in arayislar:
    print(f"ID: {arayis.arayis_id}")
    print(f"Districts: {arayis.districts}")
    print(f"Budget: {arayis.budget_min} - {arayis.budget_max}")
    print(f"Urgency: {arayis.urgency_level}/5")
```

**Çıktı Formatı (ArayisRecord):**

```python
ArayisRecord(
    arayis_id='arayis_5423',
    sender='Yiğit Narin',
    phone='+905301234567',
    message_text='Çankaya Birlik\'te 3+1, ₺5M bütçe, acil',
    districts=['çankaya'],
    property_types=[PropertyType.DAIRE],
    budget_min=5000000.0,
    budget_max=5000000.0,
    rooms=['3+1'],
    urgency_level=5,
    confidence=0.85
)
```

### 3. OllamaMatcher - AI Matching

```python
from a import OllamaMatcher

matcher = OllamaMatcher()
matches = matcher.match_all(arayislar, portfoyler)

for match in matches[:5]:
    print(f"{match.overall_score:.1f}% - {match.arayis_id} ↔ {match.portfoy_id}")
    print(f"  Price: {match.price_score:.2f}")
    print(f"  Rooms: {match.rooms_score:.2f}")
    print(f"  Location: {match.location_score:.2f}")
    print(f"  Recommendation: {match.recommendation}")
```

**Çıktı Formatı (Match):**

```python
Match(
    arayis_id='arayis_5423',
    portfoy_id='cb_scraper_358156',
    overall_score=89.5,  # 0-100
    confidence=0.92,      # 0-1
    price_score=1.0,
    rooms_score=0.8,
    location_score=1.0,
    type_score=0.9,
    features_score=0.7,
    urgency_score=1.0,
    reasons=[
        MatchReason(category='price_match', score=1.0, explanation='...'),
        MatchReason(category='location_match', score=1.0, explanation='...'),
    ],
    ai_analysis="",
    recommendation="📞 Yiğit Narin'e ulaş",
    contact_info="+905301234567",
    timestamp="2026-07-10T12:34:56"
)
```

---

## 🧮 MATCHING ALGORITMA

### 6-Factor Weighted Scoring

```python
overall_score = (
    price_score    × 0.25 +    # En önemli
    rooms_score    × 0.25 +    # En önemli
    location_score × 0.20 +
    type_score     × 0.15 +
    features_score × 0.10 +
    urgency_score  × 0.05      # En az önemli
)
```

### Scoring Functions Detayı

#### Price Scoring

```python
if not budget_min or not price:
    return 0.5  # Neutral

if budget_min <= price <= budget_max:
    return 1.0  # Perfect

elif budget_min * 0.8 <= price <= budget_max * 1.2:
    return 0.8  # Good

elif budget_min * 0.5 <= price <= budget_max * 1.5:
    return 0.5  # Acceptable

else:
    return 0.2  # Not match
```

#### Location Scoring

```python
if not arayis_districts:
    return 0.5  # No preference

if portfoy_district.lower() in [d.lower() for d in arayis_districts]:
    return 1.0  # Exact match

else:
    return 0.2  # Different district
```

---

## 🌐 NETWORK & HTTP

### Request Headers

```python
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Apple WebKit/537.36...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9',
    'Referer': 'https://www.cb.com.tr/',
}
```

### Rate Limiting

```python
RATE_LIMIT = 0.5  # seconds between pages

# Implemented in scrape_page():
time.sleep(RATE_LIMIT)
```

### Retry Logic

```python
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

# Exponential backoff:
wait_time = RETRY_DELAY * (attempt + 1)
# 2s → 4s → 6s
```

---

## 💾 VERI SAKLAMA

### JSON Yapısı

```json
{
  "source": "cb.com.tr",
  "scraped_at": "2026-07-10T12:34:56.789123",
  "total_listings": 587,
  "listings": [
    { ... listing object ... }
  ],
  "errors": []
}
```

### CSV Formatı

```
id,title,type,city,district,neighborhood,area,rooms,price,consultant,office,url,latitude,longitude,scraped_at
358156,ÇAMLIDERE'DE MÜSTAKİL 2+1...,Villa,ANKARA,ÇAMLIDERE,BEYLER,120,2+1,₺5.350.000,Yiğit Narin,CB VIP,https://...,40,510168,32,477800,2026-07-10T12:34:56
```

---

## 🔐 TÜRKÇE NLP PATTERNS

### Districts Regex (Ankara)

```python
DISTRICTS = {
    'çankaya': r'(?:çankaya|cankaya)',
    'keçiören': r'(?:keçiören|kecior)',
    'yenimahalle': r'(?:yenimahalle|yeni mahalle)',
    # ... total 13 districts
}
```

### Property Types Regex

```python
PROPERTY_TYPES = {
    r'\b(daire|flat|apartment|apt)\b': PropertyType.DAIRE,
    r'\b(villa|müstakil|ev|house)\b': PropertyType.VILLA,
    r'\b(ofis|office|büro|iş yeri)\b': PropertyType.OFIS,
    # ... etc
}
```

### Features Regex

```python
FEATURES = {
    'balkon': r'(?:balkon|terrace)',
    'havuz': r'(?:havuz|pool|swimming)',
    'otopark': r'(?:otopark|parking|park)',
    'asansör': r'(?:asansör|asansor|elevator)',
    # ... total 10 features
}
```

### Price Extraction Regex

```python
# Turkish format: 5.000.000 or 5,000,000
tl_pattern = r'(\d+(?:[.,]\d+)?)\s*(?:₺|TL|tl)'

# Matches:
# ₺5.000.000
# 5,000,000 TL
# 5000000 ₺
```

---

## 🤖 OLLAMA INTEGRATION

### API Endpoints

```python
# Check connection
GET http://localhost:11434/api/tags

# Generate (with streaming disabled)
POST http://localhost:11434/api/generate
{
    "model": "qwen2.5:7b",
    "prompt": "...",
    "stream": false,
    "temperature": 0.3
}
```

### Fallback Mode

Eğer Ollama bağlantı başarısız:

```python
logger.warning("⚠️  Ollama not available - using fallback scoring")

# Sistem devam eder:
- ✅ Scoring algorithm çalışır
- ❌ AI analysis yok
- ❌ LLM-powered insights yok
```

---

## ⚙️ PERFORMANS OPTIMIZASYONU

### Hızlandırma

```python
# Dosyasının başında değiştir:
MAX_PAGES = 5          # 15 yerine
RATE_LIMIT = 0.1       # 0.5 yerine
RETRY_ATTEMPTS = 1     # 3 yerine
TIMEOUT = 5            # 10 yerine

# Etkileri:
# Hız: ~5-10 dakika → ~1 dakika
# Risk: Sunucu blocking ihtimali artar
```

### Yavaşlatma

```python
MAX_PAGES = 15
RATE_LIMIT = 1.0       # 0.5 yerine
RETRY_ATTEMPTS = 5     # 3 yerine
TIMEOUT = 15           # 10 yerine

# Etkileri:
# Hız: ~1 dakika → ~2-3 dakika
# Risk: Çok düşük (iyi pratik)
```

### Memory Optimization

```python
# Matcher:
# 600+ portföy × 45 arayış = 27,000 kombinasyon
# Her matching ~0.1 MB
# Toplam: ~2.7 MB RAM

# Scraper:
# 587 listing × 15 fields = ~350 KB
```

---

## 🧪 TESTING

### Unit Test Örneği

```python
def test_price_extraction():
    parser = WhatsAppCBParser()
    
    text = "Bütçem ₺5.000.000 - ₺6.500.000"
    min_p, max_p = parser._extract_prices(text)
    
    assert min_p == 5000000.0
    assert max_p == 6500000.0

def test_rooms_extraction():
    parser = WhatsAppCBParser()
    
    text = "3+1 veya 4+1 istiyorum"
    rooms = parser._extract_rooms(text)
    
    assert '3+1' in rooms
    assert '4+1' in rooms

def test_matching_score():
    matcher = OllamaMatcher()
    
    arayis = ArayisRecord(...)
    portfoy = PortfoyRecord(...)
    
    match = matcher.match_arayis_portfoy(arayis, portfoy)
    
    assert 0 <= match.overall_score <= 100
    assert 0 <= match.confidence <= 1
```

---

## 📊 METRIKLERI İZLEME

### Logger Output

```python
logger.info("📥 Sayfa 1 çekiliyor...")       # Info level
logger.warning("⚠️ Timeout...")              # Warning level
logger.error("❌ File not found...")         # Error level
logger.debug("📊 Processed 587 listings")   # Debug level
```

### Metric Collection

```python
# Scraper:
- Toplam ilan: 587
- Ortalama fiyat: ₺5,234,567
- Emlak türleri dağılımı
- Şehir dağılımı

# Matcher:
- Toplam kombinasyon: 27,000
- Bulunan match: 42
- Ortalama score: 87.3%
- 90+ score: 18
- 70-89 score: 16
- 50-69 score: 6
```

---

## 🔒 SECURITY CONSIDERATIONS

### Web Scraping Ethics

✅ **Yapılması Iyi:**
- Rate limiting (0.5-1 saniye/sayfa)
- User-Agent ayarı
- İnsan gibi davran
- Robots.txt kontrol et
- Sunucuya yük binmeme

❌ **Yapılmaması Gereken:**
- DDoS tarzı saldırı
- Sunucuyu çökerterek scraping
- Telif hakkı ihlali
- Bot detection sistemini engelleme

### Data Privacy

- Telefon numaraları hassas bilgidir
- WhatsApp exportu şifreli depolansın
- Çıktı dosyaları kopyalanmadan saklan

---

## 📈 SCALABILITY

### Şu An (Baseline)

```
İlan: 587 (1 ofis)
Arayış: ~50 (WhatsApp grubu)
Kombinasyon: 29,350
Süre: ~1-2 dakika
```

### 10x Ölçeklendirme

```
İlan: 5,870 (10 ofis)
Arayış: ~500 (10 WhatsApp grubu)
Kombinasyon: 2,935,000
Süre: ~10-20 dakika
Çözüm: Threading/Multiprocessing gerekli
```

### 100x Ölçeklendirme

```
İlan: 58,700 (100 ofis)
Arayış: ~5,000 (100 grup)
Kombinasyon: 293,500,000
Çözüm: Database + Backend API gerekli
```

---

## 🛠️ DEVAM EDEN GELİŞTİRMELER

### Roadmap

**Phase 1 (Tamamlandı)**
- ✅ Web Scraper
- ✅ WhatsApp Parser
- ✅ AI Matcher
- ✅ Report Generation

**Phase 2 (Şu an)
- ⏳ Database integration
- ⏳ Web dashboard
- ⏳ Real-time updates

**Phase 3 (Gelecek)
- ⚫ WhatsApp API
- ⚫ Email notifications
- ⚫ Mobile app
- ⚫ Computer Vision (foto analizi)

---

## 📞 REFERANSLAR

### Kütüphaneler

- **requests** (HTTP) - https://requests.readthedocs.io/
- **BeautifulSoup4** (HTML parsing) - https://www.crummy.com/software/BeautifulSoup/
- **Ollama** (Local LLM) - https://ollama.ai/

### RegEx Araçları

- **RegEx101** - https://regex101.com/
- **RegEx Tester** - https://www.regexpal.com/

### Türkçe NLP

- **spaCy Turkish Model** - https://github.com/explosion/spacy-models
- **Turkish Tokenizer** - https://github.com/emres/turkish-tokenizer

---

## ✅ VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 10.07.2026 | Initial unified release |
| 0.9 | 09.07.2026 | Multi-file architecture |
| 0.1 | 01.07.2026 | Basic scraper |

---

**Dokümantasyon Versiyonu:** 1.0  
**Son Güncelleme:** 10.07.2026  
**Durum:** ✅ Current  

Made by **Yiğit Narin** @ NEXA Digital

