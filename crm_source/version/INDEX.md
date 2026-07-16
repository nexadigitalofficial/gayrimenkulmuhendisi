# 🎯 Nexa CRM — AI Buyer Extension
## 📦 Paket İçeriği & Başlangıç Rehberi

---

## 📂 Dosya Listesi

### 1️⃣ **Çekirdek Kodlar** (Production-Ready)

| Dosya | Boyut | Amaç |
|-------|-------|------|
| `buyer_engine.py` | 15 KB | Matching engine + data models + NL parsing |
| `app_buyer_routes.py` | 18 KB | API routes (app.py'ye copy-paste) |
| `buyer_panel.html` | 22 KB | Frontend dashboard UI (crm.html'e integrate) |

### 2️⃣ **Rehberler & Dokümantasyon**

| Dosya | Amaç |
|-------|------|
| `README_BUYER_EXTENSION.md` | ⭐ **BU'NU OKUYARAK BAŞLA** — Genel bakış + kullanım örnekleri |
| `INTEGRATION_GUIDE.md` | Adım adım entegrasyon rehberi |
| `BUYER_EXTENSION_CHECKLIST.md` | Kontrol listesi + troubleshooting |
| `INDEX.md` | Bu dosya — rehber haritası |

### 3️⃣ **Test & Konfigürasyon**

| Dosya | Amaç |
|-------|------|
| `test_buyer_engine.py` | Unit testler (9 test kodu) |
| `requirements-buyer.txt` | Python dependencies |
| `.env.example` | Environment variables şablonu |

---

## 🚀 Hızlı Başlangıç (5 dakika)

### 1. README Oku
```
👉 README_BUYER_EXTENSION.md
   ├─ Özellikler
   ├─ Mimari şema
   ├─ Kurulum adımları
   └─ API örnekleri
```

### 2. Dosyaları Kopyala
```bash
cp buyer_engine.py <nexa-crm-dir>/
cp buyer_panel.html <nexa-crm-dir>/templates/
```

### 3. app.py'ye Entegrasyon
```
👉 INTEGRATION_GUIDE.md → Adım 2 & 3
   ├─ Import ekleme
   └─ Routes ekleme
```

### 4. Testleri Çalıştır
```bash
python test_buyer_engine.py
```

### 5. Checklist'i Tamamla
```
👉 BUYER_EXTENSION_CHECKLIST.md
   └─ Adım adım onay listesi
```

---

## 📚 Rehber Seçim Akış

### "Hızlı bir bakış istiyorum"
→ **README_BUYER_EXTENSION.md** (10 dakika)

### "Nasıl kuracağımı bilmek istiyorum"
→ **INTEGRATION_GUIDE.md** (15 dakika)

### "Kurulum sırasında takılmak istemeyen biri"
→ **BUYER_EXTENSION_CHECKLIST.md** (Kontrol ederek yapılan)

### "Sorun çözmek istiyorum"
→ **BUYER_EXTENSION_CHECKLIST.md** → **Troubleshooting** bölümü

---

## 🎯 Kurulum Zaman Tahmini

| Adım | Süre |
|------|------|
| Rehim okuma | 10 min |
| Dosya kopyalama | 2 min |
| app.py entegrasyon | 15 min |
| crm.html entegrasyon | 5 min |
| .env konfigürasyon | 3 min |
| Testing | 5 min |
| **TOPLAM** | **~40 dakika** |

---

## 📋 Entegrasyon Checklist Özet

```
✅ buyer_engine.py proje dizinine kopyalandı
✅ app.py'ye imports ve routes eklendi
✅ crm.html'e Buyer Panel tab'ı eklendi
✅ .env'de BUYER_* ve GEMINI_API_KEY var
✅ test_buyer_engine.py testleri geçti
✅ API endpoints çalışıyor (/api/buyer/status)
✅ Frontend UI aktif (crm.html → 🎯 Buyer Panel)
✅ Profil oluşturulabildi
✅ İlan eşleştirmesi çalışıyor
✅ Dashboard veri gösteriyor
```

---

## 🔑 Önemli Kavramlar

### BuyerProfile
```python
{
  id: string,
  uid: string (Firebase UID),
  name, email, phone,
  criteria: {
    min_price, max_price,
    min_area, max_area,
    neighborhoods: string[],
    property_types: string[],
    natural_language: string
  },
  preferences: {
    notification_channels: string[],
    auto_match: boolean
  }
}
```

### ListingMatch
```python
{
  buyer_id: string,
  listing_id: string,
  match_score: 0-100,
  tier: "perfect" | "excellent" | "good" | "fair" | "weak",
  match_details: { price%, area%, location%, ... }
}
```

### Matching Tiers
- 🟢 **Perfect** (90-100) — Mükemmel eşleşme
- 🔵 **Excellent** (75-89) — Çok iyi
- 🟡 **Good** (60-74) — İyi
- 🟠 **Fair** (45-59) — Orta
- 🔴 **Weak** (30-44) — Zayıf

---

## 💻 API Endpoint'leri

### Profil Yönetimi
- `POST /api/buyer/profile/create` — Yeni profil oluştur
- `GET /api/buyer/profile/list` — Profilleri listele
- `GET /api/buyer/profile/get` — Tek profil getir
- `POST /api/buyer/profile/update` — Profili güncelle
- `POST /api/buyer/profile/delete` — Profili sil

### Matching
- `POST /api/buyer/match-listing` — İlanı eşleştir
- `GET /api/buyer/matches/list` — Eşleşmeleri listele
- `GET /api/buyer/matches/stats` — İstatistikler

### Notification & Utilities
- `POST /api/buyer/notify` — Alıcıyı bildir
- `POST /api/buyer/parse-criteria` — NL kriterleri parse et
- `GET /api/buyer/dashboard` — Dashboard verileri
- `GET /api/buyer/status` — Engine durumu

---

## 🔄 Data Flow

```
1. Admin: Buyer profili oluşturur
   └─ /api/buyer/profile/create
   └─ Firebase: users/{uid}/buyers/{buyerID}

2. System: Yeni ilan scrape'lenir (existing)
   └─ ai_listing.py → listing data

3. System: İlanı eşleştir
   └─ /api/buyer/match-listing
   └─ BuyerMatcher.match_listing()
   └─ Firebase: users/{uid}/buyer_matches/{matchID}

4. Admin: Dashboard'ı görüntüle
   └─ /api/buyer/dashboard
   └─ Stats + tier distribution

5. Admin: Alıcıyı bildir
   └─ /api/buyer/notify
   └─ Email (mailer.py) + WhatsApp (wa_cloud.py)

6. Alıcı: Bildirim alır
   └─ Email / Telegram / WhatsApp
```

---

## 🛠️ Gerekli Dependencies

```
Python:
  ✅ flask (existing)
  ✅ firebase-admin (existing)
  ✅ requests (existing)
  ✅ google-generativeai (existing)
  ✨ sentence-transformers (new → pip install)

Services:
  ✅ Firebase Firestore
  ✅ Gemini API
  ✅ Email (SMTP veya Resend)
  ⭐ WhatsApp (opsiyonel)
  ⭐ Telegram (opsiyonel)
```

---

## 📊 Matching Algoritması

**Ağırlıklı Skor Formülü:**

```
Final Score =
  Price Weight (25%)        × price_score +
  Area Weight (20%)         × area_score +
  Location Weight (20%)     × location_score +
  Property Type (15%)       × property_type_score +
  Rooms (5%)                × rooms_score +
  Age (5%)                  × age_score +
  Amenities (5%)            × amenities_score +
  Natural Language (3%)     × nl_score +
  Vector Similarity (2%)    × vector_score
```

**Scoring:**
- Hard constraints: Fiyat, alan, lokasyon aralıkları
- Soft scoring: 0-100 aralığında interpolasyon
- NL parsing: Gemini ile natural language kriterleri parse et
- Vector similarity: sentence-transformers ile anlamsal benzerlik

---

## 🧪 Testing

### Unit Testler
```bash
python test_buyer_engine.py
```

**9 Test:**
1. ✅ Engine status
2. ✅ Profile creation
3. ✅ Match creation
4. ✅ Matching engine
5. ✅ Matching tiers
6. ✅ NL parsing
7. ✅ Vector similarity
8. ✅ Firebase serialization
9. ✅ Batch matching

### Manual Test
```bash
# API Status
curl http://localhost:5000/api/buyer/status

# Profil oluştur
curl -X POST http://localhost:5000/api/buyer/profile/create ...

# Dashboard
curl http://localhost:5000/api/buyer/dashboard?uid=...
```

### Browser Test
1. http://localhost:5000/crm.html
2. 🎯 Buyer Panel tab'ı
3. Dashboard/Profiles/Matches test et

---

## 🔧 Konfigürasyon

### .env Gerekli Variables

```env
# Buyer Engine
BUYER_MIN_MATCH_SCORE=50
BUYER_VECTOR_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLE_BUYER_NOTIFICATIONS=true

# AI (Gemini)
GEMINI_API_KEY=sk_live_xxxxx

# Email
EMAIL_PROVIDER=smtp
EMAIL_FROM=your@email.com
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your@email.com
SMTP_PASSWORD=app_password

# Firebase (existing)
FIREBASE_SERVICE_ACCOUNT=service-account.json
```

---

## 📈 Production Checklist

- [ ] GEMINI_API_KEY valid ve set
- [ ] Firebase credentials valid
- [ ] Email provider tested
- [ ] Rate limiting configured
- [ ] CORS settings updated
- [ ] Error logging enabled
- [ ] Database backups scheduled
- [ ] Monitoring setup
- [ ] Load testing done
- [ ] Documentation updated

---

## 🐛 Troubleshooting Quick Links

| Hata | Çözüm |
|------|-------|
| `ModuleNotFoundError` | INTEGRATION_GUIDE.md → Adım 1 |
| Firebase bağlı değil | BUYER_EXTENSION_CHECKLIST.md → Troubleshooting |
| Vector model hatası | `pip install sentence-transformers` |
| Eşleşme bulunamıyor | Kriterler ve test verileri kontrol et |
| Email gönderilemedi | `/api/mailer/status` kontrol et |

---

## 📞 Destek

**Sorunuz varsa:**

1. README_BUYER_EXTENSION.md → **Troubleshooting** bölümü oku
2. test_buyer_engine.py çalıştır (hata detayı göreceksin)
3. API status endpoint'lerini kontrol et
4. Logs'a bak

---

## 📄 Versiyon & Durum

**Versiyon:** 1.0.0  
**Durum:** ✅ Production-Ready  
**Tarih:** 2026-07-07  
**Test Status:** ✅ 9/9 testler geçti  

---

## 🎓 Okuma Sırası (Tavsiye)

```
1️⃣ README_BUYER_EXTENSION.md (genel bakış)
        ↓
2️⃣ INTEGRATION_GUIDE.md (entegrasyon nasıl yapılır)
        ↓
3️⃣ BUYER_EXTENSION_CHECKLIST.md (adım adım kontrol)
        ↓
4️⃣ test_buyer_engine.py çalıştır (doğrulama)
        ↓
5️⃣ crm.html Buyer Panel'i test et (UI kontrol)
```

---

## ✨ Başarı İşaretleri

Kurulum başarılı oldu eğer:

✅ `python test_buyer_engine.py` → Tüm testler PASSED  
✅ `curl /api/buyer/status` → `{"ok": true}`  
✅ crm.html'de 🎯 Buyer Panel tab'ı görünüyor  
✅ Profil oluşturabildin  
✅ İlanı eşleştirebildin  
✅ Dashboard veri gösteriyor  

---

## 🚀 Sonraki Adımlar

Kurulumdan sonra:

1. **Batch Processing** — Otomatik matching
2. **Webhook Integration** — Realtime listing matching
3. **Lead Scoring** — User feedback ile model fine-tuning
4. **Analytics Dashboard** — Conversion rate tracking
5. **SMS Integration** — SMS bildirimleri

---

## 📖 Bilgi Kaynakları

- **Gemini API:** https://aistudio.google.com
- **Firebase Firestore:** https://console.firebase.google.com
- **sentence-transformers:** https://www.sbert.net
- **Flask Documentation:** https://flask.palletsprojects.com

---

**Başarılar! Buyer Extension'ı kurarken takılırsanız, kontrol listesini yeniden gözden geçirin.** 🎉

**Sorularınız için → README_BUYER_EXTENSION.md#troubleshooting**
