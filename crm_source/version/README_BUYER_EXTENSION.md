# 🎯 Nexa CRM — AI Buyer Extension

**AI Buyer Extension**, Nexa CRM'e entegre edilmiş, alıcı profillerini otomatik olarak yeni ilanlarla eşleştiren ve multi-channel bildirimler gönderen bir sistemdir.

## ✨ Özellikler

- ✅ **Alıcı Profili Yönetimi** — Fiyat, alan, mahalle, oda sayısı, yaş, amenities
- ✅ **AI Matching Engine** — Gemini + Vector benzerliği ile semantik eşleştirme
- ✅ **Natural Language Parsing** — "Ankara'da 2+1 daire, max 5M" şeklinde kriterleri otomatik parse et
- ✅ **Multi-Channel Notifications** — Email, Telegram, WhatsApp, CRM Task
- ✅ **Dashboard & Analytics** — Eşleşme istatistikleri, tier dağılımı, ortalama skor
- ✅ **Firebase Integration** — Tüm veriler güvenli Firestore'da
- ✅ **Fuzzy Matching** — Hatalı yazımlara karşı toleranslı

## 🏗️ Mimari

```
┌─────────────────────────────────────────┐
│         Nexa CRM (Mevcut)                │
├─────────────────────────────────────────┤
│  • app.py (Flask)                       │
│  • Firebase (Firestore)                 │
│  • mailer.py (Email)                    │
│  • wa_cloud.py (WhatsApp)               │
│  • ai_listing.py (Scraping + Gemini)    │
└─────────────────────────────────────────┘
            ↓
      [NEW] Buyer Extension
┌─────────────────────────────────────────┐
│  buyer_engine.py                        │
│  ├─ BuyerProfile (Data model)           │
│  ├─ BuyerMatcher (Matching logic)       │
│  ├─ ListingMatch (Match result)         │
│  └─ NotificationEngine (Notifications)  │
├─────────────────────────────────────────┤
│  /api/buyer/* (Routes)                  │
│  ├─ /profile/create/list/get/update     │
│  ├─ /match-listing/matches/stats        │
│  ├─ /notify / /dashboard                │
│  └─ /parse-criteria                     │
├─────────────────────────────────────────┤
│  buyer_panel.html (Frontend)            │
│  ├─ Dashboard (Stats)                   │
│  ├─ Profiles (CRUD)                     │
│  └─ Matches (View + Notify)             │
└─────────────────────────────────────────┘
```

## 🚀 Kurulum

### 1️⃣ Dosyaları Kopyala

```bash
# Proje dizinine kopyala
cp buyer_engine.py /path/to/nexa-crm/
cp buyer_panel.html /path/to/nexa-crm/templates/
```

### 2️⃣ Python Paketlerini Yükle

```bash
# Opsiyonel: Vector similarity için
pip install -r requirements-buyer.txt

# Veya manuel
pip install sentence-transformers>=2.2.0
```

### 3️⃣ app.py'ye Entegrasyon

**A) İmport'ları Ekle** (Satır ~42)

```python
from buyer_engine import (
    BuyerProfile, BuyerMatcher, ListingMatch,
    buyer_engine_status, parse_natural_language_criteria
)
```

**B) API Routes'larını Ekle** (bootstrap_app() çağrısından önce)

Aşağıdaki routes'ları app.py'nin sonuna kopyala-yapıştır yap:
- `/api/buyer/status`
- `/api/buyer/profile/create` (POST)
- `/api/buyer/profile/list` (GET)
- `/api/buyer/profile/get` (GET)
- `/api/buyer/profile/update` (POST)
- `/api/buyer/profile/delete` (POST)
- `/api/buyer/match-listing` (POST)
- `/api/buyer/matches/list` (GET)
- `/api/buyer/matches/stats` (GET)
- `/api/buyer/notify` (POST)
- `/api/buyer/parse-criteria` (POST)
- `/api/buyer/dashboard` (GET)

**Kaynak:** [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) → Adım 3

### 4️⃣ crm.html'e Entegrasyon

**buyer_panel.html'i crm.html'e ekle:**

```html
<!-- crm.html'in <body> içine -->

<!-- TAB NAV'ına ekle -->
<button onclick="switchToBuyerPanel(currentUserID)">🎯 Buyer Panel</button>

<!-- İçeriğe ekle -->
<div id="buyerPanelContainer" style="display:none;">
  <!-- buyer_panel.html içeriğini buraya paste et -->
</div>
```

### 5️⃣ .env Konfigürasyonu

```bash
# Buyer Engine
BUYER_MIN_MATCH_SCORE=50
BUYER_VECTOR_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLE_BUYER_NOTIFICATIONS=true

# Mevcut variables (zaten var olmalı)
GEMINI_API_KEY=...
EMAIL_PROVIDER=smtp
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

### 6️⃣ Test Et

```bash
# Engine status kontrol
curl http://localhost:5000/api/buyer/status

# Unit testleri çalıştır
python test_buyer_engine.py
```

## 📖 Kullanım

### Admin Panel (crm.html → Buyer Panel)

#### Dashboard
- 📊 Aktif buyer profilleri
- 📈 Toplam eşleşme sayısı
- ⭐ Ortalama eşleşme skoru
- 📋 Tier dağılımı (Perfect, Excellent, Good, Fair, Weak)

#### Profiller
1. **+ Yeni Profil** butonuna tıkla
2. Temel info (Ad, Email, Telefon)
3. Kriterleri gir:
   - 💰 Fiyat aralığı (TL)
   - 📐 Alan aralığı (m²)
   - 📍 Semtler (Çankaya, Dikmen, vb.)
   - 🏠 Mülk tipi (Daire, Dubleks, Villa, vb.)
   - Oda sayısı, yaş, amenities (opsiyonel)
4. Bildirim tercihlerini seç (Email, CRM Task, Telegram, WhatsApp)
5. **Kaydet**

#### Eşleşmeler
1. **Profil Seç** dropdown'dan
2. Tüm eşleşmeleri görüntüle (tier'e göre renk kodlama)
3. Skor, detaylar, ilan bilgisi görüntüle
4. **📧 Bildir** ile alıcıyı bilgilendir

### API Kullanım

#### Profil Oluştur

```bash
curl -X POST http://localhost:5000/api/buyer/profile/create \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user_123",
    "name": "Ahmet Yılmaz",
    "email": "ahmet@example.com",
    "phone": "05324514008",
    "criteria": {
      "min_price": 3000000,
      "max_price": 6000000,
      "neighborhoods": ["Çankaya"],
      "property_types": ["Daire"]
    }
  }'
```

#### İlanı Eşleştir

```bash
curl -X POST http://localhost:5000/api/buyer/match-listing \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user_123",
    "listing": {
      "id": "listing_123",
      "property_type": "Daire",
      "location": "Çankaya",
      "price": 4500000,
      "area": 110,
      "rooms": 3,
      "age": 5,
      "amenities": ["Asansör", "Otopark"]
    }
  }'
```

**Yanıt:**

```json
{
  "ok": true,
  "listing_id": "listing_123",
  "matches": [
    {
      "buyer_id": "buyer_001",
      "match_score": 87.5,
      "tier": "excellent",
      "details": {
        "price": "4.500.000 TL (85%)",
        "area": "110 m² (90%)",
        "location": "Çankaya (100%)"
      }
    }
  ]
}
```

#### Eşleşmeleri Listele

```bash
curl "http://localhost:5000/api/buyer/matches/list?uid=user_123&buyer_id=buyer_001&limit=50"
```

#### Dashboard

```bash
curl "http://localhost:5000/api/buyer/dashboard?uid=user_123"
```

#### Alıcıyı Bildir

```bash
curl -X POST http://localhost:5000/api/buyer/notify \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "user_123",
    "buyer_id": "buyer_001",
    "match_score": 87.5,
    "channels": ["email", "crm_task"]
  }'
```

## 📊 Eşleşme Skoru Nasıl Hesaplanır?

Ağırlıklı ortalama formülü:

```
Final Score = 
  Price (25%) +
  Area (20%) +
  Location (20%) +
  Property Type (15%) +
  Rooms (5%) +
  Age (5%) +
  Amenities (5%) +
  Natural Language (3%) +
  Vector Similarity (2%)
```

### Tier Dağılımı

| Skor | Tier | Emoji | Anlamı |
|------|------|-------|--------|
| 90-100 | 🟢 Perfect | Mükemmel | İdeal eşleşme |
| 75-89 | 🔵 Excellent | Mükemmel | Çok iyi eşleşme |
| 60-74 | 🟡 Good | İyi | Kabul edilebilir |
| 45-59 | 🟠 Fair | Orta | Düşünülebilir |
| 30-44 | 🔴 Weak | Zayıf | Marjinal |
| <30 | ⚪ Poor | Çok zayıf | Eşleşmiyor |

## 🔍 Natural Language Parsing

Gemini ile kriterleri doğal dilde yaaz:

```bash
curl -X POST http://localhost:5000/api/buyer/parse-criteria \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Ankara'\'da yeni, balkonlu, otopark, minimum 100m², maksimum 5 milyon, Çankaya veya Dikmen"
  }'
```

**Yanıt:**

```json
{
  "ok": true,
  "criteria": {
    "min_area": 100,
    "max_price": 5000000,
    "neighborhoods": ["Çankaya", "Dikmen"],
    "property_types": ["Daire"],
    "amenities_required": ["Balkon", "Otopark"]
  }
}
```

## 🔗 Firebase Veri Yapısı

```
Firestore
└─ users/{uid}
   ├─ buyers/{buyerID}
   │  ├─ id: string
   │  ├─ name, email, phone
   │  ├─ criteria: {...}
   │  ├─ preferences: {...}
   │  ├─ is_active: boolean
   │  ├─ created_at: timestamp
   │  └─ updated_at: timestamp
   │
   └─ buyer_matches/{matchID}
      ├─ buyer_id: string
      ├─ listing_id: string
      ├─ listing_data: {...}
      ├─ match_score: number (0-100)
      ├─ match_details: {...}
      ├─ tier: string
      ├─ created_at: timestamp
      ├─ notification_sent: boolean
      └─ user_interest: "interested" | "not_interested" | null
```

## ⚙️ Konfigürasyon

### buyer_engine.py Sabitler

```python
MIN_MATCH_SCORE = 50  # Gösterilecek min skor
VECTOR_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Hızlı, hafif
GEMINI_MODEL = "gemini-2.5-flash"  # NL parsing için
```

### Gemini Rate Limits

- **gemini-2.5-flash**: 10 RPM / 250 RPD (önerilen)
- **gemini-2.5-flash-lite**: 15 RPM / 1000 RPD (fallback)
- **gemini-2.5-pro**: 5 RPM / 100 RPD (yetenekli ama sınırlı)

## 🧪 Testing

```bash
# Unit testleri çalıştır
python test_buyer_engine.py

# Spesifik test
python -m pytest test_buyer_engine.py::test_matching_engine -v
```

## 🐛 Troubleshooting

### ❌ "Firebase bağlı değil"
- app.py'de `init_firebase_admin()` çağrılıyor mu?
- `.env`'de `FIREBASE_SERVICE_ACCOUNT` var mı?

### ❌ Vector model yüklenmedi
```bash
pip install sentence-transformers
```

### ❌ Gemini API hatası
- `.env`'de `GEMINI_API_KEY` var mı?
- API key valid mi? → [Google AI Studio](https://aistudio.google.com/)

### ❌ Email gönderilemedi
- `mailer.py` status kontrol: `/api/mailer/status`
- SMTP credentials doğru mu?

### ❌ Eşleşme bulunamıyor
- Min skor yeterli mi? (default: 50)
- Kriterler çok sıkı mı?
- → Test profili oluştur, rahat kriterler kullan

## 📈 Kullanım Akışı

```
1. ADMIN: Buyer profili oluşturur
   /api/buyer/profile/create
   ↓
2. SİSTEM: Yeni ilan scrape'lenir
   (existing listing pipeline)
   ↓
3. SİSTEM: İlanı buyer'larla eşleştir
   /api/buyer/match-listing
   ↓
4. ADMIN: Dashboard'da eşleşmeleri görür
   /api/buyer/dashboard
   ↓
5. ADMIN: Alıcıyı bildir
   /api/buyer/notify
   ↓
6. ALICI: Email/Telegram/WhatsApp aldı
```

## 🚨 Production Hazırlığı

- [ ] `GEMINI_API_KEY` set mi?
- [ ] `EMAIL_PROVIDER` ve SMTP configured mi?
- [ ] `WA_PHONE_NUMBER_ID` ve `WA_ACCESS_TOKEN` set mi?
- [ ] Firebase security rules'ları kontrol et
- [ ] Rate limiting aktif mi? (`flask-limiter`)
- [ ] Logging konfigüre edildi mi?
- [ ] Batch processing job'ları scheduled mi?

## 📚 Kaynak Dosyalar

| Dosya | Amaç |
|-------|------|
| `buyer_engine.py` | Ana logic (Matching, profiles, models) |
| `app_buyer_routes.py` | API route'ları (app.py'ye copy-paste) |
| `buyer_panel.html` | Frontend UI (crm.html'e integrate) |
| `test_buyer_engine.py` | Unit testler |
| `INTEGRATION_GUIDE.md` | Detaylı entegrasyon rehberi |
| `requirements-buyer.txt` | Python dependencies |
| `.env.example` | Environment variables |

## 📞 Destek

- **Hata raporu**: Detaylı error message + env setup
- **Feature request**: Nexa Lab discord/email
- **Performance issue**: Profil sayısı, listing frequency, API quotas

## 📄 Lisans

Nexa CRM tarafından — Gayrimenkul Mühendisi Brand

---

**Versiyon:** 1.0.0  
**Tarih:** 2026-07-07  
**Status:** Production-Ready ✅
